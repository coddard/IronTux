#!/usr/bin/env python3
"""
============================================================
IronTux (Enterprise Offline) v4.1
Focus: Post-Install Security, Anti-Bruteforce, Port Sealing
Features: OOP, Docker-Safe Firewall, Auto-Backup, Verification
============================================================
"""

import os
import sys
import shutil
import subprocess
import argparse
import tarfile
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Prompt, Confirm
except ImportError:
    print("CRITICAL: 'rich' library is missing. Install it via: sudo pip3 install rich")
    sys.exit(1)

console = Console()

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURATION & CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────
BACKUP_DIR = "/var/backups/hardening_tool"
CRITICAL_FILES = [
    "/etc/ssh/sshd_config",
    "/etc/fstab",
    "/etc/fail2ban/jail.local",
    "/etc/selinux/config",
    "/etc/default/ufw",
    "/etc/ufw/after.rules",
    "/etc/firewalld/zones/public.xml",
    "/etc/apt/apt.conf.d/50unattended-upgrades"
]

@dataclass
class HardeningContext:
    dry_run: bool = False
    pkg_manager: str = ""
    os_family: str = ""
    ssh_port: str = "22"
    custom_ports: List[str] = field(default_factory=list)
    new_user: str = ""
    report_log: List[Dict[str, str]] = field(default_factory=list)
    
    # CLI Overrides
    skip_update: bool = False
    skip_ssh: bool = False
    skip_fw: bool = False
    skip_f2b: bool = False

# ──────────────────────────────────────────────────────────────────────────────
# CORE CLASSES
# ──────────────────────────────────────────────────────────────────────────────
class SystemManager:
    """Handles OS-level detection and command execution safely."""
    def __init__(self, context: HardeningContext):
        self.ctx = context

    def detect_os(self):
        if shutil.which("apt-get"):
            self.ctx.pkg_manager, self.ctx.os_family = "apt-get", "debian"
        elif shutil.which("dnf"):
            self.ctx.pkg_manager, self.ctx.os_family = "dnf", "rhel"
        elif shutil.which("zypper"):
            self.ctx.pkg_manager, self.ctx.os_family = "zypper", "suse"
        elif shutil.which("pacman"):
            self.ctx.pkg_manager, self.ctx.os_family = "pacman", "arch"
        elif shutil.which("apk"):
            self.ctx.pkg_manager, self.ctx.os_family = "apk", "alpine"
        else:
            console.print("[red][✖] Unsupported OS. No known package manager found.[/red]")
            sys.exit(1)

    def run(self, cmd: str, ignore_error: bool = False) -> subprocess.CompletedProcess:
        if self.ctx.dry_run:
            self.ctx.report_log.append({"status": "DRY-RUN", "msg": f"Would run: {cmd}"})
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return result
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed: {cmd}\nReason: {e.stderr.strip()}"
            if not ignore_error:
                self.ctx.report_log.append({"status": "ERROR", "msg": error_msg})
            return e

    def restart_service(self, service_name: str):
        if self.ctx.os_family == "alpine":
            self.run(f"rc-service {service_name} restart", ignore_error=True)
        else:
            self.run(f"systemctl restart {service_name}", ignore_error=True)

    def check_service_status(self, service_name: str) -> bool:
        """Verifies if a critical service is actually running post-hardening."""
        if self.ctx.dry_run:
            return True
        result = subprocess.run(f"systemctl is-active {service_name}", shell=True, capture_output=True, text=True)
        return result.stdout.strip() == "active"


class BackupManager:
    """Handles centralized snapshot backups and --restore functionality."""
    def __init__(self, sys_mgr: SystemManager):
        self.sys = sys_mgr

    def create_snapshot(self) -> str:
        if self.sys.ctx.dry_run: return "DRY_RUN"
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_path = os.path.join(BACKUP_DIR, f"snapshot_{ts}.tar.gz")

        with tarfile.open(archive_path, "w:gz") as tar:
            for filepath in CRITICAL_FILES:
                if os.path.exists(filepath):
                    tar.add(filepath, arcname=filepath.lstrip("/"))
        
        self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": f"System snapshot created: {archive_path}"})
        return archive_path

    def restore_snapshot(self, archive_path: str):
        if not os.path.exists(archive_path):
            console.print(f"[bold red]✖ Backup archive not found: {archive_path}[/bold red]")
            sys.exit(1)
        console.print(f"[bold yellow]⚠ Restoring system state from: {archive_path}[/bold yellow]")
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path="/")
        
        self.sys.restart_service("sshd")
        self.sys.restart_service("fail2ban")
        self.sys.restart_service("ufw" if self.sys.ctx.os_family == "debian" else "firewalld")
        console.print("[bold green]✔ System restored successfully.[/bold green]")
        sys.exit(0)


class SecurityHardener:
    def __init__(self, sys_mgr: SystemManager):
        self.sys = sys_mgr

    def update_and_patch(self):
        if self.sys.ctx.skip_update:
            self.sys.ctx.report_log.append({"status": "SKIP", "msg": "System update skipped via flag"})
            return
            
        if self.sys.ctx.os_family == "debian":
            self.sys.run("apt-get update && apt-get upgrade -y")
            self.sys.run("apt-get install -y unattended-upgrades")
            if not self.sys.ctx.dry_run:
                self.sys.run("dpkg-reconfigure --priority=low unattended-upgrades", ignore_error=True)
            self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": "System updated & Unattended-Upgrades configured"})
        elif self.sys.ctx.os_family == "rhel":
            self.sys.run("dnf update -y")
            self.sys.run("dnf install -y dnf-automatic")
            if not self.sys.ctx.dry_run:
                self.sys.run("systemctl enable --now dnf-automatic.timer")
            self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": "System updated & DNF-Automatic configured"})

    def configure_user(self):
        user = self.sys.ctx.new_user
        if not user: return
        check_user = self.sys.run(f"id {user}", ignore_error=True)
        if hasattr(check_user, 'returncode') and check_user.returncode == 0:
             self.sys.ctx.report_log.append({"status": "SKIP", "msg": f"User '{user}' already exists"})
             return
        if not self.sys.ctx.dry_run:
            self.sys.run(f"adduser --disabled-password --gecos '' {user}", ignore_error=True)
            if self.sys.ctx.os_family == "debian": self.sys.run(f"usermod -aG sudo {user}")
            elif self.sys.ctx.os_family in ["rhel", "arch", "suse"]: self.sys.run(f"usermod -aG wheel {user}")
        self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": f"User '{user}' created and added to admin group"})

    def harden_ssh(self):
        if self.sys.ctx.skip_ssh:
            self.sys.ctx.report_log.append({"status": "SKIP", "msg": "SSH hardening skipped via flag"})
            return

        cfg = "/etc/ssh/sshd_config"
        if not os.path.exists(cfg): return
        
        settings = {
            "PermitRootLogin": "no",
            "PasswordAuthentication": "no",
            "PubkeyAuthentication": "yes",
            "X11Forwarding": "no",
            "MaxAuthTries": "3"
        }
        
        if not self.sys.ctx.dry_run:
            with open(cfg, "r") as f: lines = f.readlines()
            new_lines = []
            applied = set()
            for line in lines:
                matched = False
                for k, v in settings.items():
                    if line.strip().lower().startswith(k.lower()):
                        new_lines.append(f"{k} {v}\n")
                        applied.add(k)
                        matched = True
                        break
                if not matched: new_lines.append(line)
            for k, v in settings.items():
                if k not in applied: new_lines.append(f"\n{k} {v}\n")
            with open(cfg, "w") as f: f.writelines(new_lines)
            
            svc = "sshd" if self.sys.ctx.os_family in ["rhel", "arch", "suse"] else "ssh"
            self.sys.restart_service(svc)
            
            if not self.sys.check_service_status(svc):
                self.sys.ctx.report_log.append({"status": "ERROR", "msg": "SSH Service failed to start after hardening!"})
            else:
                self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": "SSH Secured (Root disabled, PubKey forced)"})

    def configure_fail2ban(self):
        if self.sys.ctx.skip_f2b:
            self.sys.ctx.report_log.append({"status": "SKIP", "msg": "Fail2Ban skipped via flag"})
            return
            
        pm = self.sys.ctx.pkg_manager
        install_cmd = f"{pm} install -y fail2ban" if self.sys.ctx.os_family != "alpine" else f"{pm} add fail2ban"
        self.sys.run(install_cmd, ignore_error=True)

        if not self.sys.ctx.dry_run and os.path.exists("/etc/fail2ban/jail.conf"):
            self.sys.run("cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local")
            self.sys.run("sed -i 's/bantime  = 10m/bantime  = 1h/g' /etc/fail2ban/jail.local")
            self.sys.run("sed -i 's/maxretry = 5/maxretry = 3/g' /etc/fail2ban/jail.local")
            self.sys.restart_service("fail2ban")
            
            if not self.sys.check_service_status("fail2ban"):
                self.sys.ctx.report_log.append({"status": "ERROR", "msg": "Fail2Ban Service failed to start!"})
            else:
                self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": "Fail2Ban Configured (1h ban, 3 retries)"})

    def configure_firewall(self):
        if self.sys.ctx.skip_fw:
            self.sys.ctx.report_log.append({"status": "SKIP", "msg": "Firewall configuration skipped via flag"})
            return
            
        port = self.sys.ctx.ssh_port
        custom_ports = self.sys.ctx.custom_ports
        
        if self.sys.ctx.os_family == "debian":
            self._setup_ufw(port, custom_ports)
        elif self.sys.ctx.os_family in ["rhel", "suse"]:
            self._setup_firewalld(port, custom_ports)
        else:
            self.sys.ctx.report_log.append({"status": "SKIP", "msg": f"Firewall setup skipped for OS: {self.sys.ctx.os_family}"})

    def _setup_ufw(self, ssh_port: str, custom_ports: List[str]):
        pm = self.sys.ctx.pkg_manager
        self.sys.run(f"{pm} install -y ufw", ignore_error=True)

        if not self.sys.ctx.dry_run:
            self.sys.run("ufw --force reset")
            self.sys.run("ufw default deny incoming")
            self.sys.run("ufw default allow outgoing")
            self.sys.run(f"ufw allow {ssh_port}/tcp comment 'SSH'")
            self.sys.run("ufw allow 80/tcp comment 'HTTP'")
            self.sys.run("ufw allow 443/tcp comment 'HTTPS'")
            
            for p in custom_ports:
                self.sys.run(f"ufw allow {p} comment 'Custom'")

            # Docker UFW Bypass Fix
            if shutil.which("docker"):
                after_rules = "/etc/ufw/after.rules"
                if os.path.exists(after_rules):
                    with open(after_rules, "r") as f:
                        if "# BEGIN UFW AND DOCKER" not in f.read():
                            docker_patch = """
# BEGIN UFW AND DOCKER
*filter
:ufw-user-forward - [0:0]
:DOCKER-USER - [0:0]
-A DOCKER-USER -j RETURN -s 10.0.0.0/8
-A DOCKER-USER -j RETURN -s 172.16.0.0/12
-A DOCKER-USER -j RETURN -s 192.168.0.0/16
-A DOCKER-USER -p udp -m udp --sport 53 --dport 1024:65535 -j RETURN
-A DOCKER-USER -j ufw-user-forward
-A DOCKER-USER -j DROP -p tcp -m tcp --tcp-flags SYN,ACK,FIN,RST SYN
-A DOCKER-USER -j DROP -p udp
COMMIT
# END UFW AND DOCKER
"""
                            with open(after_rules, "a") as f: f.write(docker_patch)
                            self.sys.ctx.report_log.append({"status": "INFO", "msg": "Docker UFW isolation rules injected."})

            self.sys.run("ufw --force enable")
            if not self.sys.check_service_status("ufw"):
                 self.sys.ctx.report_log.append({"status": "ERROR", "msg": "UFW failed to activate!"})
            else:
                 self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": f"UFW Firewall sealed. Opened: {ssh_port}, 80, 443, {','.join(custom_ports)}"})

    def _setup_firewalld(self, ssh_port: str, custom_ports: List[str]):
        pm = self.sys.ctx.pkg_manager
        self.sys.run(f"{pm} install -y firewalld", ignore_error=True)

        if not self.sys.ctx.dry_run:
            self.sys.run("systemctl enable firewalld --now")
            self.sys.run("firewall-cmd --permanent --zone=public --remove-service=ssh", ignore_error=True)
            self.sys.run(f"firewall-cmd --permanent --zone=public --add-port={ssh_port}/tcp")
            self.sys.run("firewall-cmd --permanent --zone=public --add-port=80/tcp")
            self.sys.run("firewall-cmd --permanent --zone=public --add-port=443/tcp")
            
            for p in custom_ports:
                self.sys.run(f"firewall-cmd --permanent --zone=public --add-port={p}")
                
            self.sys.run("firewall-cmd --reload")
            if not self.sys.check_service_status("firewalld"):
                self.sys.ctx.report_log.append({"status": "ERROR", "msg": "Firewalld failed to activate!"})
            else:
                self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": f"Firewalld sealed. Opened: {ssh_port}, 80, 443, {','.join(custom_ports)}"})

    def apply_sysctl_hardening(self):
        """Applies Kernel Hardening (SYN Cookies, RP Filter, ASLR)"""
        sysctl_conf = """
# Mitigate SYN flood attacks
net.ipv4.tcp_syncookies = 1
# Prevent IP spoofing
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
# Prevent MITM attacks via redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
# Protect against Smurf attacks
net.ipv4.icmp_echo_ignore_broadcasts = 1
# Address Space Layout Randomization (ASLR)
kernel.randomize_va_space = 2
# Restrict kernel logs
kernel.dmesg_restrict = 1
"""
        if not self.sys.ctx.dry_run:
            with open("/etc/sysctl.d/99-security.conf", "w") as f:
                f.write(sysctl_conf.strip())
            self.sys.run("sysctl -p /etc/sysctl.d/99-security.conf", ignore_error=True)
        self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": "Kernel Hardening (SYN Cookies, RP Filter, ASLR) applied"})

# ──────────────────────────────────────────────────────────────────────────────
# UX & DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────
def display_dashboard(ctx: HardeningContext):
    table = Table(title="[bold blue]Security Operations Summary[/bold blue]")
    table.add_column("Status", justify="center", style="cyan", no_wrap=True)
    table.add_column("Task / Operation", style="magenta")

    for entry in ctx.report_log:
        status = entry["status"]
        if status == "SUCCESS": color = "[green]✔[/green]"
        elif status == "ERROR": color = "[red]✖[/red]"
        elif status == "DRY-RUN": color = "[blue]🥽[/blue]"
        elif status == "SKIP": color = "[dim]↷[/dim]"
        else: color = "[yellow]ℹ[/yellow]"
        
        table.add_row(color, entry["msg"])
    console.print("\n", table)

# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────
def main():
    if os.geteuid() != 0:
        console.print("[bold red]✖ Root privileges required. Run with sudo.[/bold red]")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Linux Hardening Tool v4.1 (Enterprise)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate changes without applying them.")
    parser.add_argument("--restore", type=str, metavar="ARCHIVE", help="Restore system from a specific .tar.gz snapshot.")
    parser.add_argument("--no-update", action="store_true", help="Skip system update and patching")
    parser.add_argument("--skip-ssh", action="store_true", help="Skip SSH configuration hardening")
    parser.add_argument("--skip-fw", action="store_true", help="Skip Firewall configuration")
    parser.add_argument("--skip-f2b", action="store_true", help="Skip Fail2Ban installation")
    args = parser.parse_args()

    ctx = HardeningContext(
        dry_run=args.dry_run, 
        skip_update=args.no_update,
        skip_ssh=args.skip_ssh,
        skip_fw=args.skip_fw,
        skip_f2b=args.skip_f2b
    )
    
    sys_mgr = SystemManager(ctx)
    backup_mgr = BackupManager(sys_mgr)
    hardener = SecurityHardener(sys_mgr)

    sys_mgr.detect_os()

    if args.restore:
        backup_mgr.restore_snapshot(args.restore)

    console.print(Panel.fit(
        f"[bold cyan]Linux Post-Install Hardening v4.1[/bold cyan]\n"
        f"OS Detected: [bold]{ctx.os_family.upper()}[/bold]\n"
        f"Mode: {'[bold blue]DRY-RUN[/bold blue]' if ctx.dry_run else '[bold red]LIVE[/bold red]'}",
        border_style="cyan"
    ))

    # Prompts
    ctx.new_user = Prompt.ask("[yellow]Enter a new admin username (Leave blank to skip)[/yellow]", default="").strip()
    
    if not ctx.skip_fw:
        ssh_port_input = Prompt.ask("[yellow]Enter your exact SSH Port[/yellow]", default="22")
        ctx.ssh_port = ssh_port_input if ssh_port_input.isdigit() else "22"
        
        custom_p = Prompt.ask("[yellow]Additional ports to open (e.g., 8080/tcp, 51820/udp). Leave blank if none[/yellow]", default="")
        if custom_p.strip():
            ctx.custom_ports = [p.strip() for p in custom_p.split(",") if p.strip()]

    if not Confirm.ask("Do you want to proceed with hardening?"):
        sys.exit(0)

    # 1. Backup Phase
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        task1 = progress.add_task("[yellow]Creating system snapshot...", total=None)
        backup_mgr.create_snapshot()
        time.sleep(1)
        progress.update(task1, completed=100)

    # 2. Hardening Phase
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        
        task_update = progress.add_task("[cyan]Updating System...", total=None)
        hardener.update_and_patch()
        progress.update(task_update, completed=100)
        
        task_user = progress.add_task("[cyan]Setting up Admin User...", total=None)
        hardener.configure_user()
        progress.update(task_user, completed=100)

        task_ssh = progress.add_task("[cyan]Securing SSH...", total=None)
        hardener.harden_ssh()
        progress.update(task_ssh, completed=100)

        task_f2b = progress.add_task("[cyan]Configuring Fail2Ban...", total=None)
        hardener.configure_fail2ban()
        progress.update(task_f2b, completed=100)

        task_fw = progress.add_task("[cyan]Setting up Firewall...", total=None)
        hardener.configure_firewall()
        progress.update(task_fw, completed=100)

        task_sysctl = progress.add_task("[cyan]Applying Kernel Sysctl Hardening...", total=None)
        hardener.apply_sysctl_hardening()
        progress.update(task_sysctl, completed=100)

    # 3. Final Report
    display_dashboard(ctx)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
============================================================
IronTux (Enterprise Offline)
Focus: Post-Install Security, Anti-Bruteforce, Port Sealing
Features: OOP, Docker-Safe Firewall, Auto-Backup & Restore, Auto-Patching
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
    new_user: str = ""
    report_log: List[Dict[str, str]] = field(default_factory=list)

# ──────────────────────────────────────────────────────────────────────────────
# CORE CLASSES (CLEAN CODE ARCHITECTURE)
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
        """Executes shell commands with robust stderr capturing and dry-run support."""
        if self.ctx.dry_run:
            self.ctx.report_log.append({"status": "DRY-RUN", "msg": f"Would run: {cmd}"})
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
            return result
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed: {cmd}\nReason: {e.stderr.strip()}"
            if not ignore_error:
                console.print(f"[bold red]✖ ERROR:[/bold red] {error_msg}")
                self.ctx.report_log.append({"status": "ERROR", "msg": error_msg})
            return e

    def restart_service(self, service_name: str):
        """Abstracts service restarts for Systemd (most) and OpenRC (Alpine)."""
        if self.ctx.os_family == "alpine":
            self.run(f"rc-service {service_name} restart", ignore_error=True)
        else:
            self.run(f"systemctl restart {service_name}", ignore_error=True)


class BackupManager:
    """Handles centralized snapshot backups and --restore functionality."""
    def __init__(self, sys_mgr: SystemManager):
        self.sys = sys_mgr

    def create_snapshot(self) -> str:
        if self.sys.ctx.dry_run:
            return "DRY_RUN_SNAPSHOT"
            
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
        console.print("[bold green]✔ System restored successfully. Please verify your connections.[/bold green]")
        sys.exit(0)


class SecurityHardener:
    """Contains all hardening logic, utilizing the SystemManager."""
    def __init__(self, sys_mgr: SystemManager):
        self.sys = sys_mgr

    def update_and_patch(self):
        """Updates packages and configures unattended upgrades."""
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
        else:
            # Fallback for others
            update_cmd = {"suse": "zypper update -y", "arch": "pacman -Syu --noconfirm", "alpine": "apk upgrade"}.get(self.sys.ctx.os_family, "")
            if update_cmd:
                self.sys.run(update_cmd)
                self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": "System updated (Auto-patching not supported for this OS)"})

    def configure_user(self):
        """Creates a new user and grants sudo privileges."""
        user = self.sys.ctx.new_user
        if not user:
            self.sys.ctx.report_log.append({"status": "SKIP", "msg": "User creation skipped"})
            return

        check_user = self.sys.run(f"id {user}", ignore_error=True)
        if hasattr(check_user, 'returncode') and check_user.returncode == 0:
             self.sys.ctx.report_log.append({"status": "SKIP", "msg": f"User '{user}' already exists"})
             return

        if not self.sys.ctx.dry_run:
            self.sys.run(f"adduser --disabled-password --gecos '' {user}", ignore_error=True)
            
            if self.sys.ctx.os_family == "debian":
                self.sys.run(f"usermod -aG sudo {user}")
            elif self.sys.ctx.os_family in ["rhel", "arch", "suse"]:
                self.sys.run(f"usermod -aG wheel {user}")
        
        self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": f"User '{user}' created and added to admin group"})

    def harden_ssh(self):
        cfg = "/etc/ssh/sshd_config"
        if not os.path.exists(cfg):
            return

        settings = {
            "PermitRootLogin": "no",
            "PasswordAuthentication": "no",
            "PubkeyAuthentication": "yes",
            "X11Forwarding": "no",
            "MaxAuthTries": "3"
        }
        
        if not self.sys.ctx.dry_run:
            with open(cfg, "r") as f:
                lines = f.readlines()
            
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
                if not matched:
                    new_lines.append(line)
            
            for k, v in settings.items():
                if k not in applied:
                    new_lines.append(f"\n{k} {v}\n")
                    
            with open(cfg, "w") as f:
                f.writelines(new_lines)
            
            self.sys.restart_service("sshd" if self.sys.ctx.os_family in ["rhel", "arch", "suse"] else "ssh")
            
        self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": "SSH Secured (Root disabled, PubKey forced)"})

    def configure_fail2ban(self):
        pm = self.sys.ctx.pkg_manager
        install_cmd = f"{pm} install -y fail2ban" if self.sys.ctx.os_family != "alpine" else f"{pm} add fail2ban"
        self.sys.run(install_cmd, ignore_error=True)

        if not self.sys.ctx.dry_run and os.path.exists("/etc/fail2ban/jail.conf"):
            self.sys.run("cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local")
            self.sys.run("sed -i 's/bantime  = 10m/bantime  = 1h/g' /etc/fail2ban/jail.local")
            self.sys.run("sed -i 's/maxretry = 5/maxretry = 3/g' /etc/fail2ban/jail.local")
            self.sys.restart_service("fail2ban")
            
        self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": "Fail2Ban Configured (1h ban, 3 retries)"})

    def configure_firewall(self):
        """Sets up Docker-safe firewall depending on the OS."""
        port = self.sys.ctx.ssh_port
        
        if self.sys.ctx.os_family == "debian":
            self._setup_ufw(port)
        elif self.sys.ctx.os_family in ["rhel", "suse"]:
            self._setup_firewalld(port)
        else:
            self.sys.ctx.report_log.append({"status": "SKIP", "msg": f"Firewall setup skipped for OS: {self.sys.ctx.os_family}"})

    def _setup_ufw(self, ssh_port: str):
        pm = self.sys.ctx.pkg_manager
        self.sys.run(f"{pm} install -y ufw", ignore_error=True)

        if not self.sys.ctx.dry_run:
            self.sys.run("ufw --force reset")
            self.sys.run("ufw default deny incoming")
            self.sys.run("ufw default allow outgoing")
            self.sys.run(f"ufw allow {ssh_port}/tcp comment 'SSH'")
            self.sys.run("ufw allow 80/tcp comment 'HTTP'")
            self.sys.run("ufw allow 443/tcp comment 'HTTPS'")

            # Docker UFW Bypass Fix (Injecting to after.rules)
            if shutil.which("docker"):
                after_rules = "/etc/ufw/after.rules"
                if os.path.exists(after_rules):
                    with open(after_rules, "r") as f:
                        content = f.read()
                    
                    if "# BEGIN UFW AND DOCKER" not in content:
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
                        with open(after_rules, "a") as f:
                            f.write(docker_patch)
                        self.sys.ctx.report_log.append({"status": "INFO", "msg": "Docker UFW isolation rules injected."})

            self.sys.run("ufw --force enable")
            
        self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": f"UFW Firewall sealed. Ports Open: {ssh_port}, 80, 443"})

    def _setup_firewalld(self, ssh_port: str):
        pm = self.sys.ctx.pkg_manager
        self.sys.run(f"{pm} install -y firewalld", ignore_error=True)

        if not self.sys.ctx.dry_run:
            self.sys.run("systemctl enable firewalld --now")
            self.sys.run("firewall-cmd --permanent --zone=public --remove-service=ssh", ignore_error=True)
            self.sys.run(f"firewall-cmd --permanent --zone=public --add-port={ssh_port}/tcp")
            self.sys.run("firewall-cmd --permanent --zone=public --add-port=80/tcp")
            self.sys.run("firewall-cmd --permanent --zone=public --add-port=443/tcp")
            self.sys.run("firewall-cmd --reload")
            
        self.sys.ctx.report_log.append({"status": "SUCCESS", "msg": f"Firewalld sealed. Ports Open: {ssh_port}, 80, 443"})

# ──────────────────────────────────────────────────────────────────────────────
# UX & DASHBOARD
# ──────────────────────────────────────────────────────────────────────────────
def display_dashboard(ctx: HardeningContext):
    table = Table(title="[bold blue]Security Operations Summary[/bold blue]")
    table.add_column("Status", justify="center", style="cyan", no_wrap=True)
    table.add_column("Task / Operation", style="magenta")

    for entry in ctx.report_log:
        status = entry["status"]
        if status == "SUCCESS":
            color = "[green]✔[/green]"
        elif status == "ERROR":
            color = "[red]✖[/red]"
        elif status == "DRY-RUN":
            color = "[blue]🥽[/blue]"
        elif status == "SKIP":
            color = "[dim]↷[/dim]"
        else:
            color = "[yellow]ℹ[/yellow]"
        
        table.add_row(color, entry["msg"])

    console.print("\n")
    console.print(table)

# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────
def main():
    if os.geteuid() != 0:
        console.print("[bold red]✖ Root privileges required. Run with sudo.[/bold red]")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Linux Hardening Tool v4.0 (Enterprise)")
    parser.add_argument("--dry-run", action="store_true", help="Simulate changes without applying them.")
    parser.add_argument("--restore", type=str, metavar="ARCHIVE", help="Restore system from a specific .tar.gz snapshot.")
    args = parser.parse_args()

    ctx = HardeningContext(dry_run=args.dry_run)
    sys_mgr = SystemManager(ctx)
    backup_mgr = BackupManager(sys_mgr)
    hardener = SecurityHardener(sys_mgr)

    sys_mgr.detect_os()

    if args.restore:
        backup_mgr.restore_snapshot(args.restore)

    # UI Banner
    console.print(Panel.fit(
        f"[bold cyan]Linux Post-Install Hardening v4.0[/bold cyan]\n"
        f"OS Detected: [bold]{ctx.os_family.upper()}[/bold]\n"
        f"Mode: {'[bold blue]DRY-RUN[/bold blue]' if ctx.dry_run else '[bold red]LIVE[/bold red]'}",
        border_style="cyan"
    ))

    # Pre-flight Prompts
    new_user_input = Prompt.ask("[yellow]Enter a new admin username (Leave blank to skip)[/yellow]", default="")
    ctx.new_user = new_user_input.strip()

    ssh_port_input = Prompt.ask("[yellow]Enter your exact SSH Port (Used for Firewall configuration)[/yellow]", default="22")
    if ssh_port_input.isdigit() and 1 <= int(ssh_port_input) <= 65535:
        ctx.ssh_port = ssh_port_input
    else:
        console.print("[red]Invalid port. Defaulting to 22.[/red]")
        ctx.ssh_port = "22"

    if not Confirm.ask("Do you want to proceed with hardening?"):
        console.print("Aborted.")
        sys.exit(0)

    # 1. Backup Phase
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        task1 = progress.add_task("[yellow]Creating system snapshot...", total=None)
        backup_mgr.create_snapshot()
        time.sleep(1) # UX purpose
        progress.update(task1, completed=100)

    # 2. Hardening Phase
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task_update = progress.add_task("[cyan]Updating System & Configuring Auto-Patches...", total=None)
        hardener.update_and_patch()
        progress.update(task_update, completed=100)
        
        task_user = progress.add_task("[cyan]Setting up Admin User...", total=None)
        hardener.configure_user()
        progress.update(task_user, completed=100)

        task_ssh = progress.add_task("[cyan]Securing SSH Configuration...", total=None)
        hardener.harden_ssh()
        progress.update(task_ssh, completed=100)

        task_f2b = progress.add_task("[cyan]Configuring Anti-Bruteforce (Fail2Ban)...", total=None)
        hardener.configure_fail2ban()
        progress.update(task_f2b, completed=100)

        task_fw = progress.add_task("[cyan]Setting up Docker-Safe Firewall...", total=None)
        hardener.configure_firewall()
        progress.update(task_fw, completed=100)

    # 3. Final Report
    display_dashboard(ctx)

if __name__ == "__main__":
    main()

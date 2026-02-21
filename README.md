
# 🛡️ IronTux: Enterprise Offline Linux Hardening Tool

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![OS Support](https://img.shields.io/badge/OS-Debian%20%7C%20Ubuntu%20%7C%20RHEL%20%7C%20Arch%20%7C%20Alpine-success)
![License](https://img.shields.io/badge/license-MIT-green)

**IronTux** is a powerful, offline, and Object-Oriented Programming (OOP) based Python script designed to secure fresh Linux installations (VPS or Homelab) in seconds. It specializes in sealing your server against brute-force attacks, patching the infamous **Docker firewall bypass** issue, and applying kernel-level network security.

## 🎯 Purpose & Why You Need It
When you install Docker, it silently bypasses `ufw` or `iptables` to expose your container ports to the entire internet. IronTux automatically patches this critical vulnerability. Furthermore, securing a Linux server manually takes hours of configuring SSH, Fail2Ban, Sysctl, and Firewalls. IronTux automates this entire process with a 1-click rollback system—all while providing a beautiful terminal UI and advanced CLI customizations.

---

## ✨ Key Features

*   **🛡️ Multi-Distro Support & OS Auto-Detection**
    *   Automatically adapts to **Debian, Ubuntu, RHEL, CentOS, Rocky, SUSE, Arch,** and **Alpine** Linux.
    *   Dynamically selects the correct package manager (`apt`, `dnf`, `zypper`, `pacman`, `apk`).

*   **🐳 Docker-Safe Firewall Automation**
    *   **Docker Port Leak Fix:** Automatically injects custom `DOCKER-USER` iptables rules into UFW to prevent Docker from exposing internal container ports to the public internet.
    *   Implements a strict "Default Deny" policy.
    *   **Custom Ports:** Interactively allows you to open additional custom ports (e.g., `8080/tcp`, `51820/udp`) alongside standard web and SSH ports.

*   **⚙️ Deep Kernel Hardening (`sysctl`)**
    *   Enables **TCP SYN Cookies** to mitigate SYN flood DDoS attacks.
    *   Enables **Reverse Path Filtering (RP Filter)** to prevent IP spoofing.
    *   Disables **ICMP Redirects** to prevent MITM routing attacks.
    *   Enables **ASLR** (Address Space Layout Randomization) to protect against buffer overflow exploits.

*   **🔐 Zero-Trust SSH Hardening**
    *   Disables vulnerable root logins (`PermitRootLogin no`).
    *   Enforces Public Key Authentication (`PasswordAuthentication no`).
    *   Disables `X11Forwarding` and limits `MaxAuthTries` to 3.

*   **🔄 Automated Patching & Anti-Bruteforce**
    *   **Auto-Updates:** Updates packages and configures `unattended-upgrades` (Debian) or `dnf-automatic` (RHEL) for silent background patching.
    *   **Fail2Ban:** Installs and configures brute-force protection out of the box (1-hour ban after 3 failed login retries).

*   **🔍 Post-Hardening Service Verification**
    *   Actively verifies if critical services (`sshd`, `fail2ban`, `ufw`/`firewalld`) are successfully running after configuration changes are made, alerting you instantly if something crashes.

*   **⏪ 1-Click Rollback & System Snapshots**
    *   Before executing any changes, the script creates a `.tar.gz` backup archive of all critical configuration files (`sshd_config`, `ufw rules`, `fstab`, etc.).
    *   Instantly revert your system to its previous state with a single command.

---

## 🚀 How to Use

### 1. Prerequisites
Make sure you have Python 3 and the `rich` UI library installed:

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install python3-pip
sudo pip3 install rich

# RHEL/CentOS/Rocky
sudo dnf install python3-pip
sudo pip3 install rich
```

### 2. Standard Execution
Clone the repository and run the script as root:

```bash
git clone https://github.com/YOUR_USERNAME/irontux.git
cd irontux
sudo python3 IronTux.py
```

### 3. Dry-Run (Test Mode)
Want to see what the script *would* do without changing anything on your system?
```bash
sudo python3 IronTux.py --dry-run
```

---

## 🛠️ Advanced CLI Customization
Are you an advanced user who only wants to apply specific hardening modules? IronTux supports CLI flags to skip certain operations:

```bash
# Skip system updates and patching
sudo python3 IronTux.py --no-update

# Harden everything EXCEPT the firewall (useful if you use a cloud provider's external firewall)
sudo python3 IronTux.py --skip-fw

# Skip SSH configuration (useful if you already configured it manually)
sudo python3 IronTux.py --skip-ssh

# Combine flags: Only apply Sysctl, User creation, and SSH Hardening
sudo python3 IronTux.py --no-update --skip-fw --skip-f2b
```

---

## ⏪ Restoring from Backup
Made a mistake or locked yourself out? IronTux takes a snapshot of your system right before execution. You can easily restore your previous state:

```bash
sudo python3 IronTux.py --restore /var/backups/hardening_tool/snapshot_YYYYMMDD_HHMMSS.tar.gz
```
*(This automatically extracts the old configuration files and restarts `sshd`, `fail2ban`, and your firewall instantly).*

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! 

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.

---
*Built with ❤️ for secure homelabs and peaceful nights.*
```

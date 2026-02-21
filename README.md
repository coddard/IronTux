
# 🛡️ IronTux: Enterprise Offline Linux Hardening Tool

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![OS](https://img.shields.io/badge/OS-Debian%20%7C%20Ubuntu%20%7C%20RHEL%20%7C%20Arch%20%7C%20Alpine-success)
![License](https://img.shields.io/badge/license-MIT-green)

**IronTux** is a powerful, offline, and Object-Oriented Programming (OOP) based Python script designed to secure fresh Linux installations (VPS or Homelab) in seconds. It specializes in sealing your server against brute-force attacks and patching the infamous **Docker firewall bypass** issue.

When you install Docker, it silently bypasses `ufw` or `iptables` to expose your container ports to the entire internet. IronTux automatically patches this vulnerability, hardens your SSH, configures Fail2Ban, updates your system, creates a secure admin user, and implements a 1-click rollback system—all while providing a beautiful terminal UI.

---

## ✨ Features

*   **🛡️ Multi-Distro Support & OS Auto-Detection**
    *   Automatically adapts to **Debian, Ubuntu, RHEL, CentOS, Rocky, SUSE, Arch,** and **Alpine** Linux.
    *   Dynamically selects the correct package manager (`apt`, `dnf`, `zypper`, `pacman`, `apk`).

*   **🔄 Automated Patching & Updates**
    *   Updates all system packages to their latest secure versions automatically.
    *   Installs and configures `unattended-upgrades` (Debian) or `dnf-automatic` (RHEL) for silent background patching.

*   **👤 Secure Admin User Creation**
    *   Provides an interactive prompt to create a new non-root admin user.
    *   Automatically assigns the user to the `sudo` (Debian) or `wheel` (RHEL/Arch) group.

*   **🔐 Deep SSH Hardening**
    *   Disables vulnerable root logins (`PermitRootLogin no`).
    *   Enforces Public Key Authentication (`PasswordAuthentication no`).
    *   Disables `X11Forwarding` and limits `MaxAuthTries` to 3.

*   **🛑 Automated Anti-Bruteforce Defense**
    *   Installs and configures `Fail2Ban` out of the box (1-hour ban after 3 failed login retries).

*   **🐳 Docker-Safe Firewall Automation**
    *   **Docker Port Leak Fix:** Automatically injects custom `DOCKER-USER` iptables rules into UFW to prevent Docker from exposing internal container ports to the public internet.
    *   Only opens essential web ports (`80/HTTP`, `443/HTTPS`) and your custom, user-defined SSH port.
    *   Supports both `UFW` (Debian-based) and `Firewalld` (RHEL-based).

*   **⏪ 1-Click Rollback & System Snapshots**
    *   Before executing any changes, the script creates a `.tar.gz` backup archive of all critical configuration files (SSH, UFW, Firewalld, Fail2Ban, etc.).
    *   Instantly revert your system to its previous state with a single command.

*   **🎨 Developer & UX Friendly**
    *   **100% Offline Execution:** Performs all hardening operations locally without making external API calls.
    *   **Dry-Run Mode:** Simulate operations and view intended changes without modifying your system.
    *   **Rich Terminal UI:** Displays interactive progress bars and a final operation summary dashboard using the `rich` library.

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

### 2. Run the Script
Clone the repository and run the script as root:

```bash
git clone https://github.com/YOUR_USERNAME/irontux.git
cd irontux
sudo python3 IronTux.py
```

### 3. Dry-Run (Test Mode)
Want to see what the script *would* do without changing anything? Run it in dry-run mode:

```bash
sudo python3 IronTux.py --dry-run
```

---

## ⏪ Restoring from Backup

Made a mistake or locked yourself out? IronTux takes a snapshot of your system right before execution. You can easily restore your previous state:

```bash
sudo python3 IronTux.py --restore /var/backups/hardening_tool/snapshot_YYYYMMDD_HHMMSS.tar.gz
```
*(This restores SSH, Fail2Ban, UFW/Firewalld configs, and restarts the services instantly).*

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

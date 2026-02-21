
# 🛡️ IronTux: The Ultimate Linux & Docker Hardening Tool

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![OS](https://img.shields.io/badge/OS-Debian%20%7C%20Ubuntu%20%7C%20RHEL%20%7C%20Alpine%20%7C%20Arch-success)
![License](https://img.shields.io/badge/license-MIT-green)

**IronTux** is a powerful, offline, and OOP-based Python script designed to secure fresh Linux installations (VPS or Homelab) in seconds. It specializes in sealing your server against brute-force attacks and fixing the infamous **Docker firewall bypass** issue.

## 🎯 Why use this?
When you install Docker, it silently bypasses `ufw` or `iptables` to expose your container ports to the entire internet. IronTux automatically patches this vulnerability, hardens your SSH, configures Fail2Ban, and applies kernel-level network security—all while providing a beautiful terminal UI and automated rollback backups.

---

## ✨ Features

- 🐳 **Docker-Safe Firewall:** Automatically injects `ufw-docker` rules. Expose containers safely without leaking ports!
- 🧱 **Multi-Distro Support:** Detects your OS and uses the right tools (Debian/Ubuntu, RHEL/Rocky, Alpine, Arch, SUSE).
- 🔐 **SSH Sealing:** Disables root login, enforces PubKey authentication, and sets auth limits.
- 🛑 **Anti-Bruteforce:** Installs and configures `Fail2Ban` out of the box (1h ban, 3 retries).
- 🧠 **Kernel Hardening:** Modifies `sysctl.conf` to prevent IP spoofing, MITM, and enables ASLR.
- ⏪ **1-Click Rollback:** Creates a `.tar.gz` snapshot of your critical config files BEFORE applying changes. 
- 🥽 **Dry-Run Mode:** Simulate changes without actually modifying your system.

---

## 🚀 Quick Start

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
git clone https://github.com/coddard/IronTux/
cd irontux
sudo python3 IronTux.py
```

### 3. Dry-Run (Test Mode)
Want to see what the script *would* do without changing anything?
```bash
sudo python3 IronTux.py --dry-run
```

---

## ⏪ Restoring from Backup

Made a mistake? Locked yourself out? IronTux takes a snapshot of your system right before execution. You can easily restore your previous state:

```bash
sudo python3 IronTux.py --restore /var/backups/hardening_tool/snapshot_20260222_125000.tar.gz
```
*(This restores SSH, Fail2Ban, UFW/Firewalld configs, and restarts the services instantly).*

---

## 🏗️ Architecture & Clean Code
This script is written using **Object-Oriented Programming (OOP)** principles. 
- No spaghetti global variables.
- Modular `SecurityHardener` and `SystemManager` classes.
- Robust exception catching and user-friendly error logs.
- Fully offline. No external web requests are made during hardening.

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](../../issues). 

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


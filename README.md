# AllStarLink Status OLED

A Python application and system daemon to display the real-time status of your AllStarLink (ASL) radio node on an I2C SSD1306 OLED screen. It supports both **128x64** and **128x32** display resolutions, features live TX/RX wave animations, and provides an interactive terminal CLI dashboard.

---

## 👤 Credits & Inspiration

* **Developer:** Faisal Faruque Rafat (S21NET)
* **Inspiration:** Inspired by the work of [fahadmieaji/digi-gate-oled](https://github.com/fahadmieaji/digi-gate-oled).

---

## ✨ Features

* **Dual-Resolution Support:** Full compatibility with 128x64 and 128x32 OLED screens.
* **Auto-Rotating Screen Carousel:** Displays current Callsign, Node Number, Connected Links, and System Diagnostics (CPU Temp, RAM Usage, Uptime, WiFi, WARP Status).
* **Immersive RX/TX Animations:** Dynamically switches to a wave animation screen when the radio is actively transmitting (TX) or receiving (RX).
* **Terminal CLI Dashboard:** Run `allstarlink-status-oled` to see a Neofetch-style ASCII diagnostic panel in your SSH session.
* **Real-time Shell Monitor:** Monitor live node status continuously in your console using `allstarlink-status-oled --watch`.
* **Conflict Prevention:** Installer automatically handles stopping and disabling overlapping display managers (e.g., `digi-gate.service`).

---

## 📋 Prerequisites

Before installing, ensure that:
1. **I2C is enabled** on your Raspberry Pi (run `sudo raspi-config` > Interface Options > I2C).
2. The display is wired to the standard I2C pins.
3. System dependencies are installed:
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-pip python3-dev build-essential libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7 libtiff6 git
   ```

---

## 🚀 Installation & Setup

### Method 1: The Interactive One-Liner (Recommended - No Git/Unzip required)
Copy and run either of these commands in your terminal to download and execute the interactive setup script directly:

Using **curl**:
```bash
bash <(curl -sSL https://raw.githubusercontent.com/ffrafat/allstarlink-status-oled/main/install.sh)
```

Using **wget**:
```bash
bash <(wget -qO- https://raw.githubusercontent.com/ffrafat/allstarlink-status-oled/main/install.sh)
```

### Method 2: Git Clone
Alternatively, you can clone the repository manually:
```bash
git clone https://github.com/ffrafat/allstarlink-status-oled.git
cd allstarlink-status-oled
chmod +x install.sh
sudo ./install.sh
```

3. **Interactive Configuration Wizard:**
   During installation, the terminal will prompt you to enter the following variables:
   
   | Parameter | Default | Description |
   | :--- | :---: | :--- |
   | **Callsign** | `MYCALL` | Your amateur radio callsign (automatically capitalized). |
   | **Node Number** | `1234` | The AllStarLink node number to monitor. |
   | **Screen Rotation** | `0` | Rotate display output (`0` = 0°, `1` = 90°, `2` = 180°, `3` = 270°). |
   | **I2C Address** | `0x3C` | The hardware address of your SSD1306 (commonly `0x3C` or `0x3D`). |
   | **OLED Resolution** | `128x64` | Select `1` for 128x64 displays, or `2` for 128x32 displays. |

   > [!TIP]
   > Press **Enter** on any prompt to keep the default value or use your previously configured settings.

---

## 🖥️ Terminal CLI Dashboard

You can monitor your node directly inside terminal SSH sessions using the `allstarlink-status-oled` CLI tool.

### Single Report (Neofetch Style)
```bash
allstarlink-status-oled
```
Outputs a colored ASCII status layout:
```text
       *             AllStarLink Status Dashboard
      / \            ----------------------------
     /   \           Callsign    : S21NET
    /  o  \          Node Number : 1234
   /  / \  \         Node Status : IDLE
  |  |   |  |        Active Links: None
  |  |===|  |        CPU Temp    : 43.5°C
  |  |   |  |        RAM Usage   : 18% [█░░░░░░░░░]
 /   |   |   \       WiFi Signal : 85% [████████░░]
/____|___|____\      System Uptime: 2D 14H
                     OLED Setup   : 128x64 (I2C: 0x3C), Mode: LOCAL
```

### Live Terminal Monitor (Watch Mode)
To view stats refreshing dynamically in real-time every second:
```bash
allstarlink-status-oled --watch
```
*Press `Ctrl+C` to exit watch mode.*

---

## ⚙️ Post-Install Configuration

If you ever need to change your callsign, node number, rotation, address, or resolution settings later, you do not need to reinstall. Simply run:
```bash
sudo python3 /opt/allstarlink-status-oled/setup.py
```
This updates the configuration and automatically applies the settings on the next service check.

---

## 🧹 Uninstallation

To remove all binaries, symlinks, configurations, and systemd services cleanly:
```bash
chmod +x uninstall.sh
./uninstall.sh
```

# AllStarLink Status OLED

A Python application and system daemon to display the real-time status of your AllStarLink (ASL) radio node on an I2C SSD1306 OLED screen (supporting both 128x64 and 128x32 displays). 

It also includes a terminal dashboard mimicking the OLED display output with live watch mode.

## Features

- **OLED Display support:** Automatically rotates between system stats, connected node count, active links, and callsign.
- **Dynamic RX/TX animations:** Immersive live wave/signal screens when transmitting (TX) or receiving (RX).
- **Terminal CLI Dashboard:** Run `allstarlink-status-oled` to see a Neofetch-style system report in your shell, or run with `-w` / `--watch` for real-time monitoring.
- **Interactive Installer:** Simple setup workflow that configures I2C address, rotation, node number, callsign, and screen resolution.

## Installation

Run the installer script:
```bash
./install.sh
```

During installation, you will be prompted for:
1. Callsign
2. Node Number
3. Screen Rotation
4. I2C Address
5. OLED Resolution (128x64 or 128x32)

The installer will stop and disable conflicting services (e.g., `digi-gate.service`), register the status daemon under systemd, and start it automatically.

## CLI Usage

To view a status report directly in your terminal:
```bash
allstarlink-status-oled
```

For live continuous terminal monitoring (refreshes every second):
```bash
allstarlink-status-oled --watch
```

## Re-Configuration

To change parameters later without reinstalling, run the setup tool:
```bash
sudo python3 /opt/allstarlink-status-oled/setup.py
```

## Uninstallation

To remove all files and system service:
```bash
./uninstall.sh
```

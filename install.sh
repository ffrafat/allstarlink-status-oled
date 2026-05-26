#!/bin/bash

set -e

echo "Installing Allstarlink Status OLED..."

# Stop known conflicting service
if systemctl list-unit-files | grep -q digi-gate.service; then

    echo "Disabling digi-gate.service..."

    sudo systemctl stop digi-gate.service || true
    sudo systemctl disable digi-gate.service || true
fi

# Create install directory
sudo mkdir -p /opt/allstarlink-status-oled

# Copy files
sudo cp src/main.py /opt/allstarlink-status-oled/main.py
sudo cp src/setup.py /opt/allstarlink-status-oled/setup.py
sudo cp src/cli.py /opt/allstarlink-status-oled/cli.py

# Set executable permissions for CLI
sudo chmod +x /opt/allstarlink-status-oled/cli.py

# Create system symlink for easy access
sudo ln -sf /opt/allstarlink-status-oled/cli.py /usr/local/bin/allstarlink-status-oled

# Run configuration setup
sudo python3 /opt/allstarlink-status-oled/setup.py

# Install service
sudo cp service/allstarlink-status-oled.service /etc/systemd/system/

# Permissions
sudo chmod 644 /etc/systemd/system/allstarlink-status-oled.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable allstarlink-status-oled.service

# Restart service
sudo systemctl restart allstarlink-status-oled.service

echo ""
echo "Allstarlink Status OLED installed successfully."
echo ""
echo "IMPORTANT:"
echo "Only one OLED manager should run at a time."
echo ""
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

REPO_URL="https://raw.githubusercontent.com/ffrafat/allstarlink-status-oled/main"

# Copy files
if [ -d "src" ]; then
    sudo cp src/main.py /opt/allstarlink-status-oled/main.py
    sudo cp src/setup.py /opt/allstarlink-status-oled/setup.py
    sudo cp src/cli.py /opt/allstarlink-status-oled/cli.py
else
    echo "Local source files not found. Downloading files from GitHub..."
    if command -v curl >/dev/null 2>&1; then
        sudo curl -sSL "$REPO_URL/src/main.py" -o /opt/allstarlink-status-oled/main.py
        sudo curl -sSL "$REPO_URL/src/setup.py" -o /opt/allstarlink-status-oled/setup.py
        sudo curl -sSL "$REPO_URL/src/cli.py" -o /opt/allstarlink-status-oled/cli.py
    elif command -v wget >/dev/null 2>&1; then
        sudo wget -q "$REPO_URL/src/main.py" -O /opt/allstarlink-status-oled/main.py
        sudo wget -q "$REPO_URL/src/setup.py" -O /opt/allstarlink-status-oled/setup.py
        sudo wget -q "$REPO_URL/src/cli.py" -O /opt/allstarlink-status-oled/cli.py
    else
        echo "Error: Neither curl nor wget is installed."
        exit 1
    fi
fi

# Set executable permissions for CLI
sudo chmod +x /opt/allstarlink-status-oled/cli.py

# Create system symlink for easy access
sudo ln -sf /opt/allstarlink-status-oled/cli.py /usr/local/bin/allstarlink-status-oled

# Run configuration setup
sudo python3 /opt/allstarlink-status-oled/setup.py

# Install service
if [ -d "service" ]; then
    sudo cp service/allstarlink-status-oled.service /etc/systemd/system/
else
    if command -v curl >/dev/null 2>&1; then
        sudo curl -sSL "$REPO_URL/service/allstarlink-status-oled.service" -o /etc/systemd/system/allstarlink-status-oled.service
    else
        sudo wget -q "$REPO_URL/service/allstarlink-status-oled.service" -O /etc/systemd/system/allstarlink-status-oled.service
    fi
fi

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
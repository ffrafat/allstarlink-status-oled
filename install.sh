#!/bin/bash

set -e

echo "Installing AllStarLink Status OLED..."

# Stop known conflicting service
if systemctl list-unit-files | grep -q digi-gate.service; then
    echo "Disabling digi-gate.service..."
    sudo systemctl stop digi-gate.service || true
    sudo systemctl disable digi-gate.service || true
fi

# Install dependencies
echo "Installing system dependencies (this may take a minute)..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-pil python3-dev build-essential libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7 libtiff6 git

echo "Installing Python library dependencies..."
# Install luma.oled system-wide. Uses --break-system-packages for Debian Bookworm (PEP 668), 
# with a fallback to standard pip install for older OS versions.
if ! sudo pip3 install luma.oled --break-system-packages 2>/dev/null; then
    sudo pip3 install luma.oled || true
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
#!/bin/bash

set -e

echo "Updating Allstarlink Status OLED..."

TMP_DIR="/tmp/allstarlink-status-oled"

rm -rf "$TMP_DIR"

git clone https://github.com/ffrafat/allstarlink-status-oled.git "$TMP_DIR"

cd "$TMP_DIR"

sudo cp src/main.py /opt/allstarlink-status-oled/main.py
sudo cp src/setup.py /opt/allstarlink-status-oled/setup.py
sudo cp src/cli.py /opt/allstarlink-status-oled/cli.py

sudo chmod +x /opt/allstarlink-status-oled/cli.py
sudo ln -sf /opt/allstarlink-status-oled/cli.py /usr/local/bin/allstarlink-status-oled

sudo systemctl restart allstarlink-status-oled.service

echo "Update complete."
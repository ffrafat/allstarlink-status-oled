#!/bin/bash

set -e

echo "Removing Allstarlink Status OLED..."

sudo systemctl stop allstarlink-status-oled.service || true
sudo systemctl disable allstarlink-status-oled.service || true

sudo rm -f /etc/systemd/system/allstarlink-status-oled.service
sudo rm -f /usr/local/bin/allstarlink-status-oled

sudo rm -rf /opt/allstarlink-status-oled

sudo systemctl daemon-reload

echo "Allstarlink Status OLED removed."
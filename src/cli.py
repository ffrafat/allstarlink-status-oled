#!/usr/bin/env python3
import sys
import os
import time
import argparse
import re

# Allow importing from the installation directory
sys.path.append("/opt/allstarlink-status-oled")

try:
    import main
except ImportError:
    # Fallback to local import if running from repo directory
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
    try:
        import main
    except ImportError:
        print("Error: Could not import main.py. Make sure the software is installed.")
        sys.exit(1)

# ANSI Colors
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YELLOW = "\033[93m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"

# ASCII Logo (Radio Tower / Antenna)
LOGO = [
    f"       {C_BLUE}*{C_RESET}",
    f"      {C_BLUE}/ \\{C_RESET}",
    f"     {C_BLUE}/   \\{C_RESET}",
    f"    {C_BLUE}/  {C_CYAN}o{C_BLUE}  \\{C_RESET}",
    f"   {C_BLUE}/  / \\  \\{C_RESET}",
    f"  {C_BLUE}|  |   |  |{C_RESET}",
    f"  {C_BLUE}|  |{C_CYAN}==={C_BLUE}|  |{C_RESET}",
    f"  {C_BLUE}|  |   |  |{C_RESET}",
    f" {C_BLUE}/   |   |   \\{C_RESET}",
    f"{C_BLUE}/____|___|____\\{C_RESET}"
]

def visible_len(text):
    # Strips ANSI escape sequences to compute printable length
    return len(re.sub(r'\033\[[0-9;]*[a-zA-Z]', '', text))

def pad_visible(text, width):
    v_len = visible_len(text)
    padding = " " * max(0, width - v_len)
    return text + padding

def make_bar(percentage):
    filled = int(percentage / 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"{percentage}% {C_BLUE}[{bar}]{C_RESET}"

def get_stats():
    # Load config and read current statuses
    config = main.load_config()
    callsign = config.get("callsign", "MYCALL")
    node = config.get("node", "1234")
    
    asl_ready = main.is_asterisk_ready()
    
    rx, tx, remotes = False, False, []
    if asl_ready:
        rx, tx, remotes = main.get_node_status()
        
    status_text = f"{C_YELLOW}IDLE{C_RESET}"
    if not asl_ready:
        status_text = f"{C_RED}STARTING / OFFLINE{C_RESET}"
    elif tx:
        status_text = f"{C_RED}{C_BOLD}TRANSMITTING (TX){C_RESET}"
    elif rx:
        active = remotes[0] if remotes else "Unknown"
        status_text = f"{C_GREEN}{C_BOLD}RECEIVING (RX from {active}){C_RESET}"
        
    links_text = ", ".join(remotes) if remotes else "None"
    
    temp = main.get_cpu_temp()
    ram = main.get_ram_usage()
    uptime = main.get_uptime()
    wifi = main.get_wifi_strength()
    warp = main.get_warp_status()
    i2c_addr = config.get("i2c_address", "0x3C")
    resolution = config.get("resolution", "128x64")
    
    info_lines = [
        f"{C_CYAN}{C_BOLD}AllStarLink Status Dashboard{C_RESET}",
        f"{C_CYAN}----------------------------{C_RESET}",
        f"{C_BOLD}Callsign{C_RESET}    : {C_GREEN}{callsign}{C_RESET}",
        f"{C_BOLD}Node Number{C_RESET} : {C_GREEN}{node}{C_RESET}",
        f"{C_BOLD}Node Status{C_RESET} : {status_text}",
        f"{C_BOLD}Active Links{C_RESET}: {C_YELLOW}{links_text}{C_RESET}",
        f"{C_BOLD}CPU Temp{C_RESET}    : {C_GREEN}{temp}°C{C_RESET}",
        f"{C_BOLD}RAM Usage{C_RESET}   : {make_bar(ram)}",
        f"{C_BOLD}WiFi Signal{C_RESET} : {make_bar(wifi)}",
        f"{C_BOLD}System Uptime{C_RESET}: {C_GREEN}{uptime}{C_RESET}",
        f"{C_BOLD}OLED Setup{C_RESET}   : {C_GREEN}{resolution}{C_RESET} (I2C: {i2c_addr}), Mode: {C_GREEN}{warp}{C_RESET}"
    ]
    return info_lines

def draw_dashboard():
    info = get_stats()
    
    max_lines = max(len(LOGO), len(info))
    for i in range(max_lines):
        logo_part = LOGO[i] if i < len(LOGO) else ""
        logo_display = pad_visible(logo_part, 20)
        info_part = info[i] if i < len(info) else ""
        print(f"{logo_display} {info_part}")
    print()

def main_cli():
    parser = argparse.ArgumentParser(description="AllStarLink OLED Status Terminal Dashboard")
    parser.add_argument("-w", "--watch", action="store_true", help="Monitor real-time status in terminal")
    args = parser.parse_args()
    
    if args.watch:
        try:
            while True:
                # Clear terminal screen using ANSI code
                print("\033[H\033[J", end="")
                draw_dashboard()
                print("Press Ctrl+C to exit watch mode.")
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nExiting watch mode.")
    else:
        draw_dashboard()

if __name__ == "__main__":
    main_cli()

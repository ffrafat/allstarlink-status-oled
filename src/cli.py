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
    try:
        pct = int(percentage)
    except:
        pct = 0
    filled = int(pct / 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"{pct}% {C_BLUE}[{bar}]{C_RESET}"

def get_stats():
    # Load config and read current statuses
    config = main.CONFIG
    callsign = config.get("callsign", "MYCALL")
    node = config.get("node", "1234")
    
    # Check if we have background threads running (e.g. in watch mode)
    if getattr(main, "state", None) is not None:
        sys_info = main.state.get_system_stats()
        asl_info = main.state.get_asl_status()
        
        asl_ready = asl_info["asl_ready"]
        rx = asl_info["rx"]
        tx = asl_info["tx"]
        remotes = asl_info["remotes"]
        
        temp = sys_info["cpu_temp"]
        ram = sys_info["ram_usage"]
        uptime = sys_info["uptime"]
        wifi = sys_info["wifi_strength"]
        warp = sys_info["warp_status"]
    else:
        # Fallback to synchronous queries for single run CLI calls
        asl_ready = main.is_asterisk_ready()
        rx, tx, remotes = False, False, []
        if asl_ready:
            rx, tx, remotes = main.get_node_status()
        temp = main.get_cpu_temp()
        ram = main.get_ram_usage()
        uptime = main.get_uptime()
        wifi = main.get_wifi_strength()
        warp = main.get_warp_status()
        
    status_text = f"{C_YELLOW}IDLE{C_RESET}"
    if not asl_ready:
        status_text = f"{C_RED}STARTING / OFFLINE{C_RESET}"
    elif tx:
        status_text = f"{C_RED}{C_BOLD}TRANSMITTING (TX){C_RESET}"
    elif rx:
        active = remotes[0] if remotes else "Unknown"
        status_text = f"{C_GREEN}{C_BOLD}RECEIVING (RX from {active}){C_RESET}"
        
    links_text = ", ".join(remotes) if remotes else "None"
    i2c_addr = config.get("i2c_address", "0x3C")
    resolution = config.get("resolution", "128x64")
    
    # Unicode Box Border formatting
    width = 46
    box_top = f"{C_BLUE}╭" + "─" * (width + 2) + f"╮{C_RESET}"
    box_middle = f"{C_BLUE}├" + "─" * (width + 2) + f"┤{C_RESET}"
    box_bottom = f"{C_BLUE}╰" + "─" * (width + 2) + f"╯{C_RESET}"
    
    def make_row(label, val, icon=""):
        icon_prefix = f"{icon} " if icon else ""
        label_part = f"{icon_prefix}{label}"
        row_content = f"{C_BOLD}{label_part:<15}{C_RESET}: {val}"
        v_len = visible_len(row_content)
        padding = " " * max(0, width - v_len)
        return f"{C_BLUE}│{C_RESET} {row_content}{padding} {C_BLUE}│{C_RESET}"

    # Center title in header
    title_text = f"{C_CYAN}{C_BOLD}AllStarLink Status Dashboard{C_RESET}"
    title_v_len = visible_len(title_text)
    title_pad = (width - title_v_len) // 2
    title_content = " " * title_pad + title_text
    v_len = visible_len(title_content)
    title_padding = " " * max(0, width - v_len)
    title_row = f"{C_BLUE}│{C_RESET} {title_content}{title_padding} {C_BLUE}│{C_RESET}"
    
    info_lines = [
        box_top,
        title_row,
        box_middle,
        make_row("Callsign", f"{C_GREEN}{callsign}{C_RESET}", "📡"),
        make_row("Node Number", f"{C_GREEN}{node}{C_RESET}", "🔢"),
        make_row("Node Status", status_text, "🚦"),
        make_row("Active Links", f"{C_YELLOW}{links_text}{C_RESET}", "🔗"),
        make_row("CPU Temp", f"{C_GREEN}{temp}°C{C_RESET}", "🌡️"),
        make_row("RAM Usage", make_bar(ram), "⚙️"),
        make_row("WiFi Signal", make_bar(wifi), "📶"),
        make_row("Uptime", f"{C_GREEN}{uptime}{C_RESET}", "⏰"),
        make_row("OLED Setup", f"{C_GREEN}{resolution}{C_RESET} ({i2c_addr}) | Mode: {C_GREEN}{warp}{C_RESET}", "🖥️"),
        box_bottom
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
        # Initialize background state threads to keep updates latency-free
        if hasattr(main, "init_state"):
            main.init_state()
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

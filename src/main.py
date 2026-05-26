import time
import os
import sys
import re
import math
import subprocess
import json

try:
    from luma.core.interface.serial import i2c
    from luma.oled.device import ssd1306
    from luma.core.render import canvas
    from PIL import ImageFont
except ImportError:
    sys.exit(1)

CONFIG_FILE = "/opt/allstarlink-status-oled/config.json"

IDLE_REFRESH = 0.35
ACTIVE_REFRESH = 0.06

SCREEN_ROTATE_INTERVAL = 3

def load_config():

    defaults = {
        "callsign": "MYCALL",
        "node": "1234",
        "rotation": 0,
        "i2c_address": "0x3C"
    }

    if os.path.exists(CONFIG_FILE):

        try:

            with open(CONFIG_FILE, "r") as f:

                config = json.load(f)

                defaults.update(config)

        except:
            pass

    return defaults

CONFIG = load_config()

CALLSIGN = CONFIG["callsign"]
NODE_NUMBER = CONFIG["node"]
ROTATION = int(CONFIG["rotation"])
try:
    I2C_ADDRESS = int(CONFIG.get("i2c_address", "0x3C"), 16)
except:
    I2C_ADDRESS = 0x3C

RESOLUTION = CONFIG.get("resolution", "128x64")
try:
    WIDTH, HEIGHT = map(int, RESOLUTION.split("x"))
except:
    WIDTH, HEIGHT = 128, 64



# =========================================
# FONTS
# =========================================

try:

    FONT_SMALL = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        9
    )

    FONT_MED = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        12
    )

    FONT_BIG = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        18
    )

    FONT_HUGE = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        30
    )

except:

    FONT_SMALL = None
    FONT_MED = None
    FONT_BIG = None
    FONT_HUGE = None

# =========================================
# SYSTEM
# =========================================

def get_wifi_strength():

    try:

        with open("/proc/net/wireless", "r") as f:

            lines = f.readlines()

            for line in lines:

                if 'wlan' in line:

                    parts = line.split()

                    qual = int(parts[2].replace('.', ''))

                    if qual <= 70:
                        return int((qual / 70.0) * 100)

                    return qual

    except:
        pass

    return 0

def get_cpu_temp():

    try:

        out = subprocess.check_output(
            ["vcgencmd", "measure_temp"]
        ).decode()

        return out.replace("temp=", "").split("'")[0]

    except:
        return "--"

def get_ram_usage():

    try:

        out = subprocess.check_output(
            ["free", "-m"]
        ).decode().splitlines()

        mem = out[1].split()

        used = int(mem[2])
        total = int(mem[1])

        return int((used / total) * 100)

    except:
        return 0

def get_uptime():

    try:

        uptime_seconds = float(
            open('/proc/uptime').read().split()[0]
        )

        days = int(uptime_seconds // 86400)

        hours = int(
            (uptime_seconds % 86400) // 3600
        )

        return f"{days}D {hours}H"

    except:
        return "--"

def get_warp_status():

    try:

        out = subprocess.check_output(
            ["warp-cli", "status"],
            stderr=subprocess.DEVNULL
        ).decode().lower()

        if "connected" in out:
            return "WARP"

    except:
        pass

    return "LOCAL"

# =========================================
# ASL
# =========================================

def is_asterisk_ready():

    try:

        out = subprocess.check_output(
            ['sudo', 'asterisk', '-rx', f'rpt xnode {NODE_NUMBER}'],
            stderr=subprocess.STDOUT,
            timeout=1
        ).decode('utf-8')

        return "RPT_ALINKS" in out

    except:
        return False

def get_node_status():

    is_rx = False
    is_tx = False
    remotes = []

    try:

        out = subprocess.check_output(
            ['sudo', 'asterisk', '-rx', f'rpt xnode {NODE_NUMBER}'],
            timeout=1.5
        ).decode('utf-8')

        if "RPT_TXKEYED=1" in out:
            is_tx = True

        if "RPT_RXKEYED=1" in out:
            is_rx = True

        match = re.search(r"RPT_ALINKS=(.*)", out)

        if match:

            links_str = match.group(1).strip()

            parts = links_str.split(',')

            if len(parts) > 1:

                for entry in parts[1:]:

                    if len(entry) > 2:

                        node_id = entry[:-2]

                        if entry[-1] == 'K':
                            is_rx = True

                        remotes.append(node_id)

    except:
        pass

    return is_rx, is_tx, remotes

# =========================================
# DRAW HELPERS
# =========================================

def center_text(draw, text, y, font):

    bbox = draw.textbbox(
        (0, 0),
        text,
        font=font
    )

    width = bbox[2] - bbox[0]

    x = (WIDTH - width) // 2

    draw.text(
        (x, y),
        text,
        fill="white",
        font=font
    )

def draw_wifi(draw, strength):

    x_base = WIDTH - 16
    y_base = 11

    bars = 5 if strength > 80 else \
           4 if strength > 60 else \
           3 if strength > 40 else \
           2 if strength > 20 else \
           1 if strength > 5 else 0

    for i in range(5):

        h = (i + 1) * 2

        x = x_base + (i * 3)

        y = y_base - h

        if i < bars:

            draw.rectangle(
                (x, y, x + 1, y_base),
                fill="white"
            )

def draw_header(draw):

    draw.rectangle(
        (0, 0, WIDTH - 1, 15),
        outline="white"
    )

    warp = get_warp_status()

    wifi = get_wifi_strength()

    draw.text(
        (4, 3),
        warp,
        fill="white",
        font=FONT_SMALL
    )

    wifi_text = f"{wifi}%"

    draw.text(
        (WIDTH - 52, 3),
        wifi_text,
        fill="white",
        font=FONT_SMALL
    )

    draw_wifi(draw, wifi)

def get_link_line(remotes):

    if not remotes:
        return "NO LINKS"

    if len(remotes) == 1:
        return remotes[0]

    if len(remotes) == 2:
        return f"{remotes[0]} ● {remotes[1]}"

    cycle = int(time.time() / 2)

    index = cycle % len(remotes)

    return remotes[index]

# =========================================
# RF ANIMATION
# =========================================

def draw_tx_wave(draw, tick):

    base_y = 16 + (HEIGHT - 16) // 2
    h_scale = max(2, (HEIGHT - 16) // 4)

    for x in range(10, WIDTH - 10, 4):

        value = math.sin((x + tick * 14) * 0.10)

        h = int((value + 1) * h_scale)

        draw.line(
            (x, base_y - h, x, base_y + h),
            fill="white"
        )

def draw_rx_wave(draw, tick):

    center_y = 16 + (HEIGHT - 16) // 2
    pulse_x = int(
        12 + ((tick * 6) % (WIDTH - 24))
    )

    draw.line(
        (12, center_y, WIDTH - 12, center_y),
        fill="white"
    )

    draw.ellipse(
        (
            pulse_x - 3,
            center_y - 3,
            pulse_x + 3,
            center_y + 3
        ),
        outline="white",
        fill="white"
    )

# =========================================
# MAIN
# =========================================

def main(device):

    screens = [
        "default",
        "connected",
        "system",
        "callsign"
    ]

    current_screen = 0

    last_screen_change = time.time()

    tick = 0

    while True:

        temp = get_cpu_temp()

        ram = get_ram_usage()

        uptime = get_uptime()

        asl_ready = is_asterisk_ready()

        rx = False
        tx = False
        remotes = []

        if asl_ready:

            rx, tx, remotes = get_node_status()

        if time.time() - last_screen_change > SCREEN_ROTATE_INTERVAL:

            current_screen = (
                current_screen + 1
            ) % len(screens)

            last_screen_change = time.time()

        with canvas(device) as draw:

            # =====================================
            # STARTUP
            # =====================================

            if not asl_ready:

                if HEIGHT == 32:

                    center_text(
                        draw,
                        "STARTING...",
                        10,
                        FONT_MED
                    )

                else:

                    center_text(
                        draw,
                        "SYSTEM",
                        16,
                        FONT_BIG
                    )

                    center_text(
                        draw,
                        "STARTING",
                        40,
                        FONT_MED
                    )

            # =====================================
            # TX IMMERSIVE
            # =====================================

            elif tx:

                if HEIGHT == 32:

                    center_text(
                        draw,
                        "TX KEYED",
                        2,
                        FONT_SMALL
                    )

                else:

                    center_text(
                        draw,
                        "LOCAL TX",
                        10,
                        FONT_BIG
                    )

                draw_tx_wave(
                    draw,
                    tick
                )

            # =====================================
            # RX IMMERSIVE
            # =====================================

            elif rx:

                active = remotes[0] if remotes else "RX"

                if HEIGHT == 32:

                    center_text(
                        draw,
                        f"RX {active}",
                        2,
                        FONT_SMALL
                    )

                else:

                    center_text(
                        draw,
                        f"RX {active}",
                        10,
                        FONT_BIG
                    )

                draw_rx_wave(
                    draw,
                    tick
                )

            # =====================================
            # NORMAL ROTATION
            # =====================================

            else:

                screen = screens[current_screen]

                if HEIGHT == 32:

                    # ---------------------------------
                    # 32px HEIGHT LAYOUTS
                    # ---------------------------------

                    if screen == "default":

                        center_text(
                            draw,
                            f"NODE {NODE_NUMBER}",
                            2,
                            FONT_MED
                        )

                        center_text(
                            draw,
                            "STATUS: IDLE",
                            18,
                            FONT_MED
                        )

                    elif screen == "connected":

                        center_text(
                            draw,
                            "CONNECTED TO",
                            2,
                            FONT_SMALL
                        )

                        center_text(
                            draw,
                            get_link_line(remotes),
                            16,
                            FONT_MED
                        )

                    elif screen == "system":

                        center_text(
                            draw,
                            f"T:{temp}C  R:{ram}%",
                            2,
                            FONT_SMALL
                        )

                        center_text(
                            draw,
                            f"UP: {uptime}",
                            16,
                            FONT_SMALL
                        )

                    elif screen == "callsign":

                        center_text(
                            draw,
                            CALLSIGN,
                            8,
                            FONT_BIG
                        )

                else:

                    # ---------------------------------
                    # 64px HEIGHT LAYOUTS
                    # ---------------------------------

                    if screen == "default":

                        draw_header(draw)

                        center_text(
                            draw,
                            f"NODE {NODE_NUMBER}",
                            24,
                            FONT_MED
                        )

                        center_text(
                            draw,
                            "IDLE",
                            42,
                            FONT_BIG
                        )

                    elif screen == "connected":

                        draw_header(draw)

                        center_text(
                            draw,
                            "CONNECTED",
                            24,
                            FONT_BIG
                        )

                        center_text(
                            draw,
                            get_link_line(remotes),
                            46,
                            FONT_MED
                        )

                    elif screen == "system":

                        draw_header(draw)

                        center_text(
                            draw,
                            f"TEMP {temp}C",
                            22,
                            FONT_MED
                        )

                        center_text(
                            draw,
                            f"RAM {ram}%",
                            38,
                            FONT_MED
                        )

                        center_text(
                            draw,
                            f"UP {uptime}",
                            54,
                            FONT_SMALL
                        )

                    elif screen == "callsign":

                        center_text(
                            draw,
                            CALLSIGN,
                            18,
                            FONT_HUGE
                        )

        tick += 1

        if tx or rx:

            time.sleep(ACTIVE_REFRESH)

        else:

            time.sleep(IDLE_REFRESH)

# =========================================
# START
# =========================================

if __name__ == "__main__":

    serial = i2c(
        port=1,
        address=I2C_ADDRESS
    )

    device = ssd1306(
        serial,
        width=WIDTH,
        height=HEIGHT,
        rotate=ROTATION
    )

    main(device)
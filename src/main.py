import time
import os
import sys
import re
import math
import subprocess
import json
import threading
from PIL import Image, ImageDraw, ImageFont

LUMA_AVAILABLE = True
try:
    from luma.core.interface.serial import i2c
    from luma.oled.device import ssd1306
    from luma.core.render import canvas
except ImportError:
    LUMA_AVAILABLE = False

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
    FONT_SMALL = ImageFont.load_default()
    FONT_MED = ImageFont.load_default()
    FONT_BIG = ImageFont.load_default()
    FONT_HUGE = ImageFont.load_default()

# =========================================
# SYSTEM DATA GETTERS
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
# ASL DATA GETTERS
# =========================================

def is_asterisk_ready():
    try:
        out = subprocess.check_output(
            ['sudo', 'asterisk', '-rx', f'rpt xnode {NODE_NUMBER}'],
            stderr=subprocess.STDOUT,
            timeout=1.0
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
# ASYNCHRONOUS THREADED STATE
# =========================================

class NodeState:
    def __init__(self):
        self.lock = threading.Lock()
        
        # System parameters
        self.cpu_temp = "--"
        self.ram_usage = 0
        self.uptime = "--"
        self.wifi_strength = 0
        self.warp_status = "LOCAL"
        
        # ASL parameters
        self.asl_ready = False
        self.rx = False
        self.tx = False
        self.remotes = []

    def get_system_stats(self):
        with self.lock:
            return {
                "cpu_temp": self.cpu_temp,
                "ram_usage": self.ram_usage,
                "uptime": self.uptime,
                "wifi_strength": self.wifi_strength,
                "warp_status": self.warp_status
            }

    def get_asl_status(self):
        with self.lock:
            return {
                "asl_ready": self.asl_ready,
                "rx": self.rx,
                "tx": self.tx,
                "remotes": list(self.remotes)
            }

    def update_system(self):
        temp = get_cpu_temp()
        ram = get_ram_usage()
        uptime = get_uptime()
        wifi = get_wifi_strength()
        warp = get_warp_status()
        with self.lock:
            self.cpu_temp = temp
            self.ram_usage = ram
            self.uptime = uptime
            self.wifi_strength = wifi
            self.warp_status = warp

    def update_asl(self):
        ready = is_asterisk_ready()
        rx, tx, remotes = False, False, []
        if ready:
            rx, tx, remotes = get_node_status()
        with self.lock:
            self.asl_ready = ready
            self.rx = rx
            self.tx = tx
            self.remotes = remotes

state = None

def system_updater(state_obj):
    while True:
        try:
            state_obj.update_system()
        except:
            pass
        time.sleep(5.0)

def asl_updater(state_obj):
    while True:
        try:
            state_obj.update_asl()
        except:
            pass
        time.sleep(0.4)

def init_state():
    global state
    if state is None:
        state = NodeState()
        # Fetch initial state synchronously to avoid showing blank info at startup
        state.update_system()
        state.update_asl()
        
        t_sys = threading.Thread(target=system_updater, args=(state,), daemon=True)
        t_asl = threading.Thread(target=asl_updater, args=(state,), daemon=True)
        t_sys.start()
        t_asl.start()

# =========================================
# DRAWING HELPERS
# =========================================

def center_text(draw, text, y, font):
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        x = (WIDTH - width) // 2
        draw.text((x, y), text, fill="white", font=font)
    except:
        draw.text((10, y), text, fill="white", font=font)

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

def draw_header(draw, sys_info):
    draw.rectangle(
        (0, 0, WIDTH - 1, 15),
        outline="white"
    )
    warp = sys_info["warp_status"]
    wifi = sys_info["wifi_strength"]
    wifi_text = f"{wifi}%"

    draw.text(
        (4, 3),
        warp,
        fill="white",
        font=FONT_SMALL
    )
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
# PIXEL ICONS DRAWING
# =========================================

def draw_thermometer_icon(draw, x, y):
    # Small bulb at bottom and stem going up
    draw.ellipse((x, y + 6, x + 4, y + 10), outline="white")
    draw.rectangle((x + 1, y, x + 3, y + 7), outline="white")
    draw.point((x + 2, y + 8), fill="white")
    draw.point((x + 1, y + 8), fill="white")
    draw.point((x + 3, y + 8), fill="white")
    draw.point((x + 2, y + 7), fill="white")

def draw_ram_icon(draw, x, y):
    # RAM chip drawing with pins
    draw.rectangle((x, y + 1, x + 6, y + 5), outline="white")
    draw.line((x + 1, y, x + 1, y), fill="white")
    draw.line((x + 3, y, x + 3, y), fill="white")
    draw.line((x + 5, y, x + 5, y), fill="white")
    draw.line((x + 1, y + 6, x + 1, y + 6), fill="white")
    draw.line((x + 3, y + 6, x + 3, y + 6), fill="white")
    draw.line((x + 5, y + 6, x + 5, y + 6), fill="white")

def draw_clock_icon(draw, x, y):
    # Uptime clock drawing
    draw.ellipse((x, y, x + 7, y + 7), outline="white")
    draw.line((x + 3, y + 3, x + 3, y + 1), fill="white")
    draw.line((x + 3, y + 3, x + 5, y + 3), fill="white")

# =========================================
# MODERN RF VISUALIZERS
# =========================================

def draw_tx_equalizer(draw, tick, start_y, total_height):
    # Spectrum analyzer style bouncing bars
    num_bars = 12
    bar_width = 5
    bar_gap = 3
    total_w = num_bars * bar_width + (num_bars - 1) * bar_gap
    start_x = (WIDTH - total_w) // 2
    
    max_h = total_height - start_y - 4
    base_y = HEIGHT - 2
    
    for i in range(num_bars):
        phase = tick * 0.35 + i * 0.75
        val = (math.sin(phase) + 1.0) / 2.0
        val += 0.1 * math.sin(tick * 1.2 + i)
        val = max(0.05, min(1.0, val))
        
        h = int(val * max_h)
        x = start_x + i * (bar_width + bar_gap)
        draw.rectangle((x, base_y - h, x + bar_width - 1, base_y), fill="white")

def draw_rx_smeter(draw, tick, start_y, total_height):
    cx = WIDTH // 2
    cy = HEIGHT + 5
    r = 45 if HEIGHT == 64 else 25
    
    if HEIGHT == 32:
        cy = HEIGHT + 2
        r = 20
        
    bbox = [cx - r, cy - r, cx + r, cy + r]
    draw.arc(bbox, start=210, end=330, fill="white")
    
    tick_len = 3 if HEIGHT == 64 else 2
    for angle in [210, 240, 270, 300, 330]:
        rad = math.radians(angle)
        x_start = cx + r * math.cos(rad)
        y_start = cy + r * math.sin(rad)
        x_end = cx + (r - tick_len) * math.cos(rad)
        y_end = cy + (r - tick_len) * math.sin(rad)
        draw.line((x_start, y_start, x_end, y_end), fill="white")
        
    if HEIGHT == 64:
        draw.text((cx - r - 2, cy - 25), "S1", fill="white", font=FONT_SMALL)
        draw.text((cx - 5, cy - r - 12), "S9", fill="white", font=FONT_SMALL)
        draw.text((cx + r - 18, cy - 25), "+20", fill="white", font=FONT_SMALL)
        
    # Oscillation for needle
    needle_level = 0.5 + 0.3 * math.sin(tick * 0.15) + 0.08 * math.cos(tick * 0.8)
    needle_level = max(0.1, min(0.9, needle_level))
    angle = 210 + needle_level * 120
    
    rad = math.radians(angle)
    needle_r = r - 4
    x_end = cx + needle_r * math.cos(rad)
    y_end = cy + needle_r * math.sin(rad)
    
    draw.line((cx, cy - (4 if HEIGHT == 64 else 2), x_end, y_end), fill="white")

# =========================================
# SCREEN DRAW FUNCTIONS
# =========================================

def draw_startup_screen():
    img = Image.new("1", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    if HEIGHT == 32:
        center_text(draw, "STARTING...", 10, FONT_MED)
    else:
        center_text(draw, "SYSTEM", 16, FONT_BIG)
        center_text(draw, "STARTING", 40, FONT_MED)
    return img

def draw_immersive_screen(tx, rx, remotes, tick, sys_info):
    img = Image.new("1", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    if tx:
        active_label = "TX KEYED"
        if HEIGHT == 32:
            center_text(draw, active_label, 2, FONT_SMALL)
            draw_tx_equalizer(draw, tick, 14, 32)
        else:
            center_text(draw, "LOCAL TX", 10, FONT_BIG)
            draw_tx_equalizer(draw, tick, 24, 64)
            
    elif rx:
        active = remotes[0] if remotes else "RX"
        active_label = f"RX {active}"
        if HEIGHT == 32:
            center_text(draw, active_label, 2, FONT_SMALL)
            draw_rx_smeter(draw, tick, 14, 32)
        else:
            center_text(draw, active_label, 10, FONT_BIG)
            draw_rx_smeter(draw, tick, 24, 64)
            
    return img

def draw_normal_screen(screen_name, sys_info, asl_info):
    img = Image.new("1", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    
    temp = sys_info["cpu_temp"]
    ram = sys_info["ram_usage"]
    uptime = sys_info["uptime"]
    remotes = asl_info["remotes"]
    
    if HEIGHT == 32:
        if screen_name == "default":
            center_text(draw, f"NODE {NODE_NUMBER}", 2, FONT_MED)
            center_text(draw, "STATUS: IDLE", 18, FONT_MED)
        elif screen_name == "callsign":
            center_text(draw, CALLSIGN, 8, FONT_BIG)
        elif screen_name == "connected":
            center_text(draw, "CONNECTED TO", 2, FONT_SMALL)
            center_text(draw, get_link_line(remotes), 16, FONT_MED)
        elif screen_name == "system":
            center_text(draw, f"T:{temp}C  R:{ram}%", 2, FONT_SMALL)
            center_text(draw, f"UP: {uptime}", 16, FONT_SMALL)
    else:
        # HEIGHT == 64 Layouts
        draw_header(draw, sys_info)
        
        if screen_name == "default":
            center_text(draw, f"NODE {NODE_NUMBER}", 22, FONT_MED)
            center_text(draw, "IDLE", 40, FONT_BIG)
            
            # Pulsing status dot
            pulse_r = 2 + int((time.time() * 2) % 3)
            draw.ellipse((WIDTH // 2 - pulse_r, 58 - pulse_r, WIDTH // 2 + pulse_r, 58 + pulse_r), fill="white")
            
        elif screen_name == "callsign":
            center_text(draw, CALLSIGN, 18, FONT_HUGE)
            
        elif screen_name == "connected":
            center_text(draw, "CONNECTED TO", 20, FONT_SMALL)
            center_text(draw, get_link_line(remotes), 34, FONT_MED)
            
            # Simple link visual element
            draw.ellipse((10, 52, 14, 56), outline="white")
            draw.line((14, 54, WIDTH - 14, 54), fill="white")
            draw.ellipse((WIDTH - 14, 52, WIDTH - 10, 56), outline="white")
            
        elif screen_name == "system":
            # Temp Row
            draw_thermometer_icon(draw, 12, 21)
            draw.text((24, 20), f"TEMP: {temp}°C", fill="white", font=FONT_SMALL)
            
            # RAM Row
            draw_ram_icon(draw, 12, 35)
            # RAM Bar (width 50px)
            draw.rectangle((24, 36, 74, 42), outline="white")
            bar_w = int(50 * (ram / 100.0))
            if bar_w > 0:
                draw.rectangle((26, 38, 26 + bar_w - 4 if bar_w > 4 else 26, 40), fill="white")
            draw.text((79, 34), f"{ram}%", fill="white", font=FONT_SMALL)
            
            # Uptime Row
            draw_clock_icon(draw, 12, 49)
            draw.text((24, 48), f"UPTIME: {uptime}", fill="white", font=FONT_SMALL)
            
    return img

# =========================================
# MAIN
# =========================================

def main(device):
    # Initialize background fetchers
    init_state()

    screens = [
        "default",
        "callsign",
        "connected",
        "system"
    ]
    current_screen_idx = 0
    last_screen_change = time.time()
    tick = 0
    
    last_static_img = None
    transition_progress = 1.0
    transition_start_time = 0
    transition_duration = 0.5  # half second sliding animation
    
    # 20 FPS rendering loop
    FRAME_TIME = 0.05
    
    while True:
        loop_start = time.time()
        
        # Get snapshots of states (extremely fast, no blocking)
        sys_info = state.get_system_stats()
        asl_info = state.get_asl_status()
        
        asl_ready = asl_info["asl_ready"]
        tx = asl_info["tx"]
        rx = asl_info["rx"]
        remotes = asl_info["remotes"]
        
        if not asl_ready:
            img = draw_startup_screen()
            device.display(img)
            time.sleep(0.2)
            continue
            
        if tx or rx:
            img = draw_immersive_screen(tx, rx, remotes, tick, sys_info)
            device.display(img)
            tick += 1
            
            # Faster updates during animations
            elapsed = time.time() - loop_start
            sleep_time = max(0.01, ACTIVE_REFRESH - elapsed)
            time.sleep(sleep_time)
            continue
            
        # Screen transitions
        now = time.time()
        if now - last_screen_change > SCREEN_ROTATE_INTERVAL:
            last_static_img = draw_normal_screen(screens[current_screen_idx], sys_info, asl_info)
            current_screen_idx = (current_screen_idx + 1) % len(screens)
            last_screen_change = now
            transition_progress = 0.0
            transition_start_time = now
            
        if transition_progress < 1.0:
            elapsed_transition = now - transition_start_time
            transition_progress = min(1.0, elapsed_transition / transition_duration)
            
            # Calculate pixel offset (sliding from right to left)
            offset = int(WIDTH * transition_progress)
            img_next = draw_normal_screen(screens[current_screen_idx], sys_info, asl_info)
            
            combined = Image.new("1", (WIDTH * 2, HEIGHT))
            if last_static_img:
                combined.paste(last_static_img, (0, 0))
            combined.paste(img_next, (WIDTH, 0))
            
            cropped = combined.crop((offset, 0, offset + WIDTH, HEIGHT))
            device.display(cropped)
        else:
            img = draw_normal_screen(screens[current_screen_idx], sys_info, asl_info)
            device.display(img)
            
        tick += 1
        
        elapsed = time.time() - loop_start
        sleep_time = max(0.01, FRAME_TIME - elapsed)
        time.sleep(sleep_time)

# =========================================
# START
# =========================================

if __name__ == "__main__":
    if not LUMA_AVAILABLE:
        print("Error: luma.oled libraries not found. Please run the installer.")
        sys.exit(1)

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
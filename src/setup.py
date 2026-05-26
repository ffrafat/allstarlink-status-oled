import os
import json

CONFIG_FILE = "/opt/allstarlink-status-oled/config.json"

def main():
    # Ensure target directory exists
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    # Load existing configuration if it exists
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        except Exception:
            pass

    # Default values
    default_callsign = config.get("callsign", "MYCALL")
    default_node = config.get("node", "1234")
    default_rotation = config.get("rotation", 0)
    default_resolution = config.get("resolution", "128x64")
    default_i2c_address = config.get("i2c_address", "0x3C")

    print("\n=== AllStarLink Status OLED Configuration ===")

    # Prompt for callsign
    callsign = input(f"Enter Callsign [{default_callsign}]: ").strip()
    if not callsign:
        callsign = default_callsign

    # Prompt for node
    node = input(f"Enter Node Number [{default_node}]: ").strip()
    if not node:
        node = default_node

    # Prompt for rotation
    while True:
        rotation_str = input(f"Enter Screen Rotation (0=0°, 1=90°, 2=180°, 3=270°) [{default_rotation}]: ").strip()
        if not rotation_str:
            rotation = default_rotation
            break
        try:
            rotation = int(rotation_str)
            if rotation in [0, 1, 2, 3]:
                break
            else:
                print("Invalid rotation. Please enter 0, 1, 2, or 3.")
        except ValueError:
            print("Invalid input. Please enter a number (0, 1, 2, or 3).")

    # Prompt for I2C Address
    while True:
        i2c_addr = input(f"Enter I2C Address [{default_i2c_address}]: ").strip()
        if not i2c_addr:
            i2c_addr = default_i2c_address
            break
        if i2c_addr.lower().startswith("0x"):
            try:
                int(i2c_addr, 16)
                break
            except ValueError:
                print("Invalid hex address. Example: 0x3C")
        else:
            try:
                int(i2c_addr)
                break
            except ValueError:
                print("Invalid address. Please enter a hex (0x3C) or decimal number.")

    # Prompt for Resolution
    print("\nSelect OLED Resolution:")
    print("1) 128x64 (Default)")
    print("2) 128x32")
    while True:
        choice = input(f"Enter choice (1 or 2) [{(1 if default_resolution == '128x64' else 2)}]: ").strip()
        if not choice:
            resolution = default_resolution
            break
        if choice == "1":
            resolution = "128x64"
            break
        elif choice == "2":
            resolution = "128x32"
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")

    # Save config
    config["callsign"] = callsign.upper()
    config["node"] = node
    config["rotation"] = rotation
    config["i2c_address"] = i2c_addr
    config["resolution"] = resolution

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

    # Set permissions on config.json so it is readable by the system service
    try:
        os.chmod(CONFIG_FILE, 0o644)
    except Exception:
        pass

    print(f"Configuration saved successfully to {CONFIG_FILE}\n")

if __name__ == "__main__":
    main()

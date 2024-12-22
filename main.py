import os
import time
import re
import requests
import json
import tkinter as tk
from tkinter import ttk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys

# Default configuration
config = {
    "webhook_url": "https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz",
    "mention_everyone": False,
    "mention_here": False,
    "mention_role": False,
    "mention_user": False,
    "role_id": "",
    "user_id": "",
    "ignore_mobile_observatory": False,
    "ignore_stargates": False,
    "ignore_wormholes": False,
    "ignore_stations": False,
    "ignore_citadels": False,
    "custom_message_enabled": False,
    "custom_message": "Character decloaked: **{CHARNAME}**",
    "multi_ping_enabled": False,
    "multi_ping_count": 2
}

citadels = [
    "Astrahus", "Fortizar", "Keepstar", "Raitaru", "Azbel", "Sotiyo", "Athanor",
    "Tatara", "Ansiblex", "Pharolux", "Tenebrex", "Metenox"
]

# Get the base directory where the script or exe resides
if getattr(sys, 'frozen', False):  # Running as a PyInstaller bundle
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "settings.json")
LOG_DIR = os.path.expanduser("~/Documents/EVE/logs/Gamelogs")
DECLINATION_REGEX = r"Your cloak deactivates"
LISTENER_REGEX = r"Listener: (.+)"
last_decloak_event = {}
observer = None

# Save configuration to file
def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

# Load configuration from file
def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config.update(json.load(f))

# Function to send notification to Discord
def send_discord_notification(character_name):
    mentions = []
    if config["mention_everyone"]:
        mentions.append("@everyone")
    if config["mention_here"]:
        mentions.append("@here")
    if config["mention_role"] and config["role_id"]:
        mentions.append(f"<@&{config['role_id']}>")
    if config["mention_user"] and config["user_id"]:
        mentions.append(f"<@{config['user_id']}>")

    mention_text = " ".join(mentions)
    if config["custom_message_enabled"]:
        message = config["custom_message"].replace("{CHARNAME}", character_name)
    else:
        message = f"Character decloaked: **{character_name}**"

    payload = {"content": f"{mention_text} {message}"}
    try:
        for _ in range(config["multi_ping_count"] if config["multi_ping_enabled"] else 1):
            response = requests.post(config["webhook_url"], json=payload)
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Failed to send notification: {e}")

# Event handler for log file changes
class LogHandler(FileSystemEventHandler):
    def on_modified(self, event):
        global last_decloak_event
        if event.src_path.endswith(".txt"):
            with open(event.src_path, "r", encoding="utf-8", errors="ignore") as file:
                lines = file.readlines()
                for line in reversed(lines):
                    if config["ignore_mobile_observatory"] and "Mobile Observatory" in line:
                        continue
                    if config["ignore_stargates"] and "Stargate" in line:
                        continue
                    if config["ignore_wormholes"] and "Wormhole" in line:
                        continue
                    if config["ignore_stations"] and "Station" in line:
                        continue
                    if config["ignore_citadels"] and any(structure in line for structure in citadels):
                        continue

                    if re.search(DECLINATION_REGEX, line):
                        timestamp_match = re.match(r"\[ ([^\]]+) \]", line)
                        if timestamp_match:
                            timestamp = timestamp_match.group(1)
                            if event.src_path in last_decloak_event and last_decloak_event[event.src_path] == timestamp:
                                return
                            last_decloak_event[event.src_path] = timestamp

                        with open(event.src_path, "r", encoding="utf-8", errors="ignore") as char_file:
                            char_file.seek(0)
                            for char_line in char_file:
                                listener_match = re.search(LISTENER_REGEX, char_line)
                                if listener_match:
                                    character_name = listener_match.group(1)
                                    send_discord_notification(character_name)
                                    return

# Start monitoring logs
def start_monitoring():
    global observer
    if observer:
        return

    event_handler = LogHandler()
    observer = Observer()
    observer.schedule(event_handler, LOG_DIR, recursive=False)
    observer.start()
    print("Monitoring started.")

# Stop monitoring logs
def stop_monitoring():
    global observer
    if observer:
        observer.stop()
        observer.join()
        observer = None
    print("Monitoring stopped.")

def create_gui():
    def toggle_monitoring():
        if monitor_button["text"] == "Start Monitoring":
            start_monitoring()
            monitor_button["text"] = "Stop Monitoring"
        else:
            stop_monitoring()
            monitor_button["text"] = "Start Monitoring"

    def save_settings():
        config["webhook_url"] = webhook_entry.get()
        config["mention_everyone"] = everyone_var.get()
        config["mention_here"] = here_var.get()
        config["mention_role"] = role_var.get()
        config["mention_user"] = user_var.get()
        config["role_id"] = role_entry.get()
        config["user_id"] = user_entry.get()
        config["ignore_mobile_observatory"] = mobile_observatory_var.get()
        config["ignore_stargates"] = stargate_var.get()
        config["ignore_wormholes"] = wormhole_var.get()
        config["ignore_stations"] = station_var.get()
        config["ignore_citadels"] = upwell_var.get()
        config["custom_message_enabled"] = custom_message_var.get()
        config["custom_message"] = custom_message_entry.get()
        config["multi_ping_enabled"] = multi_ping_var.get()
        config["multi_ping_count"] = int(multi_ping_count.get())
        save_config()
        print("Settings saved.")

    def toggle_entry_state(entry, variable):
        entry.config(state="normal" if variable.get() else "disabled")

    root = tk.Tk()
    root.title("DECLOAKER")
    root.resizable(False, False)

    padding = 10
    root_frame = ttk.Frame(root, padding=padding)
    root_frame.grid(row=0, column=0, sticky="nsew")

    # Discord Settings Section
    ttk.Label(root_frame, text="Discord Settings", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))

    ttk.Label(root_frame, text="Webhook URL:").grid(row=1, column=0, sticky="w")
    webhook_entry = ttk.Entry(root_frame, width=50)
    webhook_entry.grid(row=1, column=1, columnspan=2, sticky="we")
    webhook_entry.insert(0, config["webhook_url"])

    everyone_var = tk.BooleanVar(value=config["mention_everyone"])
    ttk.Checkbutton(root_frame, text="@everyone", variable=everyone_var).grid(row=2, column=0, sticky="w")

    here_var = tk.BooleanVar(value=config["mention_here"])
    ttk.Checkbutton(root_frame, text="@here", variable=here_var).grid(row=2, column=1, sticky="w")

    role_var = tk.BooleanVar(value=config["mention_role"])
    role_check = ttk.Checkbutton(root_frame, text="@role (ID):", variable=role_var, command=lambda: toggle_entry_state(role_entry, role_var))
    role_check.grid(row=3, column=0, sticky="w")
    role_entry = ttk.Entry(root_frame, width=30)
    role_entry.grid(row=3, column=1, columnspan=2, sticky="we")
    role_entry.insert(0, config["role_id"])
    role_entry.config(state="normal" if config["mention_role"] else "disabled")

    user_var = tk.BooleanVar(value=config["mention_user"])
    user_check = ttk.Checkbutton(root_frame, text="@user (ID):", variable=user_var, command=lambda: toggle_entry_state(user_entry, user_var))
    user_check.grid(row=4, column=0, sticky="w")
    user_entry = ttk.Entry(root_frame, width=30)
    user_entry.grid(row=4, column=1, columnspan=2, sticky="we")
    user_entry.insert(0, config["user_id"])
    user_entry.config(state="normal" if config["mention_user"] else "disabled")

    custom_message_var = tk.BooleanVar(value=config["custom_message_enabled"])
    ttk.Checkbutton(root_frame, text="Custom Message: ", variable=custom_message_var, command=lambda: toggle_entry_state(custom_message_entry, custom_message_var)).grid(row=5, column=0, sticky="w")
    custom_message_entry = ttk.Entry(root_frame, width=50)
    custom_message_entry.grid(row=5, column=1, columnspan=2, sticky="we")
    custom_message_entry.insert(0, config["custom_message"])
    custom_message_entry.config(state="normal" if config["custom_message_enabled"] else "disabled")

    # Multi-Ping Section
    multi_ping_var = tk.BooleanVar(value=config["multi_ping_enabled"])
    ttk.Checkbutton(root_frame, text="Multi-Ping", variable=multi_ping_var, command=lambda: toggle_entry_state(multi_ping_count, multi_ping_var)).grid(row=6, column=0, sticky="w")
    multi_ping_count = ttk.Combobox(root_frame, values=[2, 3, 4, 5], state="readonly", width=5)
    multi_ping_count.grid(row=6, column=1, sticky="w")
    multi_ping_count.set(str(config["multi_ping_count"]))
    multi_ping_count.config(state="normal" if config["multi_ping_enabled"] else "disabled")

    # Extra Options Section
    ttk.Label(root_frame, text="Extra Options", font=("Arial", 10, "bold")).grid(row=7, column=0, columnspan=3, sticky="w", pady=(10, 5))

    mobile_observatory_var = tk.BooleanVar(value=config["ignore_mobile_observatory"])
    stargate_var = tk.BooleanVar(value=config["ignore_stargates"])
    wormhole_var = tk.BooleanVar(value=config["ignore_wormholes"])
    station_var = tk.BooleanVar(value=config["ignore_stations"])
    upwell_var = tk.BooleanVar(value=config["ignore_citadels"])

    ttk.Checkbutton(root_frame, text="Ignore Stargates", variable=stargate_var).grid(row=8, column=0, sticky="w")
    ttk.Checkbutton(root_frame, text="Ignore Wormholes", variable=wormhole_var).grid(row=8, column=1, sticky="w")
    ttk.Checkbutton(root_frame, text="Ignore Stations", variable=station_var).grid(row=9, column=0, sticky="w")
    ttk.Checkbutton(root_frame, text="Ignore Mobile Observatory", variable=mobile_observatory_var).grid(row=9, column=1, sticky="w")
    ttk.Checkbutton(root_frame, text="Ignore Citadels", variable=upwell_var).grid(row=10, column=0, sticky="w")

    ttk.Label(root_frame, text="").grid(row=11, column=0, columnspan=3)  # Blank row

    monitor_button = ttk.Button(root_frame, text="Start Monitoring", command=toggle_monitoring)
    monitor_button.grid(row=12, column=0, sticky="w")

    save_button = ttk.Button(root_frame, text="Apply Settings", command=save_settings)
    save_button.grid(row=12, column=1, columnspan=2, sticky="e")

    root.mainloop()

if __name__ == "__main__":
    load_config()
    create_gui()

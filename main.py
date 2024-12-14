import os
import time
import re
import requests
import json
import tkinter as tk
from tkinter import ttk
from tkinter import Menu
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys

# Default configuration
config = {
    "webhook_url": "https://discord.com/api/webhooks/123456789/abcdefghijklmnopqrstuvwxyz",
    "mention_everyone": True,
    "mention_here": False,
    "mention_role": False,
    "mention_user": False,
    "role_id": "",
    "user_id": "",
    "ignore_mobile_observatory": False,
    "ignore_stargates": False,
    "ignore_wormholes": False,
    "ignore_stations": False
}

# Get the base directory where the script or exe resides
if getattr(sys, 'frozen', False):  # Running as a PyInstaller bundle
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Set configuration file path relative to script or exe location
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
    message = f"{mention_text} Character decloaked: **{character_name}**"
    payload = {"content": message}
    try:
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

# GUI application
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
        save_config()
        print("Settings saved.")

    def toggle_role_entry():
        role_entry.config(state="normal" if role_var.get() else "disabled")

    def toggle_user_entry():
        user_entry.config(state="normal" if user_var.get() else "disabled")

    def open_settings_popup():
        def save_popup_settings():
            config["ignore_mobile_observatory"] = mobile_observatory_var.get()
            config["ignore_stargates"] = stargate_var.get()
            config["ignore_wormholes"] = wormhole_var.get()
            config["ignore_stations"] = station_var.get()
            save_config()
            popup.destroy()

        popup = tk.Toplevel(root)
        popup.title("Settings")
        popup.geometry("300x250")

        # Center the popup over the main window
        root_x = root.winfo_x()
        root_y = root.winfo_y()
        root_width = root.winfo_width()
        root_height = root.winfo_height()
        popup_x = root_x + (root_width // 2) - 150
        popup_y = root_y + (root_height // 2) - 125
        popup.geometry(f"300x250+{popup_x}+{popup_y}")

        mobile_observatory_var = tk.BooleanVar(value=config["ignore_mobile_observatory"])
        stargate_var = tk.BooleanVar(value=config["ignore_stargates"])
        wormhole_var = tk.BooleanVar(value=config["ignore_wormholes"])
        station_var = tk.BooleanVar(value=config["ignore_stations"])

        frame = ttk.Frame(popup, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Checkbutton(frame, text="Ignore Mobile Observatory", variable=mobile_observatory_var).grid(row=0, column=0, sticky="w", pady=5)
        ttk.Checkbutton(frame, text="Ignore Stargates", variable=stargate_var).grid(row=1, column=0, sticky="w", pady=5)
        ttk.Checkbutton(frame, text="Ignore Wormholes", variable=wormhole_var).grid(row=2, column=0, sticky="w", pady=5)
        ttk.Checkbutton(frame, text="Ignore Stations", variable=station_var).grid(row=3, column=0, sticky="w", pady=5)

        ttk.Button(frame, text="Save", command=save_popup_settings).grid(row=4, column=0, pady=10)

    root = tk.Tk()
    root.title("DECLOAKER")
    root.resizable(False, False)  # Prevent resizing

    # Menu bar
    menubar = Menu(root)
    settings_menu = Menu(menubar, tearoff=0)
    settings_menu.add_command(label="Settings", command=open_settings_popup)
    menubar.add_cascade(label="Options", menu=settings_menu)
    root.config(menu=menubar)

    # Add padding
    padding = 10
    root_frame = ttk.Frame(root, padding=padding)
    root_frame.grid(row=0, column=0, sticky="nsew")

    ttk.Label(root_frame, text="Webhook URL:").grid(row=0, column=0, sticky="w")
    webhook_entry = ttk.Entry(root_frame, width=50)
    webhook_entry.grid(row=0, column=1, columnspan=2, sticky="we")
    webhook_entry.insert(0, config["webhook_url"])

    everyone_var = tk.BooleanVar(value=config["mention_everyone"])
    ttk.Checkbutton(root_frame, text="@everyone", variable=everyone_var).grid(row=1, column=0, sticky="w")

    here_var = tk.BooleanVar(value=config["mention_here"])
    ttk.Checkbutton(root_frame, text="@here", variable=here_var).grid(row=1, column=1, sticky="w")

    role_var = tk.BooleanVar(value=config["mention_role"])
    role_check = ttk.Checkbutton(root_frame, text="@role (ID):", variable=role_var, command=toggle_role_entry)
    role_check.grid(row=2, column=0, sticky="w")

    role_entry = ttk.Entry(root_frame, width=30)
    role_entry.grid(row=2, column=1, columnspan=2, sticky="we")
    role_entry.insert(0, config["role_id"])
    role_entry.config(state="normal" if config["mention_role"] else "disabled")

    user_var = tk.BooleanVar(value=config["mention_user"])
    user_check = ttk.Checkbutton(root_frame, text="@user (ID):", variable=user_var, command=toggle_user_entry)
    user_check.grid(row=3, column=0, sticky="w")

    user_entry = ttk.Entry(root_frame, width=30)
    user_entry.grid(row=3, column=1, columnspan=2, sticky="we")
    user_entry.insert(0, config["user_id"])
    user_entry.config(state="normal" if config["mention_user"] else "disabled")

    # Add padding between text fields and buttons
    ttk.Label(root_frame).grid(row=4, column=0, pady=10)  # Empty row for spacing

    global monitor_button
    monitor_button = ttk.Button(root_frame, text="Start Monitoring", command=toggle_monitoring)
    monitor_button.grid(row=5, column=0, sticky="w")

    save_button = ttk.Button(root_frame, text="Save Settings", command=save_settings)
    save_button.grid(row=5, column=1, columnspan=2, sticky="e")

    root.mainloop()

if __name__ == "__main__":
    load_config()
    create_gui()

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog, scrolledtext
import json
import pygame
import os
import serial
import serial.tools.list_ports
import threading
import csv
from datetime import datetime
import signal
import sys
import uuid
import socket
import websocket
import base64
import hashlib
import queue
import time

# Initialize the pygame mixer with a larger buffer size to reduce latency
pygame.mixer.init(buffer=4096)

audio_files = {}
timer = None
remaining_time = 0
arduino = None
log_file = None
recording_active = False
sound_enabled = True  # Assuming a global setting to enable/disable all sounds

SERIAL_BAUDRATE = 19200
SERIAL_STARTUP_DELAY_SECONDS = 1.8
serial_rx_queue = queue.Queue()
serial_stop_event = threading.Event()
serial_decode_error_count = 0

# OBS Control Client
class OBSClient:
    def __init__(self, url, message_callback, password=None):
        self.url = url
        self.ws = None
        self.connected = False
        self.message_callback = message_callback
        self.password = password

    def connect(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True
        self.thread.start()

    def on_open(self, ws):
        self.connected = True
        self.message_callback("Connected to OBS WebSocket.")

    def on_message(self, ws, message):
        self.message_callback(f"Received: {message}")
        data = json.loads(message)
        
        if data["op"] == 0:  # Hello message received
            if "authentication" in data["d"]:
                challenge = data["d"]["authentication"]["challenge"]
                salt = data["d"]["authentication"]["salt"]
                self.send_identify(challenge, salt)
            else:
                self.send_identify()

    def on_error(self, ws, error):
        self.connected = False
        self.message_callback(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        self.connected = False
        self.message_callback("Connection closed.")

    def send_identify(self, challenge=None, salt=None):
        # Compute the authentication key if challenge and salt are provided
        if self.password and challenge and salt:
            auth_response = self.compute_auth_response(challenge, salt)
        else:
            auth_response = None

        identify_msg = {
            "op": 1,
            "d": {
                "rpcVersion": 1,
                "authentication": auth_response
            }
        }
        self.send(json.dumps(identify_msg))

    def compute_auth_response(self, challenge, salt):
        # Compute the authentication response
        secret = base64.b64encode(hashlib.sha256((self.password + salt).encode('utf-8')).digest()).decode('utf-8')
        auth_response = base64.b64encode(hashlib.sha256((secret + challenge).encode('utf-8')).digest()).decode('utf-8')
        return auth_response

    def send(self, message):
        if self.connected:
            self.ws.send(message)
        else:
            self.message_callback("Cannot send message. Not connected.")

    def close(self):
        if self.connected:
            self.ws.close()
            self.connected = False

# OBS Control App integrated into the main window
class OBSControlApp:
    def __init__(self, root):
        self.obs_client = None
        self.connection_status = tk.StringVar(value="Disconnected")
        self.is_recording = False
        self.recording_start_time = None
        self.blinking = False
        self.blink_color = "blue"
        self.default_color = root.cget("bg")  # Use the default background color of the window
        self.create_widgets(root)

    def create_widgets(self, root):
        # Frame for OBS controls
        obs_frame = tk.Frame(root, borderwidth=1, relief="groove")
        obs_frame.place(relx=0.71, rely=0.008, relwidth=0.3, relheight=1)

        # Connection controls
        connection_frame = tk.LabelFrame(obs_frame, text="OBS Connection Panel", padx=10, pady=10)
        connection_frame.pack(fill="x", padx=5, pady=5)

        connect_button = tk.Button(
            connection_frame, text="Connect", command=self.connect_to_obs
        )
        connect_button.grid(row=0, column=0, padx=5)

        disconnect_button = tk.Button(
            connection_frame, text="Disconnect", command=self.disconnect_from_obs
        )
        disconnect_button.grid(row=0, column=1, padx=5)

        tk.Label(connection_frame, text="Status:").grid(row=0, column=2, padx=5)
        tk.Label(connection_frame, textvariable=self.connection_status).grid(
            row=0, column=3, padx=5
        )

        # LED Status Indicator
        self.status_led = tk.Label(connection_frame, width=2, height=1, bg="red")
        self.status_led.grid(row=0, column=4, padx=5)

        # Recording controls
        recording_frame = tk.LabelFrame(obs_frame, text="Recording Controls", padx=10, pady=10)
        recording_frame.pack(fill="x", padx=10, pady=5)

        self.start_button = tk.Button(
            recording_frame, text="Start Recording", command=self.start_recording
        )
        self.start_button.grid(row=0, column=0, padx=5)

        self.stop_button = tk.Button(
            recording_frame, text="Stop Recording", command=self.stop_recording, state=tk.DISABLED
        )
        self.stop_button.grid(row=0, column=1, padx=5)

        # Timer Display
        self.timer_label = tk.Label(recording_frame, text="00:00")
        self.timer_label.grid(row=0, column=2, padx=5)

        # Circular Blinking Indicator
        self.blink_label = tk.Canvas(recording_frame, width=15, height=15, highlightthickness=0)
        self.blink_label.grid(row=0, column=3, padx=5)
        self.blink_indicator = self.blink_label.create_oval(2, 2, 14, 14, fill=self.default_color)

        # Directory controls
        directory_frame = tk.LabelFrame(obs_frame, text="Directory Controls", padx=10, pady=10)
        directory_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(directory_frame, text="Recording Directory:").grid(
            row=0, column=0, padx=5
        )

        self.directory_entry = tk.Entry(directory_frame, width=40)
        self.directory_entry.grid(row=0, column=1, padx=5)

        browse_button = tk.Button(
            directory_frame, text="Browse", command=self.browse_directory
        )
        browse_button.grid(row=0, column=2, padx=5)

        set_directory_button = tk.Button(
            directory_frame, text="Set Directory", command=self.set_recording_directory
        )
        set_directory_button.grid(row=0, column=3, padx=5)

        # Console display
        console_frame = tk.LabelFrame(obs_frame, text="Console", padx=10, pady=10)

        # Pack the console frame immediately after the directory frame
        console_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.console = scrolledtext.ScrolledText(
            console_frame, wrap=tk.WORD, width=50, height=20
        )
        self.console.pack(fill="both", expand=True)

    def connect_to_obs(self):
        if self.obs_client and self.obs_client.connected:
            messagebox.showinfo("Info", "Already connected.")
            return
        self.obs_client = OBSClient("ws://localhost:4455", self.log_message, password="")  # enter your OBS WebSocket password here, or leave empty if authentication is disabled
        self.obs_client.connect()

    def disconnect_from_obs(self):
        if self.obs_client:
            self.obs_client.close()
            self.connection_status.set("Disconnected")
            self.status_led.config(bg="red")
            self.log_message("Disconnected from OBS WebSocket.")
            self.reset_recording_state()

    def start_recording(self):
        if not self.obs_client or not self.obs_client.connected:
            messagebox.showerror("Error", "Not connected to OBS.")
            return

        start_record_msg = {
            "op": 6,
            "d": {
                "requestType": "StartRecord",
                "requestId": "start_record_1",
                "requestData": {},
            },
        }
        self.obs_client.send(json.dumps(start_record_msg))
        self.set_recording_state(True)

    def stop_recording(self):
        if not self.obs_client or not self.obs_client.connected:
            messagebox.showerror("Error", "Not connected to OBS.")
            return

        stop_record_msg = {
            "op": 6,
            "d": {
                "requestType": "StopRecord",
                "requestId": "stop_record_1",
                "requestData": {},
            },
        }
        self.obs_client.send(json.dumps(stop_record_msg))
        self.set_recording_state(False)

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.directory_entry.delete(0, tk.END)
            self.directory_entry.insert(0, directory)

    def set_recording_directory(self):
        if not self.obs_client or not self.obs_client.connected:
            messagebox.showerror("Error", "Not connected to OBS.")
            return

        directory = self.directory_entry.get()
        if not directory:
            messagebox.showerror("Error", "No directory selected.")
            return

        set_directory_msg = {
            "op": 6,
            "d": {
                "requestType": "SetRecordDirectory",
                "requestId": "set_record_dir_1",
                "requestData": {"recordDirectory": directory},
            },
        }
        self.obs_client.send(json.dumps(set_directory_msg))

    def set_recording_state(self, is_recording):
        """Update the UI and internal state when recording starts or stops."""
        self.is_recording = is_recording
        self.start_button.config(state=tk.DISABLED if is_recording else tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL if is_recording else tk.DISABLED)
        
        if is_recording:
            self.recording_start_time = datetime.now()
            self.blinking = True
            self.update_timer()
            self.start_blinking()
        else:
            self.blinking = False
            self.blink_label.itemconfig(self.blink_indicator, fill=self.default_color)

    def reset_recording_state(self):
        """Reset the UI to the default state when disconnected."""
        self.set_recording_state(False)

    def update_timer(self):
        """Update the recording timer every second."""
        if self.is_recording:
            elapsed_time = datetime.now() - self.recording_start_time
            minutes, seconds = divmod(elapsed_time.seconds, 60)
            self.timer_label.config(text=f"{minutes:02}:{seconds:02}")
            self.timer_label.after(1000, self.update_timer)

    def start_blinking(self):
        """Animate the blinking indicator to show recording is active."""
        if self.blinking:
            current_color = self.blink_label.itemcget(self.blink_indicator, "fill")
            next_color = self.blink_color if current_color == self.default_color else self.default_color
            self.blink_label.itemconfig(self.blink_indicator, fill=next_color)
            self.blink_label.after(500, self.start_blinking)  # Toggle every 500ms

    def log_message(self, message):
        self.console.insert(tk.END, f"{message}\n")
        self.console.yview(tk.END)
        if "Connected" in message:
            self.connection_status.set("Connected")
            self.status_led.config(bg="blue")
        elif "Connection closed" in message or "Error" in message:
            self.connection_status.set("Disconnected")
            self.status_led.config(bg="red")





# Behavior GUI Code
def save_config(config):
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)

def load_config(file_path=None):
    if file_path is None:
        file_path = "config.json"
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "protocols": {
                f"Protocol {i+1}": {
                    "sequence_1": [],
                    "sequence_2": [],
                    "sequence_3": [],
                    "sequence_4": [],
                    "Button_brightness": 128,
                    "RewardLed_brightness": 128,
                    "sequence_active": "Active",
                    "light_guidance": "Off",
                    # 'Random_seq': 'Off',
                    "Random_chase": "Off",
                    "Optional_sequences":"Off",
                    "Optional_Button_Led": "Off",
                    "sound": "Off",
                    "reward_led": "Off",
                    "reward_shape": "rectangle",
                    "reward_sound": "Off",
                    "reward_amount": 1,
                    "learning_correct_count": 5,
                    "retrieval_error_count": 3,
                    "runtime_minutes": 30,
                    "audio_files": {f"button_{j}_sound": "" for j in range(1, 10)},
                    "flash_path": "Off",
                    "flash_count": 3,
                    "Switching": "Off",
                }
                for i in range(4)
            }
        }

def load_new_config():
    file_path = filedialog.askopenfilename(
        title="Select Configuration File", filetypes=[("JSON Files", "*.json")]
    )
    if file_path:
        global config
        config = load_config(file_path)
        protocol_var.set(
            list(config["protocols"].keys())[0]
        )  # Set the default protocol to the first in the list
        update_protocol_dropdowns()  # Update the dropdowns immediately after loading the configuration
        update_ui()  # Update the UI immediately after loading the configuration

def update_protocol_dropdowns():
    """Update the protocol dropdown list in both the main window and the protocol settings window."""
    protocol_combobox["values"] = list(config["protocols"].keys())
    if "protocol_settings_combobox" in globals():
        protocol_settings_combobox["values"] = list(config["protocols"].keys())

config = load_config()

def on_app_close():
    disconnect_serial()
    save_config(config)
    app.destroy()

def update_ui():
    current_protocol = protocol_var.get()
    if current_protocol not in config["protocols"]:
        protocol_var.set(list(config["protocols"].keys())[0])
    current_protocol = protocol_var.get()
    settings = config["protocols"][current_protocol]
    sequence_display.config(
        text="Sequence: " + "->".join(map(str, settings["sequence_1"]))
    )
    sound_combobox.set(settings["sound"])
    global sound_enabled
    sound_enabled = settings["sound"] == "On"
    reward_led_status_combobox.set(settings["reward_led"])
    reward_led_shape_combobox.set(settings["reward_shape"])
    reward_sound_combobox.set(settings["reward_sound"])
    sequence_active_combobox.set(settings["sequence_active"])
    light_guidance_combobox.set(settings["light_guidance"])
    # Random_seq_combobox.set(settings['Random_seq'])
    Random_chase_combobox.set(settings["Random_chase"])
    Optional_sequences_combobox.set(settings["Optional_sequences"])
    Optional_Button_Led_combobox.set(settings["Optional_Button_Led"])
    Switching_combobox.set(settings["Switching"])
    reward_amount_combobox.set(settings["reward_amount"])
    learning_correct_count_combobox.set(settings["learning_correct_count"])
    retrieval_error_count_combobox.set(settings["retrieval_error_count"])
    runtime_spinbox.delete(0, tk.END)
    runtime_spinbox.insert(0, settings["runtime_minutes"])
    flash_path_combobox.set(settings["flash_path"])
    flash_count_spinbox.delete(0, tk.END)
    flash_count_spinbox.insert(0, settings["flash_count"])
    button_brightness_slider.set(settings["Button_brightness"])
    reward_led_brightness_slider.set(settings["RewardLed_brightness"])
    highlight_sequence_buttons()

def load_audio_file(sound_key, labels, temp_audio_files):
    file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav")])
    if file_path:
        temp_audio_files[sound_key + "_sound"] = file_path
        labels[sound_key]["text"] = os.path.basename(file_path)

def manage_audio_files(protocol_var):
    current_protocol = protocol_var.get()
    audio_window = tk.Toplevel(app)
    audio_window.title("Manage Audio Files for " + current_protocol)
    audio_window.geometry("600x400")
    audio_window.transient(app)
    audio_window.grab_set()

    temp_audio_files = config["protocols"][current_protocol]["audio_files"].copy()
    labels = {}

    for i in range(1, 10):
        button_label = f"Button {i} Sound"
        tk.Label(audio_window, text=button_label).grid(
            row=i - 1, column=0, padx=10, pady=5, sticky="w"
        )
        button_path = tk.Label(
            audio_window,
            text=os.path.basename(
                temp_audio_files.get(f"button_{i}_sound", "No file loaded")
            ),
        )
        button_path.grid(row=i - 1, column=1, padx=10, pady=5, sticky="w")
        labels[f"button_{i}"] = button_path
        tk.Button(
            audio_window,
            text="Load",
            command=lambda i=i: load_audio_file(f"button_{i}", labels, temp_audio_files),
        ).grid(row=i - 1, column=2, padx=10, pady=5)

    for sound_type in ["reward", "caution"]:
        row_index = 9 if sound_type == "reward" else 10
        tk.Label(audio_window, text=f"{sound_type.capitalize()} Sound").grid(
            row=row_index, column=0, padx=10, pady=5, sticky="w"
        )
        sound_path_label = tk.Label(
            audio_window,
            text=os.path.basename(
                temp_audio_files.get(f"{sound_type}_sound", "No file loaded")
            ),
        )
        sound_path_label.grid(row=row_index, column=1, padx=10, pady=5, sticky="w")
        labels[sound_type] = sound_path_label
        tk.Button(
            audio_window,
            text="Load",
            command=lambda sound_type=sound_type: load_audio_file(
                sound_type, labels, temp_audio_files
            ),
        ).grid(row=row_index, column=2, padx=10, pady=5)

    def save():
        config["protocols"][current_protocol]["audio_files"] = temp_audio_files
        audio_files.update(temp_audio_files)
        save_config(config)
        audio_window.destroy()

    tk.Button(audio_window, text="Save", command=save).grid(
        row=12, column=0, padx=10, pady=10
    )
    tk.Button(audio_window, text="Cancel", command=audio_window.destroy).grid(
        row=12, column=2, padx=10, pady=10
    )

def play_audio(sound_key):
    global sound_enabled

    protocol_settings = config["protocols"][protocol_var.get()]

    if (
        sound_key == "reward"
        and protocol_settings["reward_sound"] == "On"
        and reward_sound_enabled
    ):
        file_key = f"{sound_key}_sound"
        file_path = protocol_settings["audio_files"].get(file_key)
        if file_path:
            threading.Thread(
                target=play_audio_file, args=(file_path,), daemon=True
            ).start()
        else:
            print("No reward sound file set")
    elif sound_key.startswith("button") and sound_enabled:
        file_key = f"{sound_key}_sound"
        file_path = protocol_settings["audio_files"].get(file_key)
        if file_path:
            threading.Thread(
                target=play_audio_file, args=(file_path,), daemon=True
            ).start()
        else:
            print(f"No audio file set for {sound_key.replace('_', ' ').capitalize()}")
    elif sound_key.startswith("caution") and sound_enabled:
        file_key = f"{sound_key}_sound"
        file_path = protocol_settings["audio_files"].get(file_key)
        if file_path:
            threading.Thread(
                target=play_audio_file, args=(file_path,), daemon=True
            ).start()
        else:
            print(f"No audio file set for {sound_key.replace('_', ' ').capitalize()}")
    else:
        print(f"Sound is disabled or not configured for {sound_key}")

def play_audio_file(file_path):
    try:
        if pygame.mixer.get_init():
            # Load and play the audio file
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()

            # Wait for the music to finish playing
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
        else:
            print("Pygame mixer is not initialized")
    except Exception as e:
        print(f"Error playing audio file {file_path}: {e}")

def preload_audio_files():
    """Preload audio files to reduce delay when playing them."""
    protocol_settings = config["protocols"][protocol_var.get()]
    for sound_key, file_path in protocol_settings["audio_files"].items():
        if file_path:
            try:
                pygame.mixer.Sound(file_path)  # Preload sound
            except Exception as e:
                print(f"Error preloading audio file {file_path}: {e}")

def get_com_ports():
    return [port.device for port in serial.tools.list_ports.comports()]

def populate_com_ports():
    com_ports = get_com_ports()
    com_port_combobox["values"] = com_ports
    for port in com_ports:
        if "Arduino" in port:
            com_port_combobox.set(port)
            return
    if com_ports:
        com_port_combobox.set(com_ports[0])

def update_led_indicator(color):
    led_indicator.config(bg=color)

def connect_serial():
    selected_port = com_port_var.get().strip()
    if not selected_port:
        messagebox.showwarning("Arduino", "Select a COM port before connecting.")
        return

    disconnect_serial()
    connect_button.config(state=tk.DISABLED)
    terminal_monitor.insert(
        tk.END, f"Opening {selected_port} at {SERIAL_BAUDRATE} baud...\n"
    )
    terminal_monitor.see(tk.END)
    threading.Thread(
        target=_open_serial_worker, args=(selected_port,), daemon=True
    ).start()

def disconnect_serial():
    global arduino
    serial_stop_event.set()
    connection = arduino
    arduino = None
    if connection:
        try:
            if connection.is_open:
                connection.close()
        except (serial.SerialException, OSError):
            pass

def _open_serial_worker(selected_port):
    try:
        connection = serial.Serial(
            port=selected_port,
            baudrate=SERIAL_BAUDRATE,
            timeout=0.10,
            write_timeout=1.0,
        )
        # Opening the port normally resets an Arduino. Discard its boot/reset
        # bytes so they cannot appear as corrupted application log messages.
        connection.reset_input_buffer()
        time.sleep(SERIAL_STARTUP_DELAY_SECONDS)
        connection.reset_input_buffer()
        app.after(0, _finish_serial_connection, connection, selected_port)
    except (serial.SerialException, OSError, ValueError) as exc:
        app.after(0, _serial_connection_failed, selected_port, str(exc))

def _finish_serial_connection(connection, selected_port):
    global arduino, serial_decode_error_count
    arduino = connection
    serial_decode_error_count = 0
    serial_stop_event.clear()
    connect_button.config(state=tk.NORMAL)
    update_led_indicator("green")
    terminal_monitor.insert(
        tk.END, f"Connected to Arduino on {selected_port} at {SERIAL_BAUDRATE} baud\n"
    )
    terminal_monitor.see(tk.END)
    threading.Thread(
        target=listen_for_arduino, args=(connection,), daemon=True
    ).start()

def _serial_connection_failed(selected_port, error_message):
    connect_button.config(state=tk.NORMAL)
    update_led_indicator("red")
    terminal_monitor.insert(
        tk.END, f"Failed to connect to Arduino on {selected_port}: {error_message}\n"
    )
    terminal_monitor.see(tk.END)

def get_mac_address():
    mac = hex(uuid.getnode()).replace("0x", "").upper()
    mac = ":".join(mac[i : i + 2] for i in range(0, 12, 2))
    return mac

def get_ip_address():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address

def start_recording():
    directory = load_directory()

    if not directory:
        directory = filedialog.askdirectory(title="Select Directory")
        save_directory(directory)

    if not directory:
        messagebox.showwarning("Warning", "No directory selected. Data will not be logged.")
        return

    while True:
        dialog = CustomDialog(app)
        app.wait_window(dialog.top)

        rat_id = dialog.rat_id
        session_number = dialog.session_number
        session_date = dialog.date

        if not rat_id or not session_number or not session_date:
            messagebox.showinfo("Information", "Session start canceled by user.")
            return

        file_path = os.path.join(
            directory,
            f"SessionLog_RatID_{rat_id}_Session_{session_number}_Date_{session_date}.csv",
        )

        if os.path.exists(file_path):
            retry = messagebox.askyesno(
                "File Exists",
                f"A log file for Session {session_number} already exists. Do you want to enter new metadata?",
            )
            if not retry:
                return
        else:
            break

    global log_file, csv_writer, remaining_time, timer, recording_active

    log_file = open(file_path, mode="w", newline="")
    csv_writer = csv.writer(log_file)

    current_protocol = protocol_var.get()
    protocol_id = current_protocol
    ip_address = get_ip_address()
    protocol_settings = config["protocols"][current_protocol]

    csv_writer.writerow(["Rat ID", rat_id])
    csv_writer.writerow(["Session Number", session_number])
    csv_writer.writerow(["Date", session_date])
    csv_writer.writerow(["IP Address", ip_address])
    csv_writer.writerow(["Protocol ID", protocol_id])
    csv_writer.writerow(["Configuration", protocol_settings])

    terminal_monitor.insert(
        tk.END,
        f"Session started for Rat ID: {rat_id}, Session Number: {session_number}, Date: {session_date}\n",
    )

    csv_writer.writerow(["Timestamp", "Message"])
    send_protocol_to_arduino()

    start_button.config(state=tk.DISABLED)
    stop_button.config(state=tk.NORMAL)
    arduino.write(b"start_session\n")

    runtime_minutes = protocol_settings["runtime_minutes"]
    remaining_time = runtime_minutes * 60

    if timer:
        timer.cancel()
    timer = threading.Timer(1, countdown)
    timer.start()

    # Preload audio files after starting the session
    preload_audio_files()

    recording_active = True



def stop_recording():
    global timer, arduino, log_file, recording_active
    if log_file:
        log_file.close()
        log_file = None
        terminal_monitor.insert(tk.END, "Session ended and data saved.\n")

    # Send the final protocol settings before stopping
    send_final_protocol_to_arduino()

    start_button.config(state=tk.NORMAL)
    stop_button.config(state=tk.DISABLED)
    if timer:
        timer.cancel()
    if arduino and arduino.is_open:
        arduino.close()
        terminal_monitor.insert(tk.END, "Arduino disconnected.\n")
        update_led_indicator("red")

    recording_active = False

    # Stop OBS recording
    if obs_app and obs_app.obs_client and obs_app.obs_client.connected:
        obs_app.stop_recording()
        terminal_monitor.insert(tk.END, "Stopped OBS recording.\n")
    else:
        terminal_monitor.insert(tk.END, "Could not stop OBS recording - not connected.\n")


def send_final_protocol_to_arduino():
    # These are the settings to send when the stop button is clicked
    final_settings = {
        "sequence_1": [],
        "sequence_2": [],
        "sequence_3": [],
        "sequence_4": [],
        "Button_brightness": 128,
        "RewardLed_brightness": 128,
        "sequence_active": "Active",
        "light_guidance": "Off",
        "sound": "Off",
        "reward_led": "Off",
        "reward_shape": "rectangle",
        "reward_sound": "Off",
        "reward_amount": 0,
        "learning_correct_count": 5,
        "retrieval_error_count": 3,
        "runtime_minutes": 30,
        "audio_files": {f"button_{j}_sound": "" for j in range(1, 10)},
        "flash_path": "Off",
        # 'Random_seq': 'Off',
        "Random_chase": "Off",
        "Switching": "Off",
        "Optional_sequences": "Off",
        "Optional_Button_Led": "Off",
        "flash_count": 3
    }

    # Command to be sent to the Arduino
    command = (
        f'CONFIG,{",".join(map(str, final_settings["sequence_1"]))};'
        f'{",".join(map(str, final_settings["sequence_2"]))};'
        f'{",".join(map(str, final_settings["sequence_3"]))};'
        f'{",".join(map(str, final_settings["sequence_4"]))};'
        f'{final_settings["Button_brightness"]};'
        f'{final_settings["RewardLed_brightness"]};'
        f'{final_settings["reward_led"]};'
        f'{final_settings["reward_shape"]};'
        f'{final_settings["reward_sound"]};'
        f'{final_settings["reward_amount"]};'
        f'{final_settings["learning_correct_count"]};'
        f'{final_settings["retrieval_error_count"]};'
        f'{final_settings["sequence_active"]};'
        f'{final_settings["light_guidance"]};'
        f'{final_settings["flash_path"]};'
        # f'{final_settings["Random_seq"]};'
        f'{final_settings["Random_chase"]};'
        f'{final_settings["Switching"]};'
        f'{final_settings["Optional_sequences"]};'
        f'{final_settings["Optional_Button_Led"]};'
        f'{final_settings["flash_count"]}\n'
    )

    if arduino and arduino.is_open:
        arduino.write(command.encode())
        terminal_monitor.insert(
            tk.END, "Final configuration sent to Arduino: " + command
        )
    else:
        terminal_monitor.insert(tk.END, "Arduino connection not open\n")

def countdown():
    global remaining_time, timer
    if remaining_time > 0:
        remaining_time -= 1
        minutes, seconds = divmod(remaining_time, 60)
        runtime_label.config(text=f"Remaining Time: {minutes:02}:{seconds:02}")
        timer = threading.Timer(1, countdown)
        timer.start()
    else:
        stop_recording()

def set_directory():
    directory = filedialog.askdirectory(title="Select Directory")
    if directory:
        save_directory(directory)
        terminal_monitor.insert(tk.END, f"Save directory set to {directory}\n")

def save_directory(directory):
    config["directory"] = directory
    save_config(config)

def load_directory():
    return config.get("directory", "")

class CustomDialog:
    def __init__(self, parent):
        top = self.top = tk.Toplevel(parent)
        top.title("Session Metadata")

        tk.Label(top, text="Rat ID:").grid(row=0, column=0, padx=10, pady=5)
        self.rat_id_entry = ttk.Entry(top)
        self.rat_id_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(top, text="Session Number:").grid(row=1, column=0, padx=10, pady=5)
        self.session_number_entry = ttk.Entry(top)
        self.session_number_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(top, text="Date:").grid(row=2, column=0, padx=10, pady=5)
        self.date_entry = ttk.Entry(top)
        self.date_entry.grid(row=2, column=1, padx=10, pady=5)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        tk.Button(top, text="OK", command=self.ok).grid(
            row=3, column=0, columnspan=2, pady=10
        )

        self.rat_id = None
        self.session_number = None
        self.date = None

    def ok(self):
        self.rat_id = self.rat_id_entry.get()
        self.session_number = self.session_number_entry.get()
        self.date = self.date_entry.get()
        self.top.destroy()

def open_protocol_settings():
    protocol_window = tk.Toplevel(app)
    protocol_window.title("Protocol Parameter Setting")
    protocol_window.geometry("1920x800")
    protocol_window.transient(app)
    protocol_window.grab_set()

    global protocol_settings_combobox  # Define as global to access in update_protocol_dropdowns

    protocol_window.grid_columnconfigure(0, weight=1)
    protocol_window.grid_columnconfigure(1, weight=1)
    protocol_window.grid_columnconfigure(2, weight=1)

    font_settings = ("Helvetica", 8)  # Change to desired font and size

    tk.Label(protocol_window, text="Select Protocol", font=font_settings).grid(
        row=0, column=0, padx=10, pady=8, sticky="w"
    )
    protocol_var = tk.StringVar(value="Protocol 1")
    protocol_settings_combobox = ttk.Combobox(
        protocol_window,
        textvariable=protocol_var,
        state="readonly",
        width=10,
        font=font_settings,
    )

    # Sequence Dropdown Menu
    tk.Label(protocol_window, text="Select Sequence", font=font_settings).grid(
        row=19, column=0, padx=10, pady=8, sticky="w"
    )
    sequence_var = tk.StringVar(value="sequence_1")
    sequence_combobox = ttk.Combobox(
        protocol_window,
        textvariable=sequence_var,
        state="readonly",
        width=15,
        font=font_settings,
    )
    sequence_combobox["values"] = ("sequence_1", "sequence_2", "sequence_3", "sequence_4")
    sequence_combobox.grid(row=19, column=0, padx=200, pady=8, sticky="ew")

    protocol_settings_combobox["values"] = list(config["protocols"].keys())
    protocol_settings_combobox.grid(
        row=0, column=0, padx=200, pady=8, sticky="ew"
    )

    add_protocol_button = tk.Button(
        protocol_window, text="Add New Protocol", command=add_new_protocol
    )
    add_protocol_button.grid(row=0, column=0, padx=10, pady=8, sticky="e")

    manage_audio_button = tk.Button(
        protocol_window,
        text="Manage Audio",
        command=lambda: manage_audio_files(protocol_var),
        font=font_settings,
    )
    manage_audio_button.grid(row=1, column=0, pady=8, padx=10, sticky="ew")

    load_config_button = tk.Button(
        protocol_window,
        text="Load Configuration",
        command=load_new_config,
        font=font_settings,
    )
    load_config_button.grid(row=16, column=1, padx=10, pady=8, sticky="ew")

    tk.Label(protocol_window, text="Button Press sequence", font=font_settings).grid(
        row=2, column=0, padx=10, pady=8, sticky="w"
    )
    sequence_display = tk.Label(protocol_window, text="", font=font_settings)
    sequence_display.grid(row=2, column=0, pady=8, padx=10, sticky="e")

    tk.Label(
        protocol_window, text="Sequence Active/Inactive", font=font_settings
    ).grid(row=3, column=0, padx=10, pady=8, sticky="w")
    sequence_active_var = tk.StringVar()
    sequence_active_combobox = ttk.Combobox(
        protocol_window,
        textvariable=sequence_active_var,
        state="readonly",
        width=15,
        font=font_settings,
    )
    sequence_active_combobox["values"] = ("Active", "Inactive")
    sequence_active_combobox.grid(
        row=3, column=0, padx=10, pady=8, sticky="e"
    )

    tk.Label(protocol_window, text="Light Guidance", font=font_settings).grid(
        row=4, column=0, padx=10, pady=8, sticky="w"
    )
    light_guidance_var = tk.StringVar()
    light_guidance_combobox = ttk.Combobox(
        protocol_window,
        textvariable=light_guidance_var,
        state="readonly",
        width=15,
        font=font_settings,
    )
    light_guidance_combobox["values"] = ("On", "Off")
    light_guidance_combobox.grid(row=4, column=0, padx=10, pady=8, sticky="e")

    tk.Label(
        protocol_window, text="Button LED Brightness", font=font_settings
    ).grid(row=5, column=0, padx=10, pady=8, sticky="w")
    button_brightness_slider = tk.Scale(
        protocol_window, from_=0, to=255, orient="horizontal", font=font_settings
    )
    button_brightness_slider.grid(row=5, column=0, padx=10, pady=8, sticky="e")

    tk.Label(
        protocol_window, text="Reward LED Brightness", font=font_settings
    ).grid(row=6, column=0, padx=10, pady=8, sticky="w")
    reward_led_brightness_slider = tk.Scale(
        protocol_window, from_=0, to=255, orient="horizontal", font=font_settings
    )
    reward_led_brightness_slider.grid(
        row=6, column=0, padx=10, pady=8, sticky="e"
    )

    # tk.Label(protocol_window, text='Randomised Sequence', font=font_settings).grid(row=7, column=0, padx=10, pady=8, sticky='w')
    # Random_seq_var = tk.StringVar()
    # Random_seq_combobox = ttk.Combobox(protocol_window, textvariable=Random_seq_var, state='readonly', width=15, font=font_settings)
    # Random_seq_combobox['values'] = ('On', 'Off')
    # Random_seq_combobox.grid(row=7, column=0, padx=10, pady=8, sticky='e')
    tk.Label(
        protocol_window, text="Optional_sequences", font=font_settings
    ).grid(row=20, column=0, padx=10, pady=8, sticky="w")
    Optional_sequences_var = tk.StringVar()
    Optional_sequences_combobox = ttk.Combobox(
        protocol_window,
        textvariable= Optional_sequences_var,
        state="readonly",
        width=15,
        font=font_settings,
    )
    Optional_sequences_combobox["values"] = ("On", "Off")
    Optional_sequences_combobox.grid(row=20, column=0, padx=10, pady=8, sticky="e")

    tk.Label(
        protocol_window, text="Optional_Button_Led", font=font_settings
    ).grid(row=21, column=0, padx=10, pady=8, sticky="w")
    Optional_Button_Led_var = tk.StringVar()
    Optional_Button_Led_combobox = ttk.Combobox(
        protocol_window,
        textvariable= Optional_Button_Led_var,
        state="readonly",
        width=15,
        font=font_settings,
    )
    Optional_Button_Led_combobox["values"] = ("On", "Off")
    Optional_Button_Led_combobox.grid(row=21, column=0, padx=10, pady=8, sticky="e")


    tk.Label(
        protocol_window, text="Randomised Chasing", font=font_settings
    ).grid(row=7, column=0, padx=10, pady=8, sticky="w")
    Random_chase_var = tk.StringVar()
    Random_chase_combobox = ttk.Combobox(
        protocol_window,
        textvariable=Random_chase_var,
        state="readonly",
        width=15,
        font=font_settings,
    )
    Random_chase_combobox["values"] = ("On", "Off")
    Random_chase_combobox.grid(row=7, column=0, padx=10, pady=8, sticky="e")

    tk.Label(
        protocol_window, text="Switching learning and retrieval", font=font_settings
    ).grid(row=8, column=0, padx=10, pady=8, sticky="w")
    Switching_var = tk.StringVar()
    Switching_combobox = ttk.Combobox(
        protocol_window,
        textvariable=Switching_var,
        state="readonly",
        width=15,
        font=font_settings,
    )
    Switching_combobox["values"] = ("On", "Off")
    Switching_combobox.grid(row=8, column=0, padx=10, pady=8, sticky="e")

    tk.Label(
        protocol_window, text="Switching after Correct in learning count:", font=font_settings
    ).grid(row=9, column=0, padx=10, pady=8, sticky="w")
    learning_correct_count_var = tk.IntVar()
    learning_correct_count_combobox = ttk.Combobox(
        protocol_window,
        textvariable=learning_correct_count_var,
        values=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
        state="readonly",
        font=font_settings,
    )
    learning_correct_count_combobox.grid(
        row=9, column=0, padx=10, pady=8, sticky="e"
    )

    tk.Label(
        protocol_window, text="Switching after error in retrieval count:", font=font_settings
    ).grid(row=10, column=0, padx=10, pady=8, sticky="w")
    retrieval_error_count_var = tk.IntVar()
    retrieval_error_count_combobox = ttk.Combobox(
        protocol_window,
        textvariable=retrieval_error_count_var,
        values=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
        state="readonly",
        font=font_settings,
    )
    retrieval_error_count_combobox.grid(
        row=10, column=0, padx=10, pady=8, sticky="e"
    )

    tk.Label(protocol_window, text="Button Sound", font=font_settings).grid(
        row=11, column=0, padx=10, pady=8, sticky="w"
    )
    sound_var = tk.StringVar()
    sound_combobox = ttk.Combobox(
        protocol_window,
        textvariable=sound_var,
        state="readonly",
        width=15,
        font=font_settings,
    )
    sound_combobox["values"] = ("On", "Off")
    sound_combobox.grid(row=11, column=0, padx=10, pady=8, sticky="e")

    tk.Label(protocol_window, text="Reward LED Status:", font=font_settings).grid(
        row=12, column=0, padx=10, pady=8, sticky="w"
    )
    reward_led_status_var = tk.StringVar()
    reward_led_status_combobox = ttk.Combobox(
        protocol_window,
        textvariable=reward_led_status_var,
        state="readonly",
        width=15,
        font=font_settings,
    )
    reward_led_status_combobox["values"] = ("On", "Off")
    reward_led_status_combobox.grid(
        row=12, column=0, padx=10, pady=8, sticky="e"
    )

    tk.Label(protocol_window, text="Reward LED Shape:", font=font_settings).grid(
        row=13, column=0, padx=10, pady=8, sticky="w"
    )
    reward_led_shape_var = tk.StringVar()
    reward_led_shape_combobox = ttk.Combobox(
        protocol_window,
        textvariable=reward_led_shape_var,
        state="readonly",
        width=15,
        font=font_settings,
    )
    reward_led_shape_combobox["values"] = (
        "rectangle",
        "circle",
        "cross",
        "triangle",
        "pentagon",
        "star",
    )
    reward_led_shape_combobox.grid(row=13, column=0, padx=10, pady=8, sticky="e")

    tk.Label(protocol_window, text="Reward Sound Status:", font=font_settings).grid(
        row=14, column=0, padx=10, pady=8, sticky="w"
    )
    reward_sound_var = tk.StringVar()
    reward_sound_combobox = ttk.Combobox(
        protocol_window,
        textvariable=reward_sound_var,
        values=("On", "Off"),
        state="readonly",
        font=font_settings,
    )
    reward_sound_combobox.grid(row=14, column=0, padx=10, pady=8, sticky="e")

    tk.Label(protocol_window, text="Reward Amount:", font=font_settings).grid(
        row=15, column=0, padx=10, pady=8, sticky="w"
    )
    reward_amount_var = tk.IntVar()
    reward_amount_combobox = ttk.Combobox(
        protocol_window,
        textvariable=reward_amount_var,
        values=(1, 2, 3, 4, 5, 20, 50),
        state="readonly",
        font=font_settings,
    )
    reward_amount_combobox.grid(row=15, column=0, padx=10, pady=8, sticky="e")

    tk.Label(protocol_window, text="Runtime (in minutes):", font=font_settings).grid(
        row=16, column=0, padx=10, pady=8, sticky="w"
    )
    runtime_var = tk.IntVar()
    runtime_spinbox = tk.Spinbox(
        protocol_window, from_=1, to=120, textvariable=runtime_var, width=7, font=font_settings
    )
    runtime_spinbox.grid(row=16, column=0, padx=10, pady=8, sticky="e")

    tk.Label(protocol_window, text="Flash Path", font=font_settings).grid(
        row=17, column=0, padx=10, pady=8, sticky="w"
    )
    flash_path_var = tk.StringVar()
    flash_path_combobox = ttk.Combobox(
        protocol_window,
        textvariable=flash_path_var,
        state="readonly",
        width=15,
        font=font_settings,
    )
    flash_path_combobox["values"] = ("On", "Off")
    flash_path_combobox.grid(row=17, column=0, padx=10, pady=8, sticky="e")

    tk.Label(protocol_window, text="Flash Count", font=font_settings).grid(
        row=18, column=0, padx=10, pady=8, sticky="w"
    )
    flash_count_var = tk.IntVar()
    flash_count_spinbox = tk.Spinbox(
        protocol_window, from_=1, to=10, textvariable=flash_count_var, width=7, font=font_settings
    )
    flash_count_spinbox.grid(row=18, column=0, padx=10, pady=8, sticky="e")

    numpad_frame = tk.Frame(protocol_window)
    numpad_frame.grid(row=0, column=1, rowspan=15, padx=20, pady=20, sticky="ns")


    num_buttons = {}
    for i in range(9):
        num = i + 1
        num_buttons[num] = tk.Button(
            numpad_frame,
            text=str(num),
            width=10,
            height=5,
            command=lambda num=num: toggle_protocol(num),
        )
        num_buttons[num].grid(row=i // 3, column=i % 3)


    def update_ui():
        update_protocol_dropdowns()  # Ensure dropdowns are updated
        current_protocol = protocol_var.get()
        
        # Check if the selected protocol is valid, else revert to the default protocol
        if (current_protocol not in config["protocols"]) and (default_protocol in config["protocols"]):
            protocol_var.set(default_protocol)
        current_protocol = protocol_var.get()  # Update current protocol again if changed
        
        # Set sequence_var to "sequence_1" if it's not set or if it has an invalid value
        if sequence_var.get() not in ["sequence_1", "sequence_2", "sequence_3", "sequence_4"]:
            sequence_var.set("sequence_1")

        selected_sequence = sequence_var.get()
        settings = config["protocols"][current_protocol]

        # Display the selected sequence
        sequence_display.config(text="Sequence: " + "->".join(map(str, settings[selected_sequence])))

        # Set other UI elements based on the current settings
        button_brightness_slider.set(settings["Button_brightness"])
        reward_led_brightness_slider.set(settings["RewardLed_brightness"])
        sound_combobox.set(settings["sound"])
        global sound_enabled
        sound_enabled = settings["sound"] == "On"
        reward_led_status_combobox.set(settings["reward_led"])
        reward_led_shape_combobox.set(settings["reward_shape"])
        reward_sound_combobox.set(settings["reward_sound"])
        sequence_active_combobox.set(settings["sequence_active"])
        light_guidance_combobox.set(settings["light_guidance"])
        Random_chase_combobox.set(settings["Random_chase"])
        Optional_sequences_combobox.set(settings["Optional_sequences"])
        Optional_Button_Led_combobox.set(settings["Optional_Button_Led"])
        Switching_combobox.set(settings["Switching"])
        reward_sound_enabled = settings["reward_sound"] == "On"
        reward_amount_combobox.set(settings["reward_amount"])
        learning_correct_count_combobox.set(settings["learning_correct_count"])
        retrieval_error_count_combobox.set(settings["retrieval_error_count"])
        runtime_spinbox.delete(0, tk.END)
        runtime_spinbox.insert(0, settings["runtime_minutes"])
        flash_path_combobox.set(settings["flash_path"])
        flash_count_spinbox.delete(0, tk.END)
        flash_count_spinbox.insert(0, settings["flash_count"])

        # Highlight buttons based on the active sequence
        highlight_sequence_buttons()
    sequence_combobox.bind("<<ComboboxSelected>>", lambda event: update_ui())

    def toggle_protocol(num):
        current_protocol = protocol_var.get()
        selected_sequence = sequence_var.get() 
        settings = config["protocols"][current_protocol]
        settings["Button_brightness"] = button_brightness_slider.get()
        settings["RewardLed_brightness"] = reward_led_brightness_slider.get()
        settings["sound"] = sound_var.get()
        settings["reward_led"] = reward_led_status_var.get()
        settings["reward_shape"] = reward_led_shape_var.get()
        settings["reward_sound"] = reward_sound_var.get()
        settings["reward_amount"] = reward_amount_var.get()
        settings["learning_correct_count"] = learning_correct_count_var.get()
        settings["retrieval_error_count"] = retrieval_error_count_var.get()
        settings["runtime_minutes"] = runtime_var.get()
        # settings['Random_seq'] = Random_seq_var.get()
        settings["Random_chase"] = Random_chase_var.get()
        settings["Optional_sequences"] = Optional_sequences_var.get()
        settings["Optional_Button_Led"] = Optional_Button_Led_var.get()
        settings["Switching"] = Switching_var.get()
        settings["sequence_active"] = sequence_active_var.get()
        settings["light_guidance"] = light_guidance_var.get()
        settings["flash_path"] = flash_path_var.get()
        settings["flash_count"] = flash_count_var.get()
        # if num in config["protocols"][current_protocol]["sequence_1"]:
        #     config["protocols"][current_protocol]["sequence"].remove(num)
        # else:
        #     config["protocols"][current_protocol]["sequence"].append(num)
        # update_ui()


    
    # Toggle sequence number selection
        if num in settings[selected_sequence]:
            settings[selected_sequence].remove(num)
        else:
            settings[selected_sequence].append(num)

        update_ui()

    def highlight_sequence_buttons():
        current_protocol = protocol_var.get()
        selected_sequence = sequence_var.get()
        for num in range(1, 10):
            if num in config["protocols"][current_protocol][selected_sequence]:
                num_buttons[num].config(bg="light blue")
            else:
                num_buttons[num].config(bg="SystemButtonFace")

    def save_and_close():
        current_protocol = protocol_var.get()
        settings = config["protocols"][current_protocol]
        settings["Button_brightness"] = button_brightness_slider.get()
        settings["RewardLed_brightness"] = reward_led_brightness_slider.get()
        settings["sound"] = sound_var.get()
        global sound_enabled
        sound_enabled = settings["sound"] == "On"
        settings["reward_led"] = reward_led_status_var.get()
        settings["reward_shape"] = reward_led_shape_var.get()
        settings["reward_sound"] = reward_sound_var.get()
        global reward_sound_enabled
        reward_sound_enabled = settings["reward_sound"] == "On"
        settings["reward_amount"] = reward_amount_var.get()
        settings["learning_correct_count"] = learning_correct_count_var.get()
        settings["retrieval_error_count"] = retrieval_error_count_var.get()
        settings["runtime_minutes"] = runtime_var.get()
        # settings['Random_seq'] = Random_seq_var.get()
        settings["Random_chase"] = Random_chase_var.get()
        settings["Optional_sequences"] = Optional_sequences_var.get()
        settings["Optional_Button_Led"] = Optional_Button_Led_var.get()
        settings["Switching"] = Switching_var.get()
        settings["sequence_active"] = sequence_active_var.get()
        settings["light_guidance"] = light_guidance_var.get()
        settings["flash_path"] = flash_path_var.get()
        settings["flash_count"] = flash_count_var.get()
        save_config(config)
        protocol_window.destroy()

    def export_protocol():
        """Export the current protocol settings to a JSON file in the desired format."""
        current_protocol = protocol_var.get()
        settings = config["protocols"][current_protocol]

        # Structure the export with the top-level "protocols" key
        export_data = {
            "protocols": {
                current_protocol: {
                    "sequence_1": settings["sequence_1"],
                    "sequence_2": settings["sequence_2"],
                    "sequence_3": settings["sequence_3"],
                    "sequence_4": settings["sequence_4"],
                    "Button_brightness": settings["Button_brightness"],
                    "RewardLed_brightness": settings["RewardLed_brightness"],
                    "sequence_active": settings["sequence_active"],
                    "light_guidance": settings["light_guidance"],
                    "sound": settings["sound"],
                    "reward_led": settings["reward_led"],
                    "reward_shape": settings["reward_shape"],
                    "reward_sound": settings["reward_sound"],
                    "reward_amount": settings["reward_amount"],
                    "runtime_minutes": settings["runtime_minutes"],
                    "audio_files": settings["audio_files"],
                    "flash_path": settings["flash_path"],
                    "flash_count": settings["flash_count"],
                    "learning_correct_count": settings["learning_correct_count"],
                    "retrieval_error_count": settings["retrieval_error_count"],
                    # "Random_seq": settings["Random_seq"],
                    "Random_chase": settings["Random_chase"],
                    "Optional_sequences": settings["Optional_sequences"],
                    "Optional_Button_Led":settings["Optional_Button_Led"],
                    "Switching": settings["Switching"],
                }
            }
        }

        directory = filedialog.askdirectory(title="Select Directory")
        if directory:
            file_path = os.path.join(directory, f"{current_protocol}_settings.json")
            with open(file_path, "w") as f:
                json.dump(export_data, f, indent=4)
            messagebox.showinfo(
                "Export Successful", f"Protocol settings exported to {file_path}"
            )

    export_button = tk.Button(
        protocol_window, text="Export Protocol", command=export_protocol
    )
    export_button.grid(row=20, column=1, padx=10, pady=10, sticky="e")

    save_button = tk.Button(
        protocol_window, text="Save Config and Close", command=save_and_close
    )
    save_button.grid(row=22, column=0, padx=10, pady=10, sticky="e")

    cancel_button = tk.Button(
        protocol_window, text="Cancel", command=protocol_window.destroy
    )
    cancel_button.grid(row=22, column=0, padx=10, pady=10, sticky="w")

    protocol_settings_combobox.bind(
        "<<ComboboxSelected>>", lambda e: update_ui()
    )
    update_ui()

def add_new_protocol():
    new_protocol_name = simpledialog.askstring("Input", "Enter the name for the new protocol:")
    if new_protocol_name:
        if new_protocol_name in config["protocols"]:
            messagebox.showerror("Error", "Protocol name already exists.")
        else:
            config["protocols"][new_protocol_name] = default_protocol_config()
            save_config(config)
            protocol_var.set(new_protocol_name)
            update_protocol_dropdowns()
            update_ui()
            messagebox.showinfo(
                "Success", f"Protocol '{new_protocol_name}' added successfully."
            )

def default_protocol_config():
    return {
        "sequence_1": [],
        "sequence_2": [],
        "sequence_3": [],
        "sequence_4": [],
        "Button_brightness": 128,
        "RewardLed_brightness": 128,
        "sequence_active": "Active",
        "light_guidance": "Off",
        "sound": "Off",
        "reward_led": "Off",
        "reward_shape": "rectangle",
        "reward_sound": "Off",
        "reward_amount": 1,
        "learning_correct_count": 5,
        "retrieval_error_count": 3,
        "runtime_minutes": 30,
        "audio_files": {f"button_{j}_sound": "" for j in range(1, 10)},
        "flash_path": "Off",
        # 'Random_seq': 'Off',
        "Random_chase": "Off",
        "Optional_sequences":"Off",
        "Optional_Button_Led":"Off",
        "Switching": "Off",
        "flash_count": 3,
    }

config = load_config()

app = tk.Tk()
app.title("Main Application")

config = load_config()

arduino = None

default_protocol = list(config["protocols"].keys())[0] if config["protocols"] else None

app.grid_columnconfigure(0, weight=1)
app.grid_columnconfigure(1, weight=1)

# Detect screen resolution
screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()

# Calculate window size and position
window_width = int(screen_width * 0.8)  # 80% of screen width
window_height = int(screen_height * 0.8)  # 80% of screen height
position_right = int(screen_width * 0.1)  # Center the window
position_down = int(screen_height * 0.1)  # Center the window

app.geometry(f"{window_width}x{window_height}+{position_right}+{position_down}")

# Scale factor for widgets and fonts
scale_x = screen_width / 1920  # Reference width
scale_y = screen_height / 1080  # Reference height

# Create a main frame to hold all widgets
main_frame = tk.Frame(app)
main_frame.place(relx=0, rely=0, relwidth=0.7, relheight=1)

# Protocol Controls
protocol_frame = tk.LabelFrame(main_frame, text="Protocol Controls", padx=5, pady=5)  # Reduced padding
protocol_frame.place(relx=0, rely=0, relwidth=0.5, relheight=0.8)  # Increased height slightly

open_protocol_button = tk.Button(
    protocol_frame, text="Open Protocol Settings", command=open_protocol_settings
)
open_protocol_button.place(relx=0, rely=0, relwidth=0.4, relheight=0.05)  # Further reduced height

protocol_var = tk.StringVar(value=default_protocol)
protocol_combobox = ttk.Combobox(
    protocol_frame, textvariable=protocol_var, state="readonly", width=40
)
protocol_combobox["values"] = list(config["protocols"].keys())
protocol_combobox.place(relx=0.5, rely=0, relwidth=0.5, relheight=0.05)  # Further reduced height
protocol_combobox.bind("<<ComboboxSelected>>", lambda _: update_ui())

tk.Label(protocol_frame, text="Active Buttons:").place(
    relx=0, rely=0.06, relwidth=0.4, relheight=0.05  # Adjusted rely and height
)
sequence_display = tk.Label(protocol_frame, text="")
sequence_display.place(relx=0.5, rely=0.06, relwidth=0.5, relheight=0.05)  # Adjusted rely and height

tk.Label(protocol_frame, text="Sequence Active:").place(
    relx=0, rely=0.12, relwidth=0.4, relheight=0.05  # Adjusted rely and height
)
sequence_active_display = tk.Label(protocol_frame, text="")
sequence_active_display.place(relx=0.5, rely=0.12, relwidth=0.5, relheight=0.05)  # Adjusted rely and height

tk.Label(protocol_frame, text="Randomised Chase:").place(
    relx=0, rely=0.18, relwidth=0.4, relheight=0.05  # Adjusted rely and height
)
Randomised_chase_display = tk.Label(protocol_frame, text="")
Randomised_chase_display.place(relx=0.5, rely=0.18, relwidth=0.5, relheight=0.05)  # Adjusted rely and height

tk.Label(protocol_frame, text="Button_Brightness:").place(
    relx=0, rely=0.24, relwidth=0.4, relheight=0.05  # Adjusted rely and height
)
brightness_display = tk.Label(protocol_frame, text="")
brightness_display.place(relx=0.5, rely=0.24, relwidth=0.5, relheight=0.05)  # Adjusted rely and height

tk.Label(protocol_frame, text="Button Sound:").place(
    relx=0, rely=0.30, relwidth=0.4, relheight=0.05  # Adjusted rely and height
)
sound_display = tk.Label(protocol_frame, text="")
sound_display.place(relx=0.5, rely=0.30, relwidth=0.5, relheight=0.05)  # Adjusted rely and height

tk.Label(protocol_frame, text="Reward LED:").place(
    relx=0, rely=0.36, relwidth=0.4, relheight=0.05  # Adjusted rely and height
)
reward_led_display = tk.Label(protocol_frame, text="")
reward_led_display.place(relx=0.5, rely=0.36, relwidth=0.5, relheight=0.05)  # Adjusted rely and height

tk.Label(protocol_frame, text="Reward Shape:").place(
    relx=0, rely=0.42, relwidth=0.4, relheight=0.05  # Adjusted rely and height
)
reward_shape_display = tk.Label(protocol_frame, text="")
reward_shape_display.place(relx=0.5, rely=0.42, relwidth=0.5, relheight=0.05)  # Adjusted rely and height

tk.Label(protocol_frame, text="Reward Sound:").place(
    relx=0, rely=0.48, relwidth=0.4, relheight=0.05  # Adjusted rely and height
)
reward_sound_display = tk.Label(protocol_frame, text="")
reward_sound_display.place(relx=0.5, rely=0.48, relwidth=0.5, relheight=0.05)  # Adjusted rely and height

tk.Label(protocol_frame, text="Reward Amount:").place(
    relx=0, rely=0.54, relwidth=0.4, relheight=0.05  # Adjusted rely and height
)
reward_amount_display = tk.Label(protocol_frame, text="")
reward_amount_display.place(relx=0.5, rely=0.54, relwidth=0.5, relheight=0.05)  # Adjusted rely and height

tk.Label(protocol_frame, text="Runtime Minutes:").place(
    relx=0, rely=0.60, relwidth=0.4, relheight=0.05  # Adjusted rely and height
)
runtime_minutes_display = tk.Label(protocol_frame, text="")
runtime_minutes_display.place(relx=0.5, rely=0.60, relwidth=0.5, relheight=0.05)  # Adjusted rely and height

tk.Label(protocol_frame, text="Light Guidance:").place(
    relx=0, rely=0.66, relwidth=0.4, relheight=0.05  # Adjusted rely and height
)
light_guidance_display = tk.Label(protocol_frame, text="")
light_guidance_display.place(relx=0.5, rely=0.66, relwidth=0.5, relheight=0.05)  # Adjusted rely and height

tk.Label(protocol_frame, text="Flash Path:").place(
    relx=0, rely=0.72, relwidth=0.4, relheight=0.05  # Adjusted rely and height
)
flash_path_display = tk.Label(protocol_frame, text="")
flash_path_display.place(relx=0.5, rely=0.72, relwidth=0.5, relheight=0.05)  # Adjusted rely and height

tk.Label(protocol_frame, text="Flash Count:").place(
    relx=0, rely=0.78, relwidth=0.4, relheight=0.05  # Adjusted rely and height
)
flash_count_display = tk.Label(protocol_frame, text="")
flash_count_display.place(relx=0.5, rely=0.78, relwidth=0.5, relheight=0.05)  # Adjusted rely and height





# Number pad and terminal monitor
numpad_terminal_frame = tk.LabelFrame(main_frame, text="Active Button Display", padx=10, pady=10)
numpad_terminal_frame.place(relx=0.5, rely=0, relwidth=0.5, relheight=1)

# Number pad for sequences
numpad_frame = tk.Frame(numpad_terminal_frame)
numpad_frame.pack(padx=10, pady=10)

num_buttons = {}
for i in range(9):
    num = i + 1
    num_buttons[num] = tk.Button(numpad_frame, text=str(num), width=10, height=5, state="disabled")
    num_buttons[num].grid(row=i // 3, column=i % 3)

def highlight_sequence_buttons():
    current_protocol = protocol_var.get()
    for num in range(1, 10):
        if num in config["protocols"][current_protocol]["sequence_1"]:
            num_buttons[num].config(bg="light blue")
        else:
            num_buttons[num].config(bg="SystemButtonFace")

# Terminal Display
terminal_monitor = scrolledtext.ScrolledText(numpad_terminal_frame, height=15, width=60, wrap="word")
terminal_monitor.pack(fill="both", expand=True, padx=10, pady=10)

def update_ui():
    highlight_sequence_buttons()
    current_protocol = protocol_var.get()
    settings = config["protocols"].get(current_protocol, None)
    if settings:
        sequence_display.config(text=str(settings["sequence_1"]))
        sequence_active_display.config(text=str(settings["sequence_active"]))
        # Randomised_Sequence_display.config(text=settings['Random_seq'])
        Randomised_chase_display.config(text=settings["Random_chase"])
        brightness_display.config(text=str(settings["Button_brightness"]))
        sound_display.config(text=settings["sound"])
        global sound_enabled
        sound_enabled = settings["sound"] == "On"
        reward_led_display.config(text=settings["reward_led"])
        reward_shape_display.config(text=settings["reward_shape"])
        reward_sound_display.config(text=settings["reward_sound"])
        global reward_sound_enabled
        reward_sound_enabled = settings["reward_sound"] == "On"
        reward_amount_display.config(text=str(settings["reward_amount"]))
        runtime_minutes_display.config(text=str(settings["runtime_minutes"]))
        light_guidance_display.config(text=settings["light_guidance"])
        flash_path_display.config(text=settings["flash_path"])
        flash_count_display.config(text=str(settings["flash_count"]))
    else:
        print(f"No settings found for {current_protocol}")

if default_protocol:
    update_ui()

protocol_combobox.bind("<<ComboboxSelected>>", lambda _: update_ui())
update_ui()

def send_protocol_to_arduino():
    current_protocol = protocol_var.get()
    settings = config["protocols"][current_protocol]
    protocol_id = current_protocol.split(" ")[-1]
    command = f'CONFIG,{",".join(map(str, settings["sequence_1"]))};{",".join(map(str, settings["sequence_2"]))};{",".join(map(str, settings["sequence_3"]))};{",".join(map(str, settings["sequence_4"]))};{settings["Button_brightness"]};{settings["RewardLed_brightness"]};{settings["reward_led"]};{settings["reward_shape"]};{settings["reward_sound"]};{settings["reward_amount"]};{settings["learning_correct_count"]};{settings["retrieval_error_count"]};{settings["sequence_active"]};{settings["light_guidance"]};{settings["flash_path"]};{settings["Random_chase"]}; {settings["Random_chase"]};{settings["Switching"]};{settings["Optional_sequences"]};{settings["Optional_Button_Led"]};{settings["flash_count"]}\n'

    if arduino and arduino.is_open:
        arduino.write(command.encode())
        terminal_monitor.insert(tk.END, "Configuration sent to Arduino: " + command)
    else:
        terminal_monitor.insert(tk.END, "Arduino connection not open\n")

# def listen_for_arduino():
#     while arduino and arduino.is_open:
#         try:
#             if arduino.in_waiting:
#                 message = arduino.readline().decode().strip()

#                 # Split the message to extract the timestamp and the actual message
#                 if " ms] " in message:
#                     _, actual_message = message.split(" ms] ", 1)
#                 else:
#                     actual_message = message

#                 timestamp = datetime.now().strftime("%m/%d/%Y %H:%M:%S.%f")[:-3]
#                 log_entry = f"{timestamp} - {message}"
#                 terminal_monitor.insert(tk.END, log_entry + "\n")
#                 terminal_monitor.see(tk.END)
#                 if recording_active and "csv_writer" in globals() and log_file:
#                     csv_writer.writerow([timestamp, message])
#                     log_file.flush()

#                 if actual_message.startswith("audio_"):
#                     audio_index = int(actual_message.split("_")[1])
#                     sound_key = f"button_{audio_index}"
#                     play_audio(sound_key)
#                 elif actual_message == "reward_sound":
#                     play_audio("reward")
#                 elif actual_message == "caution_sound":
#                     play_audio("caution")
#         except Exception as e:
#             print(f"Error reading from serial port: {e}")





def listen_for_arduino(connection):
    """Collect complete byte lines without touching Tk from this thread."""
    buffer = bytearray()
    last_data_time = time.monotonic()
    try:
        while (
            not serial_stop_event.is_set()
            and connection.is_open
            and arduino is connection
        ):
            waiting = connection.in_waiting
            chunk = connection.read(waiting if waiting else 1)
            now = time.monotonic()
            if chunk:
                buffer.extend(chunk)
                last_data_time = now
                while b"\n" in buffer:
                    raw_line, _, remainder = buffer.partition(b"\n")
                    buffer = bytearray(remainder)
                    serial_rx_queue.put(("data", bytes(raw_line).rstrip(b"\r")))
                if len(buffer) > 4096:
                    serial_rx_queue.put(("invalid", bytes(buffer[:64])))
                    buffer.clear()
            elif buffer and now - last_data_time > 0.25:
                serial_rx_queue.put(("data", bytes(buffer).rstrip(b"\r")))
                buffer.clear()
    except (serial.SerialException, OSError) as exc:
        serial_rx_queue.put(("error", str(exc)))

def _serial_text_is_valid(message):
    if not message or len(message) > 1024:
        return False
    return all(
        (32 <= ord(character) <= 126) or character == "\t"
        for character in message
    )

def process_serial_bytes(raw_message):
    global serial_decode_error_count
    raw_message = raw_message.strip(b"\x00\r\n")
    if not raw_message:
        return
    try:
        message = raw_message.decode("ascii", errors="strict").strip()
    except UnicodeDecodeError:
        message = ""

    if not _serial_text_is_valid(message):
        serial_decode_error_count += 1
        if serial_decode_error_count == 1 or serial_decode_error_count % 20 == 0:
            sample = raw_message[:16].hex(" ")
            terminal_monitor.insert(
                tk.END,
                "Unreadable serial bytes discarded "
                f"(sample: {sample}). Confirm Arduino Serial.begin({SERIAL_BAUDRATE}).\n",
            )
            terminal_monitor.see(tk.END)
        return

    serial_decode_error_count = 0
    if " ms] " in message:
        _, actual_message = message.split(" ms] ", 1)
    else:
        actual_message = message

    timestamp = datetime.now().strftime("%m/%d/%Y %H:%M:%S.%f")[:-3]
    terminal_monitor.insert(tk.END, f"{timestamp} - {message}\n")
    terminal_monitor.see(tk.END)

    if recording_active and "csv_writer" in globals() and log_file:
        try:
            csv_writer.writerow([timestamp, message])
            log_file.flush()
        except (OSError, ValueError) as exc:
            terminal_monitor.insert(tk.END, f"Log write error: {exc}\n")

    if actual_message.startswith("audio_"):
        try:
            audio_index = int(actual_message.split("_", 1)[1])
        except (ValueError, IndexError):
            return
        if 1 <= audio_index <= 9:
            play_audio(f"button_{audio_index}")
    elif actual_message == "reward_sound":
        play_audio("reward")
    elif actual_message == "caution_sound":
        play_audio("caution")

def poll_serial_queue():
    processed = 0
    while processed < 100:
        try:
            kind, payload = serial_rx_queue.get_nowait()
        except queue.Empty:
            break
        processed += 1
        if kind in ("data", "invalid"):
            process_serial_bytes(payload)
        elif kind == "error":
            terminal_monitor.insert(tk.END, f"Serial connection error: {payload}\n")
            terminal_monitor.see(tk.END)
            disconnect_serial()
            update_led_indicator("red")
    try:
        app.after(30, poll_serial_queue)
    except tk.TclError:
        pass


def signal_handler(sig, frame):
    print("Exiting gracefully")
    stop_recording()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Send Protocol and Serial Connection
# control_frame = tk.LabelFrame(main_frame, text="Controls", padx=10, pady=10)
# control_frame.place(relx=0, rely=0.7, relwidth=0.5, relheight=0.5)

# connect_button = tk.Button(control_frame, text="Connect", command=connect_serial)
# connect_button.place(relx=0, rely=0, relwidth=0.4, relheight=0.1)

# send_protocol_button = tk.Button(
#     control_frame, text="Send Protocol to Arduino", command=send_protocol_to_arduino
# )
# send_protocol_button.place(relx=0, rely=0.1, relwidth=0.4, relheight=0.1)

# com_port_var = tk.StringVar()
# com_port_combobox = ttk.Combobox(control_frame, textvariable=com_port_var, state="readonly", width=40)
# com_port_combobox.place(relx=0.4, rely=0.0, relwidth=0.5, relheight=0.1)
# populate_com_ports()

# led_indicator = tk.Label(control_frame, text=" ", bg="red", width=2, height=1)
# led_indicator.place(relx=0.91, rely=0, relwidth=0.05, relheight=0.1)

# set_directory_button = tk.Button(control_frame, text="Set Save Directory", command=set_directory)
# set_directory_button.place(relx=0, rely=0.2, relwidth=0.4, relheight=0.1)

# start_button = tk.Button(control_frame, text="Start Recording", command=start_recording)
# start_button.place(relx=0, rely=0.3, relwidth=0.4, relheight=0.1)

# stop_button = tk.Button(control_frame, text="Stop Recording", command=stop_recording, state=tk.DISABLED)
# stop_button.place(relx=0.5, rely=0.3, relwidth=0.4, relheight=0.1)




control_frame = tk.LabelFrame(main_frame, text="Controls", padx=10, pady=10)
control_frame.place(relx=0, rely=0.7, relwidth=0.5, relheight=0.5)

connect_button = tk.Button(control_frame, text="Connect", command=connect_serial)
connect_button.place(relx=0, rely=0, relwidth=0.4, relheight=0.1)

send_protocol_button = tk.Button(
    control_frame, text="Send Protocol to Arduino", command=send_protocol_to_arduino
)
send_protocol_button.place(relx=0, rely=0.1, relwidth=0.4, relheight=0.1)

com_port_var = tk.StringVar()
com_port_combobox = ttk.Combobox(control_frame, textvariable=com_port_var, state="readonly", width=40)
com_port_combobox.place(relx=0.5, rely=0.0, relwidth=0.4, relheight=0.1)
populate_com_ports()

# Refresh button to update COM ports
refresh_button = tk.Button(control_frame, text="Refresh COM Ports", command=populate_com_ports)
refresh_button.place(relx=0.5, rely=0.1, relwidth=0.4, relheight=0.1)

led_indicator = tk.Label(control_frame, text=" ", bg="red", width=2, height=1)
led_indicator.place(relx=0.94, rely=0, relwidth=0.04, relheight=0.1)

set_directory_button = tk.Button(control_frame, text="Set Save Directory", command=set_directory)
set_directory_button.place(relx=0, rely=0.2, relwidth=0.4, relheight=0.1)

runtime_label = tk.Label(control_frame, text="Remaining Time: 00:00")
runtime_label.place(relx=0.5, rely=0.2, relwidth=0.4, relheight=0.1)  # Adjusted rely and height


start_button = tk.Button(control_frame, text="Start Recording", command=start_recording)
start_button.place(relx=0, rely=0.3, relwidth=0.4, relheight=0.1)

stop_button = tk.Button(control_frame, text="Stop Recording", command=stop_recording, state=tk.DISABLED)
stop_button.place(relx=0.5, rely=0.3, relwidth=0.4, relheight=0.1)



app.protocol("WM_DELETE_WINDOW", on_app_close)

# Initialize OBS Control in the top right corner
obs_app = OBSControlApp(app)

app.after(30, poll_serial_queue)
app.mainloop()

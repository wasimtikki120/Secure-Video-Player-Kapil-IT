import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from cryptography.fernet import Fernet, InvalidToken
import vlc
import tempfile
from tkinter import ttk
import os
import threading
import sys
from tkinter import simpledialog, messagebox, Entry, Toplevel, Label
import hashlib
import platform
import psutil
import base64


def resource_path(relative_path):
    """ Get the absolute path to the resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    result_path = os.path.join(base_path, relative_path)
    # print("Resource path:", result_path)  # Print the resolved path for debugging
    return result_path
# Function to generate a Fernet key
def generate_fernet_key(machine_identifier):
    # Use the machine-specific identifier to generate a Fernet key
    key = hashlib.sha256(machine_identifier.encode()).digest()
    return base64.urlsafe_b64encode(key)


# Function to load or generate a Fernet key
def load_or_generate_fernet_key():
    key_file = "fernet.key"
    if os.path.exists(key_file):
        with open(key_file, "rb") as file:
            fernet_key = file.read()
    else:
        fernet_key = generate_fernet_key()
        with open(key_file, "wb") as file:
            file.write(fernet_key)
    return fernet_key

class VideoPlayer:
    def __init__(self, master):
        self.master = master
        self.master.title("Kapil IT Video Player")
        self.master.geometry("1000x650")
        icon_path = resource_path("assets/logo.ico")
        if not os.path.exists(icon_path):
            messagebox.showerror("Error", f"Icon file not found at: {icon_path}")
            sys.exit(1)

        self.master.iconbitmap(icon_path)
        self.instance = None
        self.player = None
        self.current_media = None
        self.temp_file = None 

        self.setup_ui()
        self.update_status()

    def setup_ui(self):
        self.video_frame = ttk.Frame(self.master)
        self.video_frame.pack(fill=tk.BOTH, expand=True)

        self.video_canvas = tk.Canvas(self.video_frame, bg="#2c3e50")  # Dark blue background
        self.video_canvas.pack(fill=tk.BOTH, expand=True)

        self.controls_frame = ttk.Frame(self.master, style="Controls.TFrame")
        self.controls_frame.pack(fill=tk.X)

        self.btn_open = ttk.Button(self.controls_frame, text="Open", command=self.open_file, style="Open.TButton")
        self.btn_open.grid(row=0, column=0, padx=5, pady=5)

        self.btn_play = ttk.Button(self.controls_frame, text="▶ Play", command=self.play, style="Play.TButton")
        self.btn_play.grid(row=0, column=1, padx=5, pady=5)

        self.btn_pause = ttk.Button(self.controls_frame, text="⏸ Pause", command=self.pause, style="Pause.TButton")
        self.btn_pause.grid(row=0, column=2, padx=5, pady=5)

        self.btn_stop = ttk.Button(self.controls_frame, text="⏹ Stop", command=self.stop, style="Stop.TButton")
        self.btn_stop.grid(row=0, column=3, padx=5, pady=5)

        self.btn_forward = ttk.Button(self.controls_frame, text="⏩", command=self.forward, style="Forward.TButton")
        self.btn_forward.grid(row=0, column=6, padx=5, pady=5)

        # Enhanced backward button with a gradient background and arrow icon
        self.btn_backward = ttk.Button(self.controls_frame, text="⏪", command=self.backward, style="Backward.TButton")
        self.btn_backward.grid(row=0, column=7, padx=5, pady=5)

        self.status_bar = ttk.Label(self.controls_frame, text="00:00 / 00:00", style="Status.TLabel")
        self.status_bar.grid(row=0, column=4, padx=5, pady=5)

        self.progress_bar = ttk.Scale(self.controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=200, style="Progress.Horizontal.TScale")
        self.progress_bar.grid(row=0, column=5, padx=5, pady=5)
        self.progress_bar.bind("<ButtonRelease-1>", self.seek)

        self.master.bind("<F11>", self.toggle_fullscreen)
        self.master.bind("<Escape>", self.exit_fullscreen)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("Controls.TFrame", background="#ecf0f1")  # Light gray background
        self.style.configure("Status.TLabel", background="#ecf0f1", foreground="#34495e")  # Dark text on light background

        self.btn_support = ttk.Button(self.controls_frame, text="Support", command=self.show_support_info, style="Support.TButton")
        self.btn_support.grid(row=0, column=8, padx=5, pady=5)

# Add style configuration for the support button
        self.style.configure("Support.TButton", background="#1abc9c", relief=tk.FLAT, borderwidth=0)  # Green for Support button
        
        self.style.configure("TButton", background="#3498db", foreground="white", padding=5, font=('Helvetica', 10, 'bold'), borderwidth=0)  # Blue buttons with white text
        self.style.map("TButton", background=[('active', '#2980b9')])  # Darker blue on button press

        self.style.configure("Open.TButton", background="#2ecc71", relief=tk.FLAT, borderwidth=0)  # Green for Open button
        self.style.configure("Play.TButton", background="#e74c3c", relief=tk.FLAT, borderwidth=0)  # Red for Play button
        self.style.configure("Pause.TButton", background="#f39c12", relief=tk.FLAT, borderwidth=0)  # Orange for Pause button
        self.style.configure("Stop.TButton", background="#e67e22", relief=tk.FLAT, borderwidth=0)  # Dark orange for Stop button
        self.style.configure("Forward.TButton", background="#9b59b6", relief=tk.FLAT, borderwidth=0)  # Purple for Forward button
        self.style.configure("Backward.TButton", background="#9b59b6", relief=tk.FLAT, borderwidth=0)  # Dark gray for Backward button

        self.style.configure("Progress.Horizontal.TScale", background="#bdc3c7", troughcolor="#95a5a6", sliderlength=20)  # Gray progress bar with lighter slider

    def show_support_info(self):
        messagebox.showinfo("Support", "For support, please contact +91-7058924031")

    def open_file(self):
        file_path = filedialog.askopenfilename(title="Select Video File")
        if file_path:
            key, encrypted_data = self.extract_key_and_data(file_path)
            if key and encrypted_data:
                self.stop_and_release_player()
                self.delete_temp_file()
                self.decrypt_and_play(encrypted_data, key)

    def extract_key_and_data(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            key = data[data.rfind(b'\n') + 1:]
            encrypted_data = data[:data.rfind(b'\n')]
            return key, encrypted_data
        except Exception as e:
            messagebox.showerror("Error", f"Error extracting key and data from file: {str(e)}")
            return None, None

    def decrypt_and_play(self, encrypted_data, key):
        try:
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(encrypted_data)

            self.temp_file = tempfile.NamedTemporaryFile(delete=False)
            self.temp_file.write(decrypted_data)
            self.temp_file.close()

            self.instance = vlc.Instance('--no-xlib --quiet')
            self.player = self.instance.media_player_new()
            media = self.instance.media_new(self.temp_file.name)
            self.player.set_media(media)
            self.player.set_hwnd(self.get_handle())
            self.player.play()

            self.current_media = media
            self.player.event_manager().event_attach(vlc.EventType.MediaPlayerEndReached, self.on_media_end)
        except Exception as e:
            messagebox.showerror("Error", f"Error decrypting and playing video: {str(e)}")

    def on_media_end(self, event):
        messagebox.showinfo("Video Ended", "The video has ended. Click OK to restart the player.")
        threading.Thread(target=self.restart_player).start()

    def restart_player(self):
        self.stop_and_release_player()
        self.delete_temp_file()

    def stop_and_release_player(self):
        if self.player:
            self.player.stop()
        if self.instance:
            self.instance.release()

    def delete_temp_file(self):
        try:
            if self.temp_file and hasattr(self.temp_file, 'name') and os.path.exists(self.temp_file.name):
                os.unlink(self.temp_file.name)
        except Exception as e:
            messagebox.showerror("Error", f"Error deleting temporary file: {str(e)}")

    def play(self):
        if self.player and self.player.get_media() is None and self.current_media is not None:
            self.player.set_media(self.current_media)
        if self.player:
            self.player.play()

    def pause(self):
        if self.player:
            self.player.pause()

    def stop(self):
        if self.player:
            self.player.stop()

    def seek(self, event):
        if self.current_media is None:
            return
        if self.player:
            new_position = self.progress_bar.get()
            duration = self.player.get_length()
            if duration == 0:
                return
            self.player.set_position(new_position / 100)

    def update_status(self):
        if self.player and self.player.get_media() is not None:
            duration = self.player.get_length() / 1000
            position = self.player.get_time() / 1000
            self.progress_bar.set(position / duration * 100 if duration > 0 else 0)
            self.status_bar.config(text="%02d:%02d / %02d:%02d" % (position // 60, position % 60, duration // 60, duration % 60))
        self.master.after(200, self.update_status)

    def get_handle(self):
        return self.video_canvas.winfo_id()
    
    def toggle_fullscreen(self, event=None):
        if not self.master.attributes("-fullscreen"):
            self.master.attributes("-fullscreen", True)
            self.video_canvas.configure(width=self.master.winfo_screenwidth(), height=self.master.winfo_screenheight())
        else:
            self.master.attributes("-fullscreen", False)
            self.video_canvas.configure(width=640, height=360)

    def exit_fullscreen(self, event=None):
        if self.master.attributes("-fullscreen"):
            self.master.attributes("-fullscreen", False)
            self.video_canvas.configure(width=640, height=360)

    def forward(self):
        if self.player:
            current_time = self.player.get_time()
            self.player.set_time(current_time + 10000)  

    def backward(self):
        if self.player:
            current_time = self.player.get_time()
            self.player.set_time(max(0, current_time - 10000))  


def get_machine_identifier():
    try:
        mac_addresses = psutil.net_if_addrs().get('Ethernet', [])
        if mac_addresses:
            mac = ':'.join(['{:02x}'.format(int(byte)) for byte in mac_addresses[0][1]])
        else:
            mac = '000000000000'  # Fallback value if MAC address is not available
    except Exception as e:
        # print(f"Error retrieving MAC address: {e}")
        mac = '000000000000'  # Fallback value in case of an error

    cpu_id = hashlib.md5(platform.processor().encode()).hexdigest()
    # Concatenate mac and cpu_id and sanitize the identifier
    machine_identifier = mac + cpu_id
    # Replace invalid characters with underscore
    machine_identifier = machine_identifier.replace(':', '_')
    return machine_identifier


def main():
    root = tk.Tk()
    player = VideoPlayer(root)
    machine_identifier = get_machine_identifier()
    if not check_license(machine_identifier):
        messagebox.showinfo("License Required", "Please enter your license key to continue.")
        if not register_license(root):  # Remove machine_identifier argument here
            root.destroy()  # Close the application if registration fails
            return
    play_intro_video(player)
    root.mainloop()


def play_intro_video(player):
    intro_video_path = resource_path("assets/intro.mp4") # Update this path accordingly
    if os.path.exists(intro_video_path):
        player.stop()  # Stop any existing video
        key, encrypted_data = player.extract_key_and_data(intro_video_path)
        if key and encrypted_data:
            player.decrypt_and_play(encrypted_data, key)
    else:
        messagebox.showerror("Error", "Introductory video file not found.")



def check_license(machine_identifier):
    try:
        with open(f"license_{machine_identifier}.txt", "rb") as file:
            encrypted_license_key = file.read()
        decrypted_license_key = decrypt_key(encrypted_license_key, machine_identifier)
        return validate_license_key(decrypted_license_key)
    except FileNotFoundError:
        return False
# Validate the license key
def validate_license_key(license_key):
    valid_license_key = "K@pil#it#skill#hub"
    return license_key == valid_license_key
def save_license_key(license_key, machine_identifier):
    encrypted_license_key = encrypt_key(license_key.encode(), machine_identifier)
    with open(f"license_{machine_identifier}.txt", "wb") as file:
        file.write(encrypted_license_key)

def encrypt_key(license_key, machine_identifier):
    # Use the machine-specific identifier to generate Fernet key
    fernet_key = generate_fernet_key(machine_identifier)
    fernet = Fernet(fernet_key)
    return fernet.encrypt(license_key)

def decrypt_key(encrypted_license_key, machine_identifier):
    fernet_key = generate_fernet_key(machine_identifier)
    fernet = Fernet(fernet_key)
    try:
        return fernet.decrypt(encrypted_license_key).decode()
    except InvalidToken:
        messagebox.showerror("Invalid License", "The license key is invalid or corrupted.")
        return None

class CustomDialog(simpledialog.Dialog):
    def body(self, master):
        self.iconbitmap(resource_path("assets/logo.ico"))
        self.result = None
        self.label = Label(master, text="Please enter your license key:")
        self.label.pack()
        self.entry = Entry(master, show="*")
        self.entry.pack()
        return self.entry 

    def apply(self):
        self.result = self.entry.get()

def register_license(root):
    dialog = CustomDialog(root, title="Enter License Key")
    license_key = dialog.result
    machine_identifier = get_machine_identifier()
    if license_key:
        if validate_license_key(license_key):
            save_license_key(license_key, machine_identifier)
            messagebox.showinfo("Success", "License key validated. Thank you for registering!")
            return True
        else:
            messagebox.showerror("Invalid License", "The entered license key is invalid. Please try again.")
            return False
    else:
        messagebox.showerror("Invalid License", "You must enter a license key to continue.")
        return False


if __name__ == "__main__":
    main()
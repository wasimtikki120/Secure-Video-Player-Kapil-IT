from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.video import Video
from kivy.core.window import Window
from kivy.uix.popup import Popup
from cryptography.fernet import Fernet, InvalidToken
import vlc
import tempfile
import os
import threading
import sys
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


class VideoPlayerApp(App):
    def __init__(self):
        super(VideoPlayerApp, self).__init__()
        self.instance = None
        self.player = None
        self.current_media = None
        self.temp_file = None

    def build(self):
        self.machine_identifier = self.get_machine_identifier()

        layout = BoxLayout(orientation='vertical')

        self.video = Video(source='', state='stop', options={'allow_stretch': True})
        layout.add_widget(self.video)

        controls_layout = BoxLayout(orientation='horizontal')
        layout.add_widget(controls_layout)

        self.btn_open = Button(text='Open')
        self.btn_open.bind(on_press=self.open_file)
        controls_layout.add_widget(self.btn_open)

        self.btn_play = Button(text='▶ Play')
        self.btn_play.bind(on_press=self.play)
        controls_layout.add_widget(self.btn_play)

        self.btn_pause = Button(text='⏸ Pause')
        self.btn_pause.bind(on_press=self.pause)
        controls_layout.add_widget(self.btn_pause)

        self.progress_bar = Slider(min=0, max=100, value=0)
        self.progress_bar.bind(on_touch_up=self.seek)
        controls_layout.add_widget(self.progress_bar)

        return layout

    def open_file(self, instance):
        file_path = self.select_file()
        if file_path:
            key, encrypted_data = self.extract_key_and_data(file_path)
            if key and encrypted_data:
                self.play_encrypted_video(encrypted_data, key)

    def select_file(self):
        return "example_video.mp4"  # Dummy file path, replace this with your file selection logic

    def extract_key_and_data(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            key = data[data.rfind(b'\n') + 1:]
            encrypted_data = data[:data.rfind(b'\n')]
            return key, encrypted_data
        except Exception as e:
            self.show_error_message(f"Error extracting key and data from file: {str(e)}")
            return None, None

    def play_encrypted_video(self, encrypted_data, key):
        try:
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(encrypted_data)

            self.temp_file = tempfile.NamedTemporaryFile(delete=False)
            self.temp_file.write(decrypted_data)
            self.temp_file.close()

            self.player = vlc.MediaPlayer(self.temp_file.name)
            self.player.play()
        except Exception as e:
            self.show_error_message(f"Error decrypting and playing video: {str(e)}")

    def play(self, instance):
        if self.player:
            self.player.play()

    def pause(self, instance):
        if self.player:
            self.player.pause()

    def seek(self, instance, value):
        if self.player:
            new_position = value / 100.0
            self.player.set_position(new_position)

    def show_error_message(self, message):
        # Your error message display logic here
        pass

    def get_machine_identifier(self):
        try:
            mac_addresses = psutil.net_if_addrs().get('Ethernet', [])
            if mac_addresses:
                mac = ':'.join(['{:02x}'.format(int(byte)) for byte in mac_addresses[0][1]])
            else:
                mac = '000000000000'  # Fallback value if MAC address is not available
        except Exception as e:
            mac = '000000000000'  # Fallback value in case of an error

        cpu_id = hashlib.md5(platform.processor().encode()).hexdigest()
        machine_identifier = mac + cpu_id
        machine_identifier = machine_identifier.replace(':', '_')
        return machine_identifier


if __name__ == "__main__":
    VideoPlayerApp().run()

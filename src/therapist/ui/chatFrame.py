import threading
import wave
import pyaudio
from PIL import Image, ImageTk
import customtkinter as ctk



class ChatFrame(ctk.CTkScrollableFrame):
    """
    Scrollable frame to display messages (text, images, audio).
    """

    def __init__(self, master):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)

    def _add_image_to_message(self, frame, image_path, row):
        """
        Loads and displays an image within a given frame at a specific row.
        """
        try:
            image = Image.open(image_path)
            image.thumbnail((300, 300))
            photo = ImageTk.PhotoImage(image)
            img_label = ctk.CTkLabel(frame, image=photo, text="")
            img_label.image = photo  # Keep reference
            img_label.grid(row=row, column=0, padx=10, pady=5)
        except Exception as e:
            print(f"Error loading image: {e}")

    def _add_audio_to_message(self, frame, audio_path, row):
        """
        Creates a small audio player widget (icon + 'Play' button).
        """
        audio_frame = ctk.CTkFrame(frame, fg_color="transparent")
        audio_frame.grid(row=row, column=0, padx=10, pady=5, sticky="w")

        audio_icon = ctk.CTkLabel(audio_frame, text="🎵", width=30, fg_color="white", corner_radius=8)
        audio_icon.grid(row=0, column=0, padx=(0, 5))

        play_button = ctk.CTkButton(
            audio_frame,
            text="Play",
            width=50,
            command=lambda: self._play_audio(audio_path)
        )
        play_button.grid(row=0, column=1)

    def _play_audio(self, audio_path):
        """
        Spawns a thread to play the audio file to avoid blocking the UI.
        """
        threading.Thread(
            target=self._play_audio_in_thread,
            args=(audio_path,),
            daemon=True
        ).start()

    def _play_audio_in_thread(self, audio_path):
        """
        Actual audio playback logic. Runs in a background thread.
        """
        try:
            wf = wave.open(audio_path, 'rb')
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pa.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True
            )

            chunk = 1024
            data = wf.readframes(chunk)
            while data:
                stream.write(data)
                data = wf.readframes(chunk)

            stream.stop_stream()
            stream.close()
            pa.terminate()

        except Exception as e:
            print(f"Error playing audio: {e}")
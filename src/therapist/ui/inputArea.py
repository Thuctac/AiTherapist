import os
import time
import threading
import warnings
import wave
import pyaudio
from PIL import Image, ImageTk
from tkinter import filedialog
import customtkinter as ctk


class InputArea(ctk.CTkFrame):
    """
    Frame at the bottom for user inputs:
      - Text input (with placeholder)
      - Image attachment
      - Audio recording (start/stop)
      - Send button
    """

    def __init__(self, master):
        super().__init__(master, fg_color="#333333")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(3, minsize=10)

        # Text input
        self.text_input = ctk.CTkTextbox(
            self,
            height=50,
            fg_color="#333333",
            text_color="#FFFFFF",
            border_width=0
        )
        self.text_input.grid(row=0, column=1, padx=5, sticky="ew")
        self.text_input.insert("1.0", "Type your message here...")
        self.text_input.bind("<FocusIn>", self._clear_placeholder)
        self.text_input.bind("<FocusOut>", self._restore_placeholder)

        # Attachment button (image)
        self.attach_btn = self._create_button("📎", "#333333", self.attach_file, 0, 0)

        # Send button
        self.send_btn = self._create_button("→", "#3D5AFE", master.send_message, 1, 2)

        # Audio recording button
        self.is_recording = False
        self.audio_thread = None
        self.stop_recording_flag = threading.Event()
        self.record_btn = self._create_button("🎤", "#333333", self.toggle_recording, 1, 0)

        # Previews for attachments
        self.current_image = None
        self.preview_frame = None
        self.audio_filename = None
        self.current_audio = None
        self.audio_preview_frame = None

    def _create_button(self, text, color, command, row, column):
        """
        Helper function to create a CTkButton with consistent styling.
        """
        btn = ctk.CTkButton(
            self,
            text=text,
            width=40,
            fg_color=color,
            hover_color="#444444" if color == "#333333" else "#303F9F",
            command=command
        )
        btn.grid(row=row, column=column, padx=1)
        return btn

    ########################
    # PLACEHOLDER HANDLERS #
    ########################
    def _clear_placeholder(self, event):
        current_text = self.text_input.get("1.0", "end-1c")
        if current_text.strip() == "Type your message here...":
            self.text_input.delete("1.0", "end")
            self.text_input.configure(text_color="#FFFFFF")

    def _restore_placeholder(self, event):
        current_text = self.text_input.get("1.0", "end-1c")
        if not current_text.strip():
            self.text_input.insert("1.0", "Type your message here...")
            self.text_input.configure(text_color="#888888")

    ################
    # IMAGE LOGICS #
    ################
    def attach_file(self):
        """
        Opens a file dialog for image selection, then shows a preview frame.
        """
        if self.current_image or self.master.waiting_response or self.is_recording:
            return

        self.lift()
        file_path = filedialog.askopenfilename(
            parent=self,
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            self.attach_btn.configure(state="disabled")
            self._show_image_preview(file_path)

    def _show_image_preview(self, file_path):
        """
        Shows a small image preview + remove button in the input area.
        """
        if self.preview_frame:
            self.preview_frame.destroy()
        self.preview_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.preview_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        remove_btn = ctk.CTkButton(
            self.preview_frame,
            text="✕",
            fg_color="red",
            text_color="white",
            width=25,
            height=25,
            corner_radius=5,
            command=self._remove_image_preview
        )
        remove_btn.grid(row=0, column=0, padx=5, pady=5)

        # Create a thumbnail image preview
        try:
            image = Image.open(file_path)
            image.thumbnail((40, 40))
            photo = ImageTk.PhotoImage(image)
            preview_label = ctk.CTkLabel(self.preview_frame, image=photo, text="")
            preview_label.image = photo
            preview_label.grid(row=0, column=1, padx=5, pady=5)
        except Exception as e:
            print(f"Error displaying image preview: {e}")

        self.current_image = file_path

    def _remove_image_preview(self):

        self._remove_image()
        self.attach_btn.configure(state="normal")

    def _remove_image(self):
        """
        Removes the image preview frame and clears the cached image path.
        """
        if self.preview_frame:
            self.preview_frame.destroy()
            self.preview_frame = None
        self.current_image = None

    ################
    # AUDIO LOGICS #
    ################
    def toggle_recording(self):
        """
        Starts or stops audio recording based on the current state.
        """
        if self.is_recording:
            # Stop
            self.stop_recording_flag.set()
            self.record_btn.configure(state="disabled")
        else:
            # Start
            self.stop_recording_flag.clear()
            self.audio_thread = threading.Thread(target=self._record_audio, daemon=True)
            self.audio_thread.start()

        self.is_recording = not self.is_recording
        self._update_recording_button()

    def _update_recording_button(self):
        """
        Update the label/color of the recording button based on is_recording state.
        """
        if self.is_recording:
            self.record_btn.configure(text="⏺", fg_color="red", text_color="white")
        else:
            self.record_btn.configure(text="🎤", fg_color="#333333", text_color="white")

    def _record_audio(self):
        """
        Records audio from the microphone until stop_recording_flag is set,
        then saves the audio to a .wav file.
        """
        chunk = 1024
        sample_format = pyaudio.paInt16
        channels = 1
        fs = 44100

        p = pyaudio.PyAudio()
        stream = p.open(format=sample_format, channels=channels, rate=fs,
                        frames_per_buffer=chunk, input=True)

        frames = []
        print("Recording started...")

        while not self.stop_recording_flag.is_set():
            data = stream.read(chunk)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        timestamp = int(time.time())
        folder_name = "recording"
        self.audio_filename = os.path.join(folder_name, f"recording_{timestamp}.wav")

        wf = wave.open(self.audio_filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(sample_format))
        wf.setframerate(fs)
        wf.writeframes(b''.join(frames))
        wf.close()

        print(f"Recording saved as {self.audio_filename}")
        self._show_audio_preview(self.audio_filename)

    def _show_audio_preview(self, audio_path):
        """
        Displays a small "audio preview" row with a remove button + icon.
        """
        if self.audio_preview_frame:
            self.audio_preview_frame.destroy()
        self.audio_preview_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.audio_preview_frame.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        remove_audio_btn = ctk.CTkButton(
            self.audio_preview_frame,
            text="✕",
            fg_color="red",
            text_color="white",
            width=25,
            height=25,
            corner_radius=5,
            command=self._remove_audio_preview
        )
        remove_audio_btn.grid(row=0, column=0, padx=5, pady=5)

        audio_label = ctk.CTkLabel(self.audio_preview_frame, text="🎵", width=40, fg_color="white", corner_radius=8)
        audio_label.grid(row=0, column=1, padx=(0, 5))

        self.current_audio = audio_path

    def _remove_audio_preview(self):

        self._remove_audio()
        os.remove(self.audio_filename)
        self.record_btn.configure(state="normal")


    def _remove_audio(self):
        """
        Removes the audio preview frame and clears the cached audio path.
        """
        if self.audio_preview_frame:
            self.audio_preview_frame.destroy()
            self.audio_preview_frame = None
        self.current_audio = None

    #############################
    # DISABLING / ENABLING I/O #
    #############################
    def disable_buttons(self):
        self.text_input.configure(state="disabled")
        self.attach_btn.configure(state="disabled")
        self.send_btn.configure(state="disabled")
        self.record_btn.configure(state="disabled")

    def enable_buttons(self):
        self.text_input.configure(state="normal")
        self.attach_btn.configure(state="normal")
        self.send_btn.configure(state="normal")
        self.record_btn.configure(state="normal")

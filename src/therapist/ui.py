import os
import time
import threading
import warnings
import wave
import pyaudio
from PIL import Image, ImageTk
from tkinter import filedialog
import customtkinter as ctk
from random import choice

# Replace with your actual AI logic module
from therapy import TherapySession

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


class ChatHeader(ctk.CTkLabel):
    """
    A simple header label for the chat window.
    """
    def __init__(self, master):
        super().__init__(master, text="AI Therapist", font=("Arial", 24))


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
            command=self._remove_image
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
        audio_filename = os.path.join(folder_name, f"recording_{timestamp}.wav")

        wf = wave.open(audio_filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(sample_format))
        wf.setframerate(fs)
        wf.writeframes(b''.join(frames))
        wf.close()

        print(f"Recording saved as {audio_filename}")
        self._show_audio_preview(audio_filename)

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
            command=self._remove_audio
        )
        remove_audio_btn.grid(row=0, column=0, padx=5, pady=5)

        audio_label = ctk.CTkLabel(self.audio_preview_frame, text="🎵", width=40, fg_color="white", corner_radius=8)
        audio_label.grid(row=0, column=1, padx=(0, 5))

        self.current_audio = audio_path

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


class ChatWindow(ctk.CTk):
    """
    Main application window that manages:
      - UI setup (header, chat frame, input area).
      - Conversation log tracking and saving.
      - Recording folder + log folder cleanup on startup.
      - Toggling input while AI (Therapist) is processing.
      - Threaded calls to the therapy logic (TherapySession).
    """

    def __init__(self, fg_color=None, **kwargs):
        super().__init__(fg_color, **kwargs)

        # 1) Setup "recording" folder (already present in your code).
        self._setup_recording_folder()

        # 2) Setup "log" folder — new functionality
        self._setup_log_folder()

        # Therapist name for your welcome messages
        self.therapist_name = "Kevin"

        # Initialize therapy backend
        self.therapy = TherapySession(self.therapist_name)

        # Example welcome messages
        self.welcome_messages = [
            f"Hi, I’m {self.therapist_name}. Before we begin, tell me a little about yourself — what’s on your mind today?",
            f"Hello! I’m {self.therapist_name}. What’s your name? Let’s start by getting to know each other.",
            f"Hi, I’m {self.therapist_name}. How are you feeling today? I’d love to know a bit about you.",
            f"Hey, I’m {self.therapist_name}. What brings you here today?",
            f"Hi! I’m {self.therapist_name}. Tell me a bit about yourself — what’s been on your mind lately?",
            f"Hello, I’m {self.therapist_name}. I’d like to know more about you. What’s something you’d like to share?",
            f"Hi, I’m {self.therapist_name}. I’d love to get to know you better — what’s one thing you’d like to share about yourself?",
            f"Hello! I’m {self.therapist_name}. Let’s start with you — how has your day been so far?",
            f"Hi, I’m {self.therapist_name}. I’m here to listen. Can you tell me a little about what’s been going on?",
            f"Hi, I’m {self.therapist_name}. What’s one thing you’d like me to know about you as we begin?",
            f"Hello! I’m {self.therapist_name}. If you could describe your current state of mind in one word, what would it be?",
            f"Hi, I’m {self.therapist_name}. What’s something you’d like to focus on in our conversations?",
            f"Hey there, I’m {self.therapist_name}. I’d love to know more about you — what’s been on your mind?",
            f"Hi, I’m {self.therapist_name}. Let’s start with you. How would you describe what you’re feeling right now?",
            f"Hello! I’m {self.therapist_name}. What’s the first thing you’d like me to know about you?"
        ]

        self.title("AI Therapist")
        self.geometry("600x800")
        self.center_window()
        ctk.set_appearance_mode("dark")

        self.conversation_log = []
        self.waiting_response = False

        self._setup_grid()
        self._create_widgets()
        self._setup_bindings()

        initial_welcome = choice(self.welcome_messages)
        self._add_message(initial_welcome, "Therapist")

        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Keep window on top (optional)
        self.attributes('-topmost', True)

    def center_window(self):
        """
        Centers the main application window on the screen.
        """
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        window_width = 600
        window_height = 800

        position_top = int(screen_height / 2 - window_height / 2)
        position_right = int(screen_width / 2 - window_width / 2)
        self.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')

    def _setup_recording_folder(self):
        """
        Ensures 'recording/' folder exists, then empties it at startup.
        """
        folder_name = "recording"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        else:
            for f in os.listdir(folder_name):
                path = os.path.join(folder_name, f)
                if os.path.isfile(path):
                    os.remove(path)

    def _setup_log_folder(self):
        """
        Ensures 'log/' folder exists, then empties it at startup.
        (In a production environment, you may not want to delete old logs.)
        """
        log_folder = "log"
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)
        else:
            for f in os.listdir(log_folder):
                path = os.path.join(log_folder, f)
                if os.path.isfile(path):
                    os.remove(path)

    def _setup_grid(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

    def _create_widgets(self):
        # Header
        self.header = ChatHeader(self)
        self.header.grid(row=0, column=0, pady=15, sticky="ew")

        # Chat frame
        self.chat_frame = ChatFrame(self)
        self.chat_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")

        # Input area
        self.input_area = InputArea(self)
        self.input_area.grid(row=2, column=0, sticky="ew")

    def _setup_bindings(self):
        """
        Binds Enter key (without shift) to send, Shift+Enter to insert a newline.
        """
        self.input_area.text_input.bind("<Return>", self._handle_return)
        self.input_area.text_input.bind("<Shift-Return>", lambda e: "break")

    def _handle_return(self, event):
        """
        If user presses Enter without shift, send the message; with shift, insert a newline.
        """
        # Check if SHIFT is not pressed
        if not event.state & 0x1:
            self.send_message()
            return "break"
        return None

    def send_message(self):
        """
        Send the user's text, image, or audio to the chat and trigger the AI response.
        """
        if self.waiting_response:
            return

        # Gather text from input
        message = self.input_area.text_input.get("1.0", "end-1c").strip()
        if message == "Type your message here...":
            message = ""

        image_path = self.input_area.current_image
        audio_path = self.input_area.current_audio

        # If no input (text, image, or audio), do nothing
        if not (message or image_path or audio_path):
            return

        # Display user's content in the chat + log
        self._add_message(message, "user", image_path=image_path, audio_path=audio_path)

        # Clear the input area
        self.input_area.text_input.delete("1.0", "end")
        self.input_area._remove_image()
        self.input_area._remove_audio()

        # Disable further input while waiting for AI response
        self._disable_input()

        # Show placeholder for the Therapist's response
        self.loading_message_frame = self._add_message("Loading...", "Therapist")

        # Process the AI response in a background thread
        threading.Thread(
            target=self._process_response,
            args=(message, image_path, audio_path),
            daemon=True
        ).start()

    def _process_response(self, message, image_path, audio_path):
        """
        Calls the therapy logic (TherapySession) in a separate thread, then updates the UI with the response.
        """
        try:
            # Convert the conversation log to a string (if your therapy logic needs context)
            conversation_str = self.conversation_log_to_string()

            # Real logic (placeholder example):
            response = self.therapy.run(message, image_path, audio_path, conversation_str)
            # For demonstration, simulate a response:
            # response = f"[Therapist response simulation]: You said '{message}'"
        except Exception as e:
            response = f"Error: {str(e)}"

        # Update the "Loading..." message with the actual response
        self._update_message(self.loading_message_frame, response)

        # Re-enable input area
        self._enable_input()

    def _disable_input(self):
        self.waiting_response = True
        self.input_area.disable_buttons()

    def _enable_input(self):
        self.waiting_response = False
        self.input_area.enable_buttons()

    def _add_message(self, message, sender, image_path=None, audio_path=None):
        """
        Adds a new message (text, image, audio) to the chat frame and logs it.
        Returns the message frame (useful if we need to update it later).
        """
        # Different background color for user vs. therapist
        bg_color = "#4B4B4B" if sender == "user" else "#3D5AFE"

        message_frame = ctk.CTkFrame(self.chat_frame, fg_color=bg_color)
        message_frame.grid(sticky="e" if sender == "user" else "w", pady=5)
        message_frame.grid_columnconfigure(0, weight=1)

        current_row = 0

        # If there's an image, display it
        if image_path:
            self.chat_frame._add_image_to_message(message_frame, image_path, current_row)
            current_row += 1

        # If there's audio, display the audio player widget
        if audio_path:
            self.chat_frame._add_audio_to_message(message_frame, audio_path, current_row)
            current_row += 1

        # If there's text, display a label
        if message.strip():
            label = ctk.CTkLabel(message_frame, text=message, wraplength=350)
            label.grid(row=current_row, column=0, padx=10, pady=5)
            current_row += 1

        # Build log text (message + optional references to image/audio)
        log_text = message
        if image_path:
            log_text += f"\n[image path: {image_path}]"
        if audio_path:
            log_text += f"\n[audio path: {audio_path}]"

        # Append to conversation_log
        self.conversation_log.append((sender, log_text))

        # Auto-scroll to bottom
        self.after(10, self._scroll_to_bottom)
        return message_frame

    def _update_message(self, message_frame, new_message):
        """
        Given the frame containing a message, update the text label to `new_message`.
        Also updates the conversation_log accordingly.
        """
        for widget in message_frame.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(text=new_message)

                if self.conversation_log:
                    # Update last log entry
                    last_sender, _ = self.conversation_log[-1]
                    self.conversation_log[-1] = (last_sender, new_message)
                break

    def _scroll_to_bottom(self):
        """
        Scrolls the chat frame to the bottom (so the user sees the newest message).
        """
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    def _on_close(self):
        """
        Handles actions when the window is closed, like saving the conversation log.
        """
        try:
            self._save_conversation_log()
        except Exception as e:
            print(f"Error saving log: {e}")
        finally:
            self.destroy()

    def _save_conversation_log(self):
        """
        Save the entire conversation log to a timestamped text file in the 'log' folder.
        """
        timestamp = int(time.time())
        log_filename = os.path.join("log", f"conversation_log_{timestamp}.txt")
        with open(log_filename, "w", encoding="utf-8") as f:
            for sender, msg in self.conversation_log:
                f.write(f"[{sender}] {msg}\n\n")
        print(f"Conversation log saved to {log_filename}")

    def conversation_log_to_string(self):
        """
        Returns the conversation as a single string, e.g., for passing to the AI model.
        """
        lines = []
        for sender, msg in self.conversation_log:
            lines.append(f"[{sender}] {msg}")
        return "\n".join(lines)


if __name__ == "__main__":
    app = ChatWindow()
    app.mainloop()

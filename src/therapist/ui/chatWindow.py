import os
import time
import threading
import customtkinter as ctk
from random import choice
from .chatFrame import ChatFrame
from .chatHeader import ChatHeader
from .inputArea import InputArea

class ChatWindow(ctk.CTk):
    """
    Main application window that manages:
      - UI setup (header, chat frame, input area).
      - Conversation log tracking and saving.
      - Recording folder + log folder cleanup on startup.
      - Toggling input while AI (Therapist) is processing.
      - Threaded calls to the therapy logic (TherapySession).
    """

    def __init__(self, therapy, **kwargs):
        super().__init__(**kwargs)

        # 1) Setup "recording" folder (already present in your code).
        self._setup_recording_folder()

        # 2) Setup "log" folder — new functionality
        self._setup_log_folder()

        # Therapist name for your welcome messages
        self.therapist_name = "Kevin"

        # Initialize therapy backend
        self.therapy = therapy

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
        Ensures 'recording/' folder exists
        """
        folder_name = "recording"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)

    def _setup_log_folder(self):
        """
        Ensures 'log/' folder exists, then empties it at startup.
        """
        log_folder = "log"
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

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

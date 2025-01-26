import os
import time
import threading
from random import choice
import customtkinter as ctk
from tkinter import Toplevel, Listbox, Button, END, StringVar
from .chatFrame import ChatFrame
from .chatHeader import ChatHeader
from .inputArea import InputArea


class ChatWindow(ctk.CTk):
    """
    Main window:
      - Hidden until user picks load or new
      - If load -> only show after picking which conversation to load
      - If new -> prompt for unique name, then show window
      - Window is centered
      - Logs named after the conversation name
      - Parsing old logs to display images and audio
    """

    def __init__(self, therapy, **kwargs):
        super().__init__(**kwargs)

        self.withdraw()

        self.therapy = therapy
        self.title("AI Therapist")

        ctk.set_appearance_mode("dark")

        # Folders
        self._setup_log_folder()

        self.therapist_name = "Kevin"
        self.conversation_log = []
        self.waiting_response = False
        self.conversation_name = None

        self.welcome_messages = [
            f"Hi, I’m {self.therapist_name}. Before we begin, tell me a little about yourself — what’s on your mind today?",
            f"Hello! I’m {self.therapist_name}. What’s your name? Let’s start by getting to know each other.",
        ]

        # Build the main UI
        self._setup_grid()
        self._create_widgets()
        self._setup_bindings()

        # Prompt user: load or new?
        self._ask_load_or_new()

        # Window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    ##########################
    # Folder / Utility Setup #
    ##########################

    def _setup_log_folder(self):
        log_folder = "log"
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

    def _center_window(self, w=600, h=800):
        """
        Center the main ChatWindow at size w x h.
        Call this after we deiconify to ensure the window is actually created.
        """
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w // 2) - (w // 2)
        y = (screen_h // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _center_toplevel(self, win, w, h):
        """
        Center a Toplevel window at size w x h on the screen.
        """
        win.update_idletasks()
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        x = (screen_w // 2) - (w // 2)
        y = (screen_h // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")

    #############
    # GUI Setup #
    #############

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
        self.input_area.text_input.bind("<Return>", self._handle_return)
        self.input_area.text_input.bind("<Shift-Return>", lambda e: "break")

    def _handle_return(self, event):
        if not event.state & 0x1:  # SHIFT not pressed
            self.send_message()
            return "break"
        return None

    ######################
    # Send/Receive Logic #
    ######################

    def send_message(self):
        if self.waiting_response:
            return

        message = self.input_area.text_input.get("1.0", "end-1c").strip()
        if message == "Type your message here...":
            message = ""

        image_path = self.input_area.current_image
        audio_path = self.input_area.current_audio

        if not (message or image_path or audio_path):
            return

        self._add_message(message, "user", image_path=image_path, audio_path=audio_path)
        self.input_area.text_input.delete("1.0", "end")
        self.input_area._remove_image()
        self.input_area._remove_audio()

        self._disable_input()
        loading_frame = self._add_message("Loading...", "Therapist")

        threading.Thread(
            target=self._process_response,
            args=(message, image_path, audio_path, loading_frame),
            daemon=True
        ).start()

    def _process_response(self, message, image_path, audio_path, loading_frame):
        try:
            conversation_str = self.conversation_log_to_string()
            response = self.therapy.run(message, image_path, audio_path, conversation_str)
        except Exception as e:
            response = f"Error: {str(e)}"

        self._update_message(loading_frame, response)
        self._enable_input()

    def _disable_input(self):
        self.waiting_response = True
        self.input_area.disable_buttons()

    def _enable_input(self):
        self.waiting_response = False
        self.input_area.enable_buttons()

    def _add_message(self, message, sender, image_path=None, audio_path=None):
        bg_color = "#4B4B4B" if sender == "user" else "#3D5AFE"
        msg_frame = ctk.CTkFrame(self.chat_frame, fg_color=bg_color)
        msg_frame.grid(sticky="e" if sender == "user" else "w", pady=5)
        msg_frame.grid_columnconfigure(0, weight=1)

        row_idx = 0

        if image_path:
            self.chat_frame._add_image_to_message(msg_frame, image_path, row_idx)
            row_idx += 1

        if audio_path:
            self.chat_frame._add_audio_to_message(msg_frame, audio_path, row_idx)
            row_idx += 1

        if message.strip():
            lbl = ctk.CTkLabel(msg_frame, text=message, wraplength=350)
            lbl.grid(row=row_idx, column=0, padx=10, pady=5)
            row_idx += 1

        # Build log text
        log_text = message
        if image_path:
            log_text += f"\n[image path: {image_path}]"
        if audio_path:
            log_text += f"\n[audio path: {audio_path}]"

        self.conversation_log.append((sender, log_text))
        self.after(10, self._scroll_to_bottom)
        return msg_frame

    def _update_message(self, msg_frame, new_text):
        for widget in msg_frame.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(text=new_text)
                if self.conversation_log:
                    last_sender, _ = self.conversation_log[-1]
                    self.conversation_log[-1] = (last_sender, new_text)
                break

    def _scroll_to_bottom(self):
        self.chat_frame._parent_canvas.yview_moveto(1.0)

    def conversation_log_to_string(self):
        lines = []
        for sender, msg in self.conversation_log:
            lines.append(f"[{sender}] {msg}")
        return "\n".join(lines)

    ################
    # Save / Close #
    ################

    def _on_close(self):
        try:
            self._save_conversation_log()
        except Exception as e:
            print(f"Error saving log: {e}")
        finally:
            self.destroy()

    def _save_conversation_log(self):
        """
        Named after self.conversation_name if new
        or after whichever old conversation we loaded.
        """
        log_folder = "log"
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

        if self.conversation_name:
            log_filename = os.path.join(log_folder, f"{self.conversation_name}.txt")
        else:
            timestamp = int(time.time())
            log_filename = os.path.join(log_folder, f"conversation_log_{timestamp}.txt")

        with open(log_filename, "w", encoding="utf-8") as f:
            for sender, msg in self.conversation_log:
                f.write(f"[{sender}] {msg}\n\n")

        print(f"Conversation log saved to {log_filename}")

    ############################
    # Loading Old Conversation #
    ############################

    def _load_previous_conversation(self, log_path):
        """
        Parse the .txt file for text, [image path: ...], [audio path: ...].
        We do not show the main window until AFTER the user picks a file.
        """
        self.chat_frame.destroy()
        self.chat_frame = ChatFrame(self)
        self.chat_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")
        self.conversation_log.clear()

        base = os.path.basename(log_path)
        just_name, _ext = os.path.splitext(base)
        self.conversation_name = just_name

        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            temp_sender = None
            temp_lines = []

            def flush_message():
                if not temp_sender or not temp_lines:
                    return

                image_path = None
                audio_path = None
                text_parts = []

                for l in temp_lines:
                    stripped = l.strip()
                    if stripped.startswith("[image path:"):
                        path = stripped.replace("[image path:", "").replace("]", "").strip()
                        image_path = path
                    elif stripped.startswith("[audio path:"):
                        path = stripped.replace("[audio path:", "").replace("]", "").strip()
                        audio_path = path
                    else:
                        text_parts.append(stripped)

                msg_text = "\n".join(text_parts).strip()
                self._add_message(msg_text, temp_sender, image_path, audio_path)

            for line in lines:
                line = line.rstrip("\n")
                if (
                    line.startswith("[")
                    and "]" in line
                    and not line.startswith("[image path:")
                    and not line.startswith("[audio path:")
                ):
                    # new sender line
                    flush_message()
                    temp_lines.clear()
                    try:
                        sender_part = line.split("]", 1)[0].replace("[", "")
                        leftover_msg = line.split("]", 1)[1].strip()
                        temp_sender = sender_part
                        if leftover_msg:
                            temp_lines.append(leftover_msg)
                    except:
                        pass
                else:
                    temp_lines.append(line)

            flush_message()
            print(f"Loaded conversation from {log_path}")

        except Exception as e:
            print(f"Error loading conversation: {e}")
            return

        self.deiconify()
        self._center_window()

    ##################################
    # Modal Flow: Choose Load or New #
    ##################################

    def _ask_load_or_new(self):
        """
        Shows a small dialog (centered).
        If user picks Load => show load window
        If user picks New => ask for conversation name => show main
        """
        ask_window = ctk.CTkToplevel()
        ask_window.title("Choose Conversation")
        self._center_toplevel(ask_window, 300, 150)

        lbl = ctk.CTkLabel(ask_window, text="Load previous or start new?")
        lbl.pack(pady=10)

        load_btn = ctk.CTkButton(
            ask_window, text="Load Previous",
            command=lambda: [ask_window.destroy(), self._show_load_window()]
        )
        load_btn.pack(pady=5)

        new_btn = ctk.CTkButton(
            ask_window, text="New Conversation",
            command=lambda: [ask_window.destroy(), self._ask_for_conversation_name()]
        )
        new_btn.pack(pady=5)

        ask_window.grab_set()
        ask_window.lift()

    def _show_load_window(self):
        """
        Lists all .txt in 'log', user picks => then we load it => show main window after load.
        """
        load_win = ctk.CTkToplevel()
        load_win.title("Load Conversation")
        self._center_toplevel(load_win, 400, 300)

        listbox = Listbox(load_win)
        listbox.pack(fill="both", expand=True, padx=10, pady=10)

        log_folder = "log"
        files = []
        if os.path.exists(log_folder):
            files = [f for f in os.listdir(log_folder) if f.endswith(".txt")]
            files.sort()

        for f in files:
            listbox.insert(END, f)

        def on_load():
            selection = listbox.curselection()
            if selection:
                filename = listbox.get(selection[0])
                log_path = os.path.join(log_folder, filename)
                load_win.destroy()
                self._load_previous_conversation(log_path)
            else:
                load_win.destroy()
                self._ask_for_conversation_name()

        load_button = Button(load_win, text="Load Selected", command=on_load)
        load_button.pack(pady=5)

        cancel_button = Button(
            load_win, text="Cancel",
            command=lambda: [load_win.destroy(), self._ask_for_conversation_name()]
        )
        cancel_button.pack(pady=5)

        load_win.grab_set()
        load_win.lift()

    ##############################
    # New Conversation Name Flow #
    ##############################

    def _ask_for_conversation_name(self):
        """
        Ask user to pick a unique conversation name.
        After that, we start new convo => show main window => center it
        """
        name_win = ctk.CTkToplevel()
        name_win.title("Name Your Conversation")
        self._center_toplevel(name_win, 300, 150)

        lbl = ctk.CTkLabel(name_win, text="Enter a unique conversation name:")
        lbl.pack(pady=10)

        name_var = StringVar()
        entry = ctk.CTkEntry(name_win, textvariable=name_var)
        entry.pack(pady=5)

        error_lbl = ctk.CTkLabel(name_win, text="", text_color="red")
        error_lbl.pack()

        def on_confirm():
            proposed_name = name_var.get().strip()
            if not proposed_name:
                error_lbl.configure(text="Please enter a name.")
                return

            # check if already exists
            log_path = os.path.join("log", f"{proposed_name}.txt")
            if os.path.exists(log_path):
                error_lbl.configure(text="Name already exists. Choose another.")
                return

            self.conversation_name = proposed_name
            name_win.destroy()

            self._start_new_convo()

            self.deiconify()
            self._center_window()

        confirm_btn = ctk.CTkButton(name_win, text="OK", command=on_confirm)
        confirm_btn.pack(pady=5)

        cancel_btn = ctk.CTkButton(
            name_win, text="Cancel",
            command=lambda: [
                name_win.destroy(),
                self._start_new_convo(),
                self.deiconify(),
                self._center_window()
            ]
        )
        cancel_btn.pack(pady=5)

        name_win.grab_set()
        name_win.lift()

    def _start_new_convo(self):
        """
        Show a welcome message for a fresh conversation.
        """
        self.chat_frame.destroy()
        self.chat_frame = ChatFrame(self)
        self.chat_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")
        self.conversation_log.clear()

        initial_welcome = choice(self.welcome_messages)
        self._add_message(initial_welcome, "Therapist")

import customtkinter as ctk
from PIL import Image, ImageTk
from tkinter import filedialog
import warnings
import asyncio
import threading
from therapy import TherapySession

# Suppress warnings
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

class ChatWindow(ctk.CTk):
    def __init__(self, fg_color=None, **kwargs):
        super().__init__(fg_color, **kwargs)

        self.therapy = TherapySession()
        
        self.title("AI Therapist")
        self.geometry("600x800")
        ctk.set_appearance_mode("dark")
        self.waiting_response = False
        
        self._setup_grid()
        self._create_widgets()
        self._setup_bindings()
        self._add_message(self.therapy.getInitialMessage(), "ai")
        
    def _setup_grid(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
    def _create_widgets(self):
        # Header
        self.header = ctk.CTkLabel(self, text="AI Therapist", font=("Arial", 24))
        self.header.grid(row=0, column=0, pady=15, sticky="ew")
        
        # Chat area
        self.chat_frame = ctk.CTkScrollableFrame(self)
        self.chat_frame.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="nsew")
        self.chat_frame.grid_columnconfigure(0, weight=1)
        
        # Input area
        self._setup_input_area()
        
        self.preview_frame = None
        self.current_image = None
        self.cross_label = None
        
    def _setup_input_area(self):
        self.input_frame = ctk.CTkFrame(self, fg_color="#333333")
        self.input_frame.grid(row=2, column=0, sticky="ew")
        self.input_frame.grid_columnconfigure(1, weight=1)
        
        # Text input
        self.text_input = ctk.CTkTextbox(
            self.input_frame,
            height=50,
            fg_color="#333333",
            text_color="#FFFFFF",
            border_width=0
        )
        self.text_input.grid(row=0, column=1, padx=5, sticky="ew")
        
        # Buttons
        self.attach_btn = self._create_button("📎", "#333333", self.attach_file, 0)
        self.send_btn = self._create_button("→", "#3D5AFE", self.send_message, 2)
        
    def _create_button(self, text, color, command, column):
        btn = ctk.CTkButton(
            self.input_frame,
            text=text,
            width=40,
            fg_color=color,
            hover_color="#444444" if color == "#333333" else "#303F9F",
            command=command
        )
        btn.grid(row=0, column=column, padx=5)
        return btn
        
    def _setup_bindings(self):
        self.text_input.bind("<Return>", self._handle_return)
        self.text_input.bind("<Shift-Return>", lambda e: "break")
        
    def _handle_return(self, event):
        if not event.state & 0x1:
            self.send_message()
            return "break"
        return None
        
    def attach_file(self):
        if self.current_image or self.waiting_response:
            return
            
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        if file_path:
            self._show_image_preview(file_path)
            
    def _show_image_preview(self, file_path):
        self._create_preview_frame()
        
        image = Image.open(file_path)
        image.thumbnail((40, 40))
        photo = ImageTk.PhotoImage(image)
        
        preview_label = ctk.CTkLabel(self.preview_frame, image=photo, text="")
        preview_label.image = photo
        preview_label.grid(row=0, column=0)
        
        preview_label.bind("<Enter>", self._show_delete_button)
        self.preview_frame.bind("<Leave>", self._hide_delete_button)
        
        self.current_image = file_path
        
    def _create_preview_frame(self):
        if self.preview_frame:
            self.preview_frame.destroy()
            
        self.preview_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.preview_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=5, sticky="w")
        
    def _show_delete_button(self, event):
        if not self.cross_label:
            self.cross_label = ctk.CTkLabel(
                self.preview_frame,
                text="✕",
                fg_color="red",
                text_color="white",
                width=20,
                height=20,
                corner_radius=10
            )
            self.cross_label.place(relx=0.8, rely=0, anchor="n")
            self.cross_label.bind("<Button-1>", self._remove_image)
            
    def _hide_delete_button(self, event):
        if self.cross_label:
            self.cross_label.destroy()
            self.cross_label = None
            
    def _remove_image(self, event=None):
        if self.preview_frame:
            self.preview_frame.destroy()
            self.preview_frame = None
        self.current_image = None
        self.cross_label = None
        
    def send_message(self):
        if self.waiting_response:
            return

        message = self.text_input.get("1.0", "end-1c").strip()
        image_path = self.current_image

        if not (image_path or message):
            return

        # Add user's message
        self._add_message(message, "user", image_path)
        self.text_input.delete("1.0", "end")
        self._remove_image()
        self._disable_input()

        # Add "Loading..." message
        self.loading_message_id = self._add_message("Loading...", "ai")

        # Start response processing in a separate thread
        threading.Thread(
            target=self._process_response,
            args=(message, image_path),
            daemon=True
        ).start()
        
    def _process_response(self, message, image_path):
        # Get the therapist's response
        response = self.therapy.run(message, image_path)

        # Update the "Loading..." message with the actual response
        self._update_message(self.loading_message_id, response)
        self._enable_input()
        
    def _disable_input(self):
        self.waiting_response = True
        self.text_input.configure(state="disabled")
        self.attach_btn.configure(state="disabled")
        self.send_btn.configure(state="disabled")
        
    def _enable_input(self):
        self.waiting_response = False
        self.text_input.configure(state="normal")
        self.attach_btn.configure(state="normal")
        self.send_btn.configure(state="normal")
        
    def _add_message(self, message, sender, image_path=None):
        message_frame = ctk.CTkFrame(
            self.chat_frame,
            fg_color="#4B4B4B" if sender == "user" else "#3D5AFE"
        )
        message_frame.grid(sticky="e" if sender == "user" else "w", pady=5)
        message_frame.grid_columnconfigure(0, weight=1)

        current_row = 0
        if image_path:
            self._add_image_to_message(message_frame, image_path, current_row)
            current_row += 1

        if message.strip():
            label = ctk.CTkLabel(
                message_frame,
                text=message,
                wraplength=350
            )
            label.grid(row=current_row, column=0, padx=10, pady=5)

        # Auto-scroll to bottom
        self.after(10, self._scroll_to_bottom)

        # Return a reference to the message frame (used for updating "Loading...")
        return message_frame
    
    def _update_message(self, message_frame, new_message):
        # Update the text of the given message frame
        for widget in message_frame.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(text=new_message)
                break
        
    def _add_image_to_message(self, frame, image_path, row):
        image = Image.open(image_path)
        image.thumbnail((300, 300))
        photo = ImageTk.PhotoImage(image)
        
        img_label = ctk.CTkLabel(frame, image=photo, text="")
        img_label.image = photo
        img_label.grid(row=row, column=0, padx=10, pady=5)
        
    def _scroll_to_bottom(self):
        self.chat_frame._parent_canvas.yview_moveto(1.0)

if __name__ == "__main__":
    app = ChatWindow()
    app.mainloop()
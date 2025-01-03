import customtkinter as ctk

class ChatHeader(ctk.CTkLabel):
    """
    A simple header label for the chat window.
    """
    def __init__(self, master):
        super().__init__(master, text="AI Therapist", font=("Arial", 24))
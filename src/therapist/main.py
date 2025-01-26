from ui.chatWindow import ChatWindow
from therapy import TherapySession
import os

os.environ["OPENAI_MODEL_NAME"] = "gpt-4o"

app = ChatWindow(TherapySession())
app.mainloop()
from ui.chatWindow import ChatWindow
from therapy import TherapySession
import os

os.environ["OPENAI_MODEL_NAME"] = "o1"

app = ChatWindow(TherapySession())
app.mainloop()
from ui.chatWindow import ChatWindow
from therapy import TherapySession

app = ChatWindow(TherapySession())
app.mainloop()
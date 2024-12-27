import random
from crew import Therapist

class TherapySession:
    def __init__(self, therapist_name="Kevin"):

        self.therapist = Therapist()
        self.crew = self.therapist.crew()
        self.conversation_history = ""
        self.therapist_name = therapist_name
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
        self.initial_text = random.choice(self.welcome_messages)
        self.conversation_history = "Therapist: " + self.initial_text + "\n"

    def run(self, user_text_prompt=None, image_path=None):
        """
        Process user input and interact with the therapist.

        Args:
            user_text_prompt (str): Text input from the user.
            image_file (File): Optional uploaded image file.

        Returns:
            str: Therapist's response.
        """
        if not user_text_prompt and not image_path:
            return "I’m here to listen, but I didn’t catch that. Could you try again?"

        # Log user input
        if user_text_prompt:
            self.conversation_history += f"Client (Text): {user_text_prompt}\n"
        if image_path:
            self.conversation_history += f"Client (Image): {image_path}\n"

        # Prepare inputs for the therapist
        inputs = {
            'text': user_text_prompt or "",
            'image': image_path if image_path else "",
            'history': self.conversation_history
        }

        # Generate therapist's response
        try:
            result = self.crew.kickoff(inputs=inputs)
            response = result.raw
        except Exception as e:
            response = "I encountered an issue processing that. Could you try again?"

        # Log therapist's response
        self.conversation_history += f"Therapist: {response}\n"
        return response
    
    def getInitialMessage(self):
        return self.initial_text
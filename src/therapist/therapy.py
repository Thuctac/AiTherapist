import random
from crew import Therapist

class TherapySession:
    def __init__(self):

        self.therapist = Therapist()
        self.crew = self.therapist.crew()
        self.conversation_history = ""

    def run(self, user_text_prompt=None, image_path=None, audio_path=None, conversation_log=None):
        """
        Process user input and interact with the therapist.

        Args:
            user_text_prompt (str): Text input from the user.
            image_file (File): Optional uploaded image file.

        Returns:
            str: Therapist's response.
        """
        self.conversation_history = conversation_log

        # Prepare inputs for the therapist
        inputs = {
            'text': user_text_prompt or "",
            'image': image_path if image_path else "",
            'audio_path': audio_path if audio_path else "",
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
    
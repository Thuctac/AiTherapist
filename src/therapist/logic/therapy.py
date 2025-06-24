from .crew import Therapist

class TherapySession:
    def __init__(self):
        self.conversation_history = ""

    def run(self, user_text=None, image_path=None, audio_path=None, conversation_log=None):
        """
        Process user input and interact with the therapist.

        Args:
            user_text (str): Text input from the user.
            image_path (str): Path to an optional uploaded image file.
            audio_path (str): Path to an optional uploaded audio file.
            conversation_log (str): Existing conversation history.

        Returns:
            str: Therapist's response.
        """
        # Update history if provided
        if conversation_log is not None:
            self.conversation_history = conversation_log

        # Determine which inputs are provided
        text_provided = bool(user_text)
        image_provided = bool(image_path)
        audio_provided = bool(audio_path)

        # Initialize therapist with appropriate flags
        therapist = Therapist(
            text_provided=text_provided,
            image_provided=image_provided,
            audio_provided=audio_provided
        )
        crew = therapist.crew()

        # Build inputs dict
        inputs = {"history": self.conversation_history}
        if text_provided:
            inputs["text"] = user_text
        if image_provided:
            inputs["image"] = image_path
        if audio_provided:
            inputs["audio_path"] = audio_path

        # Generate response
        result = crew.kickoff(inputs=inputs)
        response = result.raw

        # Update history
        self.conversation_history += f"Therapist: {response}\n"
        return response
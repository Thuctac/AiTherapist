from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from groq import Groq
import os

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def transcribe_audio(audio_file_path):
    """
    Transcribe audio using Groq's Whisper implementation.
    """
    try:
        with open(audio_file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(os.path.basename(audio_file_path), file.read()),
                model="whisper-large-v3",
                prompt="""The audio is a recording of an individual speaking candidly about their thoughts, feelings, and experiences, 
                as if addressing a psychotherapist. The content may include discussions about emotions, personal challenges, relationships, and life events. 
                The tone is introspective and reflective, and the transcription should aim to capture the speaker's words as accurately as possible, maintaining the emotional nuances of the conversation.""",
                response_format="text",
            )
        return transcription  # This is now directly the transcription text
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None


class MyCustomToolInput(BaseModel):
    """Input schema for MyCustomTool."""
    audio_path: str = Field(..., description="The given string is the audio path where the recorded audio is stored")

class VoiceTranscriptionTool(BaseTool):
    name: str = "VoiceTranscriptionTool"
    description: str = (
        "The tool takes an audio_path and automatically converts spoken audio into written text, providing accurate transcriptions."
    )
    args_schema: Type[BaseModel] = MyCustomToolInput

    def _run(self, audio_path: str) -> str:
        # Implementation goes here
        return transcribe_audio(audio_file_path=audio_path)

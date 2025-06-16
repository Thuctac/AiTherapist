from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os
import openai

openai.api_key = os.environ.get("OPENAI_API_KEY")


def transcribe_audio(audio_file_path):
    """
    Transcribe audio using OpenAI's Whisper model.
    """
    try:
        with open(audio_file_path, "rb") as file:
            transcription = openai.Audio.transcribe(
                model="gpt-4o-transcribe",
                file=file,
                prompt="""The audio is a recording of an individual speaking candidly about their thoughts, feelings, and experiences, 
                as if addressing a psychotherapist. The content may include discussions about emotions, personal challenges, relationships, and life events. 
                The tone is introspective and reflective, and the transcription should aim to capture the speaker's words as accurately as possible, maintaining the emotional nuances of the conversation.""",
                response_format="text"
            )
        return transcription  # Returns the plain text
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

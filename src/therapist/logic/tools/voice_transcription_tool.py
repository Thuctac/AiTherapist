from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def transcribe_audio(audio_file_path):
    """
    Transcribe audio using OpenAI’s Whisper-based GPT-4o Transcribe model.
    """
    try:
        with open(audio_file_path, "rb") as audio_file:
            # NEW: use `audio.transcriptions.create`
            result = client.audio.transcriptions.create(
                model="gpt-4o-transcribe",
                file=audio_file,
                prompt=(
                    "The audio is a recording of an individual speaking candidly "
                    "about their thoughts, feelings, and experiences, "
                    "as if addressing a psychotherapist. The content may include "
                    "discussions about emotions, personal challenges, relationships, "
                    "and life events. The tone is introspective and reflective, "
                    "and the transcription should aim to capture the speaker’s words "
                    "as accurately as possible, maintaining the emotional nuances."
                ),
                response_format="text"
            )
        # If you set response_format="text", `result` is a plain string
        return result
    except Exception as e:
        print(f"An error occurred: {e}")
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

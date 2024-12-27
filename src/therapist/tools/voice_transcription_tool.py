from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field


class MyCustomToolInput(BaseModel):
    """Input schema for MyCustomTool."""
    argument: str = Field(..., description="Description of the argument.")

class VoiceTranscriptionTool(BaseTool):
    name: str = "Voice Transcription Tool"
    description: str = (
        "The tool takes an audio file and automatically converts spoken audio into written text, providing accurate transcriptions."
    )
    args_schema: Type[BaseModel] = MyCustomToolInput

    def _run(self, argument: str) -> str:
        # Implementation goes here
        return "this is an example of a tool output, ignore it and move along."

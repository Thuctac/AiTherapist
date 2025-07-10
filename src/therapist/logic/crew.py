from crewai import Agent, Crew, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import VisionTool
from .tools.voice_transcription_tool import VoiceTranscriptionTool
from .tools.ser_tool import SERTool
import os

ollama_host = os.getenv('OLLAMA_HOST', 'host.docker.internal:11434')

base_url = f"http://{ollama_host}"

therapistllm = LLM(
    model="ollama/therapist-llm:latest",
    base_url=base_url,
    temperature=0.3,
    timeout=60,
)

@CrewBase
class Therapist():
    """Therapist crew"""

    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    vision_tool = VisionTool()
    voice_tool = VoiceTranscriptionTool()
    ser_tool = SERTool()


    def __init__(self, text_provided=False, audio_provided=False, image_provided=False):
        self.enable_text_agent = text_provided
        self.enable_audio_agent = audio_provided
        self.enable_image_agent = image_provided

    @agent
    def imageTherapist(self) -> Agent:
        return Agent(
            config=self.agents_config['imageTherapist'],
            tools=[self.vision_tool],
            verbose=True,
        )

    @agent
    def textTherapist(self) -> Agent:
        return Agent(
            config=self.agents_config['textTherapist'],
            verbose=True,
            
        )

    @agent
    def voiceTherapist(self) -> Agent:
        return Agent(
            config=self.agents_config['voiceTherapist'],
            tools=[self.voice_tool, self.ser_tool],
            verbose=True,
        )

    @agent
    def therapist(self) -> Agent:
        return Agent(
            config=self.agents_config['therapist'],
            memory=True,
            verbose=True,
            llm=therapistllm
        )

    @task
    def image_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['image_analysis_task'],
            output_file='report/image_report.md',
            async_execution=True,
        )

    @task
    def text_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['text_analysis_task'],
            output_file='report/text_report.md',
            async_execution=True,
        )

    @task
    def voice_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['voice_analysis_task'],
            output_file='report/audio_report.md',
            async_execution=True,
        )

    @task
    def multimodal_conversation_task(self) -> Task:
        context = []
        if self.enable_audio_agent:
            context.append(self.voice_analysis_task())
        if self.enable_image_agent:
            context.append(self.image_analysis_task())
        if self.enable_text_agent:
            context.append(self.text_analysis_task())
        return Task(
            config=self.tasks_config['conversation_task'],
            context=context,
            async_execution=False,
        )

    def crew(self) -> Crew:
        """Creates the Therapist crew"""
        agents = []
        tasks = []

        if self.enable_audio_agent:
            agents.append(self.voiceTherapist())
            tasks.append(self.voice_analysis_task())
        if self.enable_image_agent:
            agents.append(self.imageTherapist())
            tasks.append(self.image_analysis_task())
        if self.enable_text_agent:
            agents.append(self.textTherapist())
            tasks.append(self.text_analysis_task())
        
        agents.append(self.therapist())
        tasks.append(self.multimodal_conversation_task())
        
        return Crew(
            agents=agents,
            tasks=tasks,
            verbose=False,
        )

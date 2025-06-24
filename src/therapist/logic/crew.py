from crewai import Agent, Crew, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import VisionTool
from .tools.voice_transcription_tool import VoiceTranscriptionTool
from .tools.ser_tool import SERTool

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
        )

    @task
    def visual_context_recognition_task(self) -> Task:
        return Task(
            config=self.tasks_config['visual_context_recognition_task'],
            output_file='report/ImageTherapist_report.md',
            async_execution=True,
        )

    @task
    def cognitive_reframing_task(self) -> Task:
        return Task(
            config=self.tasks_config['cognitive_reframing_task'],
            output_file='report/TextTherapist_report.md',
            async_execution=True,
        )

    @task
    def audio_emotion_insight_task(self) -> Task:
        return Task(
            config=self.tasks_config['audio_emotion_insight_task'],
            output_file='report/VoiceTherapist_report.md',
            async_execution=True,
        )

    @task
    def multimodal_conversation_task(self) -> Task:
        context = []
        if self.enable_audio_agent:
            context.append(self.audio_emotion_insight_task())
        if self.enable_image_agent:
            context.append(self.visual_context_recognition_task())
        if self.enable_text_agent:
            context.append(self.cognitive_reframing_task())
        return Task(
            config=self.tasks_config['multimodal_conversation_task'],
            context=context,
            output_file='report/Output.md',
            async_execution=False,
        )

    def crew(self) -> Crew:
        """Creates the Therapist crew"""
        agents = [self.therapist()]
        tasks = []

        if self.enable_audio_agent:
            agents.append(self.voiceTherapist())
            tasks.append(self.audio_emotion_insight_task())
        if self.enable_image_agent:
            agents.append(self.imageTherapist())
            tasks.append(self.visual_context_recognition_task())
        if self.enable_text_agent:
            agents.append(self.textTherapist())
            tasks.append(self.cognitive_reframing_task())
            
        tasks.append(self.multimodal_conversation_task())
        
        return Crew(
            agents=agents,
            tasks=tasks,
            verbose=False,
        )

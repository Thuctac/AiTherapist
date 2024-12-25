from crewai import Agent, Crew, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import VisionTool

# If you want to run a snippet of code before or after the crew starts, 
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class Therapist():
	"""Therapist crew"""

	# Learn more about YAML configuration files here:
	# Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
	# Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'

	# If you would like to add tools to your agents, you can learn more about it here:
	# https://docs.crewai.com/concepts/agents#agent-tools
	vision_tool = VisionTool()

	@agent
	def imageTherapist(self) -> Agent:
		return Agent(
			config = self.agents_config['imageTherapist'],
            tools = [self.vision_tool],
            verbose = False,
			allow_delegation=True,
		)

	@agent
	def textTherapist(self) -> Agent:
		return Agent(
			config=self.agents_config['textTherapist'],
			memory = True,
			human_input = True,
			verbose=False,
			allow_delegation=True,
		)
	
	@agent
	def therapist(self) -> Agent:
		return Agent(
			config=self.agents_config['therapist'],
			memory=True,
			verbose=False,
			allow_delegation=True,
		)

	# To learn more about structured task outputs, 
	# task dependencies, and task callbacks, check out the documentation:
	# https://docs.crewai.com/concepts/tasks#overview-of-a-task
	@task
	def visual_context_recognition_task(self) -> Task:
		return Task(
			config=self.tasks_config['visual_context_recognition_task'],
			output_file='visual_context_recognition_report.md'
		)

	@task
	def cognitive_reframing_task(self) -> Task:
		return Task(
			config=self.tasks_config['cognitive_reframing_task'],
			output_file='cognitive_reframing_report.md',
		)
	
	@task
	def conversation_task(self) -> Task:
		return Task(
			config=self.tasks_config['conversation_task'],
			context= [self.visual_context_recognition_task(), self.cognitive_reframing_task()],
			output_file='conversation.md',
		)

	@crew
	def crew(self) -> Crew:
		"""Creates the Therapist crew"""
		# To learn how to add knowledge sources to your crew, check out the documentation:
		# https://docs.crewai.com/concepts/knowledge#what-is-knowledge

		return Crew(
			agents=self.agents, # Automatically created by the @agent decorator
			tasks=self.tasks, # Automatically created by the @task decorator
			verbose=False,
		)

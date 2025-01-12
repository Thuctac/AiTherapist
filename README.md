# Therapist Crew

Welcome to the Therapist Crew project, a Bachelor Semester Project by Thuc Kevin Nguyen, powered by crewAI. This guide helps you set up a multi-agent AI system where multiple specialized “therapist” agents collaborate to provide text, image, and audio-based therapy insights. All of this is managed by the crewAI framework.

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Project](#running-the-project)
- [Naming Conversations](#naming-conversations)
- [Understanding Your Crew](#understanding-your-crew)
- [Project Code Overview](#project-code-overview)
- [Support](#support)

## Features
- Multiple agents (Text, Image, and Voice Therapists) with specialized roles.
- Modular tasks configured via YAML, each agent having unique goals and backstories.
- Custom UI (`ui/chatWindow.py`) for user interaction.
- Seamless generation and saving of conversation logs, with user-defined names.
- Integrations for image and audio processing (`VisionTool`, `VoiceTranscriptionTool`).

## Installation

### Python
Ensure you have Python version `>=3.10` and `<=3.13` installed.

### Install Dependencies
Install dependencies from the `requirements.txt` file:
```bash
pip install -r requirements.txt
```

### Environment Variables
1. Create a `.env` file in your project root.
2. Add your `OPENAI_API_KEY` (and any other API keys) inside this file:
   ```bash
   OPENAI_API_KEY=your_openai_key_here
   GROQ_API_KEY=your_groq_key_here
   ```

## Configuration

### Agents
- Located in `src/therapist/config/agents.yaml`.
- Each agent is described by a role, goal, and backstory (e.g., `imageTherapist`, `textTherapist`, etc.).

### Tasks
- Located in `src/therapist/config/tasks.yaml`.
- Each task references an agent and provides a description of how to handle user input.

### Crew / Logic
- Defined in `src/therapist/crew.py`.
- Includes logic to wire up agents, tasks, memory, and custom tools like `VisionTool` and `VoiceTranscriptionTool`.

### UI
- The UI code (e.g., `ui/chatWindow.py`) manages the chat window, image/audio handling, conversation logs, and conversation naming.

### Therapy Session
- Located in `therapy.py`.
- Contains the `TherapySession` class that orchestrates how user input is handled and passed to the crew.

## Running the Project
From the root of your project, run:
```bash
python3 src/therapist/main.py
```
This launches your Therapist Crew, instantiating each agent and assigning tasks as defined in your YAML configurations. Any text, image, or audio provided through the UI or programmatic calls is processed by the relevant agent (`Text`, `Image`, or `Voice Therapists`). The final synthesis is done by the multimodal therapist.

By default, the sample tasks produce markdown reports in a `report/` folder (e.g., `ImageTherapist_report.md`, `TextTherapist_report.md`, `VoiceTherapist_report.md`) and an overall output `Output.md`.

## Naming Conversations
- You can name your conversation when you start a new session.
- If you load an older conversation, it uses that old name to save logs.
- If you try to name a new conversation using an existing name, you’ll be prompted to choose a different one.
- Each session has a unique log file, e.g.:
  ```bash
  log/YourConversationName.txt
  ```

## Understanding Your Crew
The Therapist Crew is composed of multiple AI agents:

- **imageTherapist**: Analyzes images using `VisionTool`, providing emotional context and cognitive reframing suggestions.
- **textTherapist**: Focuses on text-based input, identifying cognitive distortions and offering reframes.
- **voiceTherapist**: Transcribes and analyzes audio recordings, detecting negative patterns or emotional cues.
- **therapist**: Serves as the multimodal psychotherapist, synthesizing input from image, text, and audio to deliver holistic insights.

These agents work on tasks such as:

- `visual_context_recognition_task`
- `cognitive_reframing_task`
- `audio_emotion_insight_task`
- `multimodal_conversation_task`

`crewAI` coordinates these agents, passing them user inputs, and reassembling their outputs for an integrated therapy session.

## Project Code Overview

### Root Folder
- **`README.md`**: This file, describing the project, setup, usage, etc.
- **`.env`**: Contains environment variables like `OPENAI_API_KEY`.
- **`crewai.yaml` or `pyproject.toml`**: Used for dependency locking.
- **`report/`**: Where agents store result logs (`*.md`).

### `src/therapist/`
- **`config/agents.yaml`**: Agent definitions (e.g., `imageTherapist`, `textTherapist`, etc.).
- **`config/tasks.yaml`**: Task definitions describing how each agent processes user data.
- **`crew.py`**: The main `Crew` class tying agents and tasks together.
- **`main.py`**: A script hooking custom inputs into the tasks.

### `ui/`
- **`chatWindow.py`**: Manages the graphical user interface (GUI), load/new conversations, image/audio attachments, and conversation logs.
- Possibly other UI modules.

### `therapy.py`
- Contains the `TherapySession` class that integrates with your Therapist crew.
- Defines how user input (text/image/audio) is passed to the crew and how to handle the results.

## Support
For any questions or issues, please open an issue in the repository or contact the project maintainers.

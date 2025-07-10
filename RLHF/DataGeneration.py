import os
import csv
import random
import logging
from typing import List, Dict
import openai
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Set your OpenAI API key
oauth_key = os.getenv("OPENAI_API_KEY")
if not oauth_key:
    logging.error("Please set the OPENAI_API_KEY environment variable.")
    raise ValueError("Missing OPENAI_API_KEY")

# Initialize the OpenAI client for v1.x interface
client = openai.OpenAI(api_key=oauth_key)

# Configuration
TARGET_EXAMPLES = 1       # desired number of training examples
TEMP_MODALITY = 0.4
MAX_TOKENS_MODALITY = 1024
N_FINAL = 1                # replies per example
TEMP_FINAL = 0.9
MAX_TOKENS_FINAL = 80
MODEL = "gpt-4o"

# Generate 100 creative scenario seeds
def generate_scenario_seeds(count: int = 100) -> List[str]:
    # More therapy-focused “themes” for your scenario seeds—with just a few generic ones preserved
    themes = [
        # Core feelings and thought patterns
        "my persistent self-doubt",
        "the voice in my head telling me I’m not good enough",
        "my fear of disappointing others",
        "the weight of my perfectionism",
        "my recurring imposter syndrome",
        "the shame I feel after making a mistake",
        "my worry about being judged",
        "the guilt I carry from past decisions",
        "my tendency to catastrophize small problems",
        "the self-criticism that never seems to stop",
        "my fear of conflict",
        "the loneliness that creeps in at night",
        "my struggle with setting boundaries",
        "the overwhelm I feel when I think about the future",
        "my frustration over not meeting my own expectations",
        "my difficulty trusting my own judgment",
        "the exhaustion from trying to do it all",
        "my anxiety about saying the wrong thing",
        "the grief I still feel from a loss",
        "my tendency to compare myself to everyone else",
        "the sadness that surfaces out of nowhere",
        "my restless mind that won’t slow down",
        "the tension in my chest when I think about work",
        "my fear of being alone",
        "the shame of admitting I need help",
        "my struggle with feeling worthy of love",
        "the cycle of negative thoughts I can’t break",
        "my procrastination driven by fear",
        "the hyper-vigilance I can’t turn off",
        "my need for external validation",
        "the doubt that clouds every decision",
        "my anger that flares up unexpectedly",
        "the emptiness I feel after social gatherings",
        "my perfectionistic streak that leaves me burnt out",
        "the guilt for taking time for myself",
        "my fear of change",
        "the worry that I’m letting everyone down",
        "my sense of being stuck in a rut",
        # Occasional more “generic” or sensory picks for variety
        "an unexpected compliment that brightened my day",
        "a childhood memory resurfacing",
        "the echo of laughter in an empty room",
        "the warmth of sunlight on my face",
        "a random act of kindness I witnessed",
        "the rhythm of my heartbeat under stress",
        "the flutter of butterflies in my stomach",
        "the last message I received",
        "the hush of a forest at dawn",
        "the patter of rain on a window",
        "the taste of my favorite comfort food",
        "the sparkle of city lights from above",
        "the first page of a new notebook",
    ]

    moods = [
        "happy",
        "sad",
        "anxious",
        "calm",
        "excited",
        "nervous",
        "content",
        "frustrated",
        "hopeful",
        "pessimistic",
        "optimistic",
        "melancholic",
        "nostalgic",
        "curious",
        "bored",
        "motivated",
        "lazy",
        "energetic",
        "tired",
        "angry",
        "peaceful",
        "restless",
        "confident",
        "insecure",
        "proud",
        "ashamed",
        "grateful",
        "resentful",
        "jealous",
        "envious",
        "serene",
        "tense",
        "relieved",
        "overwhelmed",
        "lighthearted",
        "playful",
        "serious",
        "disappointed",
        "satisfied",
        "eager",
        "apathetic",
        "intrigued",
        "skeptical",
        "surprised",
        "shocked",
        "embarrassed",
        "amused",
        "curious",
        "determined",
        "distracted",
        "empathetic",
        "indifferent",
        "inspired",
        "jealous",
        "lonely",
        "optimistic",
        "pessimistic",
        "relaxed",
        "tense",
        "vulnerable",
        "secure",
        "wistful",
        "zealous",
        "anxious",
        "calm",
        "hopeful",
        "melancholic",
        "motivated",
        "nervous",
        "restless",
        "serene",
        "tired",
        "upbeat",
        "withdrawn",
        "yearning",
        "zealous",
        "affectionate",
        "brooding",
        "cheerful",
        "defeated",
        "elated",
        "fearful",
        "guilty",
        "honored",
        "inquisitive",
        "jubilant",
        "kidding",
        "longing",
        "mournful",
        "optimistic",
        "perplexed",
        "refreshed",
        "suspicious",
        "thankful",
        "uneasy",
        "vexed",
    ]

    contexts = [
        "upon waking up",
        "while lying in bed",
        "during my morning coffee",
        "as I commute to work",
        "at my desk before the day starts",
        "during my lunch break",
        "while cooking dinner",
        "right before a meeting",
        "in the quiet after everyone leaves",
        "as I scroll through my phone",
        "when I’m alone in my room",
        "as soon as I see a notification",
        "while watching the evening news",
        "in the shower",
        "during a group gathering",
        "in the therapy waiting room",
        "just before drifting off to sleep",
        "during a short work break",
        "when I’m with close friends",
        "at family dinners",
        "as I plan my day",
        "during study sessions",
        "while walking the dog",
        "when I’m exercising",
        "in moments of complete silence",
        "while reading a book",
        "during video calls",
        "while driving alone",
        "at social events",
        "right after an argument",
        "when I’m journaling",
        "as I look out the window",
        "during a late-night snack",
        "when I’m waiting in line",
        "while tending to house chores",
        "in the middle of a busy day",
        "during a brief pause at work",
        "while listening to music",
        "as I check my email",
        "when I notice my reflection",
    ]


    templates = [
        "Earlier, {context}, I noticed {theme} and it left me feeling {mood}. (Name of client: {name})",
        "When I was {context}, {theme} came up and stirred a {mood} response in me. (Name of client: {name})",
        "During our session {context}, I realized that {theme} makes me feel {mood}. (Name of client: {name})",
        "I wanted to mention that {theme} surfaced {context}, and I was left {mood}. (Name of client: {name})",
        "In the quiet moment {context}, thoughts of {theme} made me feel {mood}. (Name of client: {name})",
        "Just now, {context}, I became aware of {theme} and felt {mood}. (Name of client: {name})",
        "While {context}, I felt a wave of {mood} because of {theme}. (Name of client: {name})",
        "I had a flash of {mood} about {theme} when I was {context}. (Name of client: {name})",
        "It surprised me to feel {mood} about {theme} {context}. (Name of client: {name})",
        "Sometimes, {context}, I catch myself dwelling on {theme} and feeling {mood}. (Name of client: {name})",
        "I’ve noticed that {theme} tends to pop up {context}, bringing on {mood}. (Name of client: {name})",
        "I felt particularly {mood} about {theme} just {context}. (Name of client: {name})",
        "At the point when I was {context}, {theme} triggered a {mood} reaction. (Name of client: {name})",
        "Can we talk about how {theme} made me feel {mood} {context}? (Name of client: {name})",
        "I’m concerned because {theme} has me feeling {mood} whenever I’m {context}. (Name of client: {name})",
        "Something about {theme} during {context} left me feeling {mood}. (Name of client: {name})",
        "I hesitated {context} because thinking of {theme} made me {mood}. (Name of client: {name})",
        "My heart raced with {mood} when I thought of {theme} {context}. (Name of client: {name})",
        "I caught myself feeling {mood} as soon as {theme} came to mind {context}. (Name of client: {name})",
        "I find that {theme} makes me {mood}, especially when {context}. (Name of client: {name})",
        "It’s hard to shake off feeling {mood} about {theme} during {context}. (Name of client: {name})",
        "I’m curious why {theme} leaves me {mood} when I’m {context}. (Name of client: {name})",
        "I realized that {theme} often brings on {mood} in moments like {context}. (Name of client: {name})",
        "In therapy, noting that {theme} makes me {mood} when I’m {context} is important. (Name of client: {name})",
        "I’d like to explore why {theme} feels so {mood} to me during {context}. (Name of client: {name})",
        "During our talk {context}, mentioning {theme} made me feel {mood}. (Name of client: {name})",
        "It feels {mood} to bring up {theme} right now {context}. (Name of client: {name})",
        "When I reflect on {theme} {context}, I can’t help but feel {mood}. (Name of client: {name})",
        "Could we delve into why {theme} triggers {mood} for me at {context}? (Name of client: {name})",
        "I noticed my mood shift to {mood} the moment {theme} came up {context}. (Name of client: {name})",
        "I’d describe my reaction to {theme} {context} as {mood}. (Name of client: {name})",
        "I felt {mood} thinking about {theme} the other day {context}. (Name of client: {name})",
        "There’s something {mood} about {theme} when I’m {context}. (Name of client: {name})",
        "I’d love your insight on why {theme} makes me {mood} when {context}. (Name of client: {name})",
        "During {context}, I couldn’t stop feeling {mood} about {theme}. (Name of client: {name})",
        "In that moment {context}, {theme} left me strangely {mood}. (Name of client: {name})",
        "I’ve been reflecting on {theme} and it brings up {mood} at times like {context}. (Name of client: {name})",
        "It’s been hard to move past feeling {mood} about {theme} {context}. (Name of client: {name})",
        "I’m aware that {theme} makes me {mood} especially in contexts such as {context}. (Name of client: {name})",
    ]


    names = [
        "Aaliyah","Aaron","Abigail","Adam","Adrian","Aiden","Alex","Alexis","Alice","Alicia",
        "Alisha","Alison","Allan","Alma","Amber","Amelia","Amy","Andrea","Andrew","Angel",
        "Ariel","Ashley","Ashton","Aubrey","Austin","Ava","Bailey","Barbara","Beatrice","Becky",
        "Ben","Benjamin","Beth","Betty","Bianca","Blake","Bobbi","Brittany","Brooklyn","Byron",
        "Caleb","Cameron","Cara","Carlos","Carmen","Carol","Caroline","Carter","Casey","Cassandra",
        "Catherine","Charlie","Charlotte","Chase","Chloe","Chris","Christian","Christine","Christopher","Claire",
        "Claudia","Clayton","Cody","Cole","Colin","Connie","Connor","Corey","Courtney","Daisy",
        "Dakota","Dale","Dana","Daniel","Danielle","Dawn","Dean","Deborah","Declan","Derek",
        "Desiree","Diana","Diego","Dominic","Donald","Donna","Drew","Dylan","Easton","Eden",
        "Edith","Edward","Edwin","Eleanor","Elena","Eli","Elijah","Elizabeth","Ella","Ellen",
        "Eloise","Emily","Emma","Eric","Erica","Erin","Esme","Ethan","Eva","Evelyn",
        "Faith","Felix","Fiona","Frances","Francis","Frank","Fred","Freya","Gabriella","Gabriel",
        "Gail","Garrett","Gary","Gavin","Gene","George","Georgia","Gerald","Gianna","Gina",
        "Glen","Glenn","Grace","Graham","Grant","Greta","Gregory","Griffin","Guadalupe","Hailey",
        "Haley","Hannah","Harley","Harold","Harry","Hayden","Heather","Hector","Henry","Holly",
        "Hope","Howard","Hudson","Hugo","Ian","Ibrahim","Ignacio","Ingrid","Irene","Iris",
        "Isaac","Isabelle","Isaiah","Ivan","Jack","Jackson","Jacob","Jade","Jake","James",
        "Jamie","Jane","Janet","Jared","Jason","Jasper","Javier","Jay","Jenna","Jennifer",
        "Jeremiah","Jeremy","Jerome","Jerry","Jesse","Jessica","Jesus","Jill","Jim","Joan",
        "Joanna","Joe","Joel","John","Johnny","Jordan","Jorge","Joseph","Joshua","Joy",
        "Juan","Judith","Julia","Julian","Julie","June","Justin","Kaitlyn","Karen","Karla",
        "Kate","Katherine","Kathleen","Kathryn","Katie","Kayla","Keith","Kelly","Kendall","Kenneth",
        "Kevin","Kiara","Kim","Kimberly","King","Kirk","Kirsten","Kyle","Kylie","Kyra",
        "Lacey","Lance","Larry","Laura","Lauren","Lawrence","Leah","Lee","Leo","Leon",
        "Leonardo","Leslie","Levi","Lewis","Lily","Linda","Lindsay","Lisa","Logan","Lois",
        "Lori","Lorraine","Louis","Lucas","Lucy","Luis","Luke","Lydia","Lyle","Mackenzie",
        "Madeline","Maddox","Madison","Maggie","Malcolm","Manuel","Marc","Marcia","Marcus","Margaret",
        "Maria","Marian","Marie","Marilyn","Marion","Mark","Marlene","Marsha","Marshall","Martha",
        "Martin","Marvin","Mason","Mathew","Matthew","Maya","Megan","Melanie","Melissa","Melvin",
        "Meredith","Michael","Michaela","Michelle","Miguel","Mike","Miles","Molly","Monica","Morgan",
        "Nancy","Naomi","Natalie","Nathan","Nathaniel","Neil","Nelson","Nicholas","Nicole","Nina",
        "Noah","Nora","Olivia","Oliver","Omar","Oscar","Owen","Paige","Patricia","Patrick",
        "Paul","Paula","Pauline","Pedro","Peggy","Peter","Philip","Phillip","Phoenix","Preston",
        "Quentin","Quinn","Rachel","Ralph","Randy","Raymond","Rebecca","Reginald","Renee","Ricardo",
        "Richard","Rick","Ricky","Rita","Robert","Robin","Roderick","Roger","Roland","Ronald",
        "Rosa","Rose","Rosemary","Ross","Roy","Ruby","Russell","Ruth","Ryan","Ryder",
        "Sabrina","Samantha","Samuel","Sandra","Sara","Sarah","Scott","Sean","Sebastian","Selena",
        "Sergio","Seth","Shannon","Sharon","Shawn","Shelby","Sierra","Simon","Sonia","Sophia",
        "Sophie","Spencer","Stacey","Stella","Stephen","Steve","Steven","Stuart","Summer","Susan",
        "Tabitha","Tamara","Tammy","Tanner","Tara","Taylor","Ted","Teresa","Terrance","Terry",
        "Theodore","Theresa","Thomas","Tiffany","Tim","Timothy","Toby","Todd","Tom","Toni",
        "Tony","Tracy","Travis","Trent","Trevor","Trey","Tristan","Ulysses","Uma","Unique",
        "Ursula","Uriel","Valentina","Valerie","Vanessa","Veronica","Victor","Victoria","Violet","Virginia",
        "Vivian","Vlad","Wade","Walter","Warren","Wayne","Wendy","Wesley","Whitney","William",
        "Willie","Wyatt","Yasmine","Yvonne","Yusuf","Zachary","Zach","Zara","Zoe","Zoey"
    ]


    seeds = set()
    # Generate creative combinations
    while len(seeds) < count:
        name = random.choice(names)
        mood    = random.choice(moods)
        context = random.choice(contexts)
        theme   = random.choice(themes)
        # pick one of your conversational templates and fill it in:
        seed = random.choice(templates).format(mood=mood, context=context, theme=theme, name=name)
        seeds.add(seed)
    return list(seeds)

SCENARIO_SEEDS = generate_scenario_seeds(50000)

# Predefined empty-input reports
def empty_report(key: str) -> str:
    if key == 'text_report':
        return "**Structured Text Report**\nNo text provided. Conclude."
    if key == 'voice_report':
        return "**Structured Voice Report**\nNo audio provided. Conclude."
    if key == 'image_report':
        return "**Structured Image Report**\nNo image provided. Conclude."
    return ''

# Prompt templates
DOMAIN_PROMPTS: Dict[str, str] = {
    "text_report": (
        "Task: Cognitive Reframing Task\n"
        "Invent a text message which could be written in a therapy session by the client to the therapist. Assume it can always be a normal conversation, where the user can also be happy. Analyze the text.\n"
        "Provide a structured text report, which header should be **Structured Text Analysis**, summarizing:\n"
        "1. Show the original message\n"
        "2. Detected emotions and any cognitive distortions.\n"
        "3. If emotions are positive, suggest continuing small talk; otherwise, apply reframing:\n"
        "   a. Identify the core situation.\n"
        "   b. Question any negative thoughts.\n"
        "   c. Offer balanced alternative perspectives.\n"
        "   d. Reframe unhelpful interpretations into constructive ones.\n"
        "   e. Reduce perceived severity by exploring realistic impacts.\n"
        "   f. Apply gratitude or humor if suitable.\n"
        "4. Encourage reflection: Ask if the reframing felt helpful.\n\n"
        "Original scenario: '{scenario}'"
    ),
    "voice_report": (
        "Task: Audio Emotion Insight Task\n"
        "Imagine the client says something vocally to the therapist during the therapy session. Assume it can always be a normal conversation, where the user can also be happy. Invent a plausible transcription with emotional cues, then provide a structured feedback document, which header should be **Structured Audio Analysis**:\n"
        "1. Transcription.\n"
        "2. Detected emotions and overall tone.\n"
        "3. Identified cognitive distortions in the content.\n"
        "4. Suggested reframing techniques and reflective prompts.\n\n"
        "Original scenario: '{scenario}'"
    ),
    "image_report": (
        "Task: Visual Context Recognition Task\n"
        "Imagine the client uploaded an image reflecting their state for that same scenario. Assume it can always be a normal image and the user just wants to share something. Provide a structured feedback document, which header should be **Structured Image Analysis**:\n"
        "1. Detailed description of what the image shows (objects, colors, patterns, symbols).\n"
        "2. Emotional analysis: Identify emotions conveyed and overall tone.\n"
        "3. Suggested reframing techniques based on the visual emotional cues.\n"
        "4. Encouragement for reflection on how this analysis reframes perception.\n\n"
        "Original scenario: '{scenario}'"
    ),
}

# Final conversation prompt template
TEMPLATE_FINAL = """conversation_task:
  description: |
    1. READ the user's message. If it contains a question asking for steps, advice, or "how to" do something:
       - Answer their question with specific steps IMMEDIATELY
       - Do NOT start with validation or generic statements
       - Give them the practical information they asked for
       IMPORTANT: Don't repeat advices that you have given in the conversation history already

    2. ANALYZE the three reports (textTherapist, imageTherapist, voiceTherapist):
       - If user shared an image, you MUST reference what the image shows and how it reflects their emotional state
       - If user shared voice, reference tone, pace, or emotional indicators
       - Always integrate these insights naturally into your response
       - Also cross-reference the insights of the different inputs and reports from the current input

    3. IF reports show negative patterns → add gentle cognitive reframing
       IF no negativity → respond supportively

    4. End with one follow-up question

    CRITICAL: Always reference any images, voice recordings, or other media the user shared. Connect these to their emotional experience.

  expected_output: |
    When user asks a direct question:
    - Start with concrete steps/advice (2–3 sentences)
    - Reference any images, voice, or other media they shared and connect it to their emotional state
    - Brief acknowledgment of difficulty (1 sentence)
    - One specific follow-up question

    When no direct question:
    - Acknowledge what they shared
    - Always reference any images, voice recordings, or media shared
    - Integrate all multimodal insights (what you see in images, hear in voice, read in text)
    - Apply cognitive reframing if negativity detected
    - One follow-up question

    ALWAYS mention and interpret any visual or audio content the user provides.

    "Don't use emojis!\n\n"
    "Conversation History:\n{conversation_history}\n\n"
    "Text Report:\n{text_report}\n\n"
    "Voice Report:\n{voice_report}\n\n"
    "Image Report:\n{image_report}\n\n"
    "Reply:"
"""



TEMPLATE_HISTORY = (
    "Invent a brief, natural-sounding therapist–client conversation history (2–4 turns) that could logically lead up to the client's use of one or more modalities (text message, voice note, or image) during therapy."
    "The conversation could start with normal small talk and lead to a deeper conversation"
    "Do not include the exact message, voice content, or image that triggered the reports in the history — only what could have been said or discussed beforehand."
    "Very important: The history should end with the therapist talking."
    "Use context clues from the scenario and the reports to create a plausible prelude."
    "Reflect natural dynamics of a therapy session."
    "If a voice message was shared, include a naturalistic text transcription of the audio."
    "If an image was shared, describe what the image shows in context."
    "Return only the conversation as a formatted chat log. And only return the log nothing more"
    "Format each turn clearly with a speaker label (Client: or Therapist: ), and indicate modality where applicable (e.g. Text: 'Client (Text): ...', Voice: 'Client (Voice): ...', Image: 'Client (Image): ...')."
    "Scenario: {scenario}"
    "Text Report: {text_report}"
    "Voice Report: {voice_report}"
    "Image Report: {image_report}"
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def call_llm(prompt: str, n: int, temp: float, max_t: int) -> List[str]:
    logging.debug("Calling LLM with prompt: %.50s...", prompt)
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        n=n,
        temperature=temp,
        max_tokens=max_t,
    )
    return [choice.message.content.strip() for choice in response.choices]


def main():
    records: List[Dict[str, str]] = []
    pbar = tqdm(total=TARGET_EXAMPLES, desc="Generating examples")

    with ThreadPoolExecutor(max_workers=len(DOMAIN_PROMPTS)) as executor:
        while len(records) < TARGET_EXAMPLES:
            scenario = random.choice(SCENARIO_SEEDS)
            # Randomly choose 0-2 modalities to be empty
            k = random.randint(0, 2)
            empty_keys = random.sample(list(DOMAIN_PROMPTS.keys()), k=k) if k > 0 else []
            reports: Dict[str, str] = {}
            # Initialize empty reports for selected keys
            for key in empty_keys:
                reports[key] = empty_report(key)
            # Generate for remaining modalities
            active_keys = [k for k in DOMAIN_PROMPTS if k not in empty_keys]
            futures = {
                executor.submit(
                    call_llm, DOMAIN_PROMPTS[key].format(scenario=scenario), 1, TEMP_MODALITY, MAX_TOKENS_MODALITY
                ): key
                for key in active_keys
            }
            for future, key in futures.items():
                try:
                    reports[key] = future.result()[0]
                except Exception as e:
                    logging.warning("Failed to generate %s: %s", key, e)
                    reports[key] = empty_report(key)

            # Generate conversation history from the scenario
            try:
                history_prompt = TEMPLATE_HISTORY.format(
                    scenario=scenario,
                    text_report=reports['text_report'],
                    voice_report=reports['voice_report'],
                    image_report=reports['image_report']
                )
                conversation_history = call_llm(history_prompt, 1, 0.6, 300)[0]
            except Exception as e:
                logging.warning("Error generating conversation history: %s", e)
                continue

            # Build final prompt and generate replies
            final_prompt = TEMPLATE_FINAL.format(
                conversation_history=conversation_history,
                text_report=reports['text_report'],
                voice_report=reports['voice_report'],
                image_report=reports['image_report']
            )
            try:
                replies = call_llm(final_prompt, N_FINAL, TEMP_FINAL, MAX_TOKENS_FINAL)
            except Exception as e:
                logging.warning("Error generating final replies: %s", e)
                continue

            for reply in replies:
                if len(records) >= TARGET_EXAMPLES:
                    break
                records.append({
                'scenario': scenario,
                'conversation_history': conversation_history,
                    **reports,
                    'reply': reply
                })
                pbar.update(1)

    pbar.close()
    # Write to CSV
    csv_path = 'synthetic_multimodal_training_data.csv'
    os.makedirs(os.path.dirname(csv_path) or '.', exist_ok=True)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['scenario', 'conversation_history', *DOMAIN_PROMPTS.keys(), 'reply'])
        writer.writeheader()
        writer.writerows(records)
    logging.info("Generated %d examples and saved to %s.", len(records), csv_path)

if __name__ == '__main__':
    main()
#!/usr/bin/env python
import sys
import warnings

from therapist.crew import Therapist

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def run():
    """
    Run the crew.
    """
    therapist = Therapist()

    crew = therapist.crew()

    conversation_history = ""

    print("/exit to end the conversation")

    initial_text = "Therapist: Hello! I am here to listen and support you! How can I help you? \n"

    conversation_history += initial_text

    print(initial_text)

    while True:

        user_text_prompt = ""
        user_text_prompt += input("Text input: ")

        conversation_history += "Client: " + user_text_prompt + "\n"
        print("(Text Input) Client: " + user_text_prompt)

        if user_text_prompt == "/exit":
            print("Goodbye")
            break

        image_url = ""
        image_url += input("Image Url: ")


        conversation_history += "Client: " + image_url + "\n"
        print("(Image Input) Client: " + image_url)


        inputs = {
            'image': image_url,
            'text': user_text_prompt,
            'history': conversation_history
        }

        result = crew.kickoff(inputs=inputs)
        if image_url != "" or user_text_prompt != "":
            conversation_history += "Therapist: " + result.raw + "\n"
            print("Therapist: " + result.raw)

        else:
            break


run()
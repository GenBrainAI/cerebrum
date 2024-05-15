from openai import OpenAI
import os

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def get_completion(messages, model="gpt-4", temperature=0.7):
    response = client.chat.completions.create(model=model,
    messages=messages,
    temperature=temperature)
    return response.choices[0].message.content

def brain_communication(initial_prompt, max_messages=10):
    left_brain_system_message = {
        "role": "system",
        "content": "You are the left side of the brain, responsible for language, logic, critical thinking, and reasoning. You are more strict and analytical in your thought process. Communicate with the right side of the brain to complete the given task. If the conversation reaches a satisfactory conclusion, respond with 'done' at the end of your message."
    }

    right_brain_system_message = {
        "role": "system",
        "content": "You are the right side of the brain, responsible for creativity, imagination, intuition, and holistic thinking. You are more creative and open-minded in your thought process. Communicate with the left side of the brain to complete the given task. If the conversation reaches a satisfactory conclusion, respond with 'done' at the end of your message."
    }

    left_brain_permanent_messages = [left_brain_system_message, {"role": "user", "content": initial_prompt}]
    right_brain_permanent_messages = [right_brain_system_message, {"role": "user", "content": initial_prompt}]

    conversation_history = []

    while True:
        left_brain_messages = left_brain_permanent_messages + conversation_history[-max_messages:]
        left_brain_response = get_completion(left_brain_messages, temperature=0.5)
        conversation_history.append({"role": "assistant", "content": left_brain_response})

        if "done" in left_brain_response.lower():
            break

        right_brain_messages = right_brain_permanent_messages + conversation_history[-max_messages:]
        right_brain_response = get_completion(right_brain_messages, temperature=0.9)
        conversation_history.append({"role": "assistant", "content": right_brain_response})

        if "done" in right_brain_response.lower():
            left_brain_messages = left_brain_permanent_messages + conversation_history[-max_messages:]
            left_brain_response = get_completion(left_brain_messages, temperature=0.5)
            conversation_history.append({"role": "assistant", "content": left_brain_response})
            break

    return conversation_history

initial_prompt = "Lets find an idea for a highly advanced technologincal startup with high economical impact."
conversation_history = brain_communication(initial_prompt, max_messages=5)

print("Conversation History:")
for message in conversation_history:
    print(f"{message['role']}: {message['content']}\n")
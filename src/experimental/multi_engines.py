import openai
import anthropic
import requests

def run_prompt(context, system_message, user_message, engine):
    if engine == "openai":
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": context + "\n" + user_message}
            ]
        )
        return response.choices[0].message['content']
    elif engine == "anthropic":
        client = anthropic.Client("YOUR_ANTHROPIC_API_KEY")
        response = client.completion(
            prompt=f"{anthropic.HUMAN_PROMPT} {context}\n{user_message}{anthropic.AI_PROMPT}",
            stop_sequences=[anthropic.HUMAN_PROMPT],
            model="claude-3-opus-20240229",
            max_tokens_to_sample=1000
        )
        return response.completion
    elif engine == "ollama":
        url = "https://api-inference.huggingface.co/models/codellama/codellama-20b"
        headers = {"Authorization": "Bearer YOUR_HUGGINGFACE_API_TOKEN"}
        payload = {
            "inputs": f"<prompt>{context}\n{user_message}</prompt>",
            "parameters": {
                "max_new_tokens": 1000,
                "temperature": 0.7,
                "stop": ["</s>"]
            }
        }
        response = requests.post(url, headers=headers, json=payload)
        return response.json()[0]['generated_text']
    else:
        raise ValueError(f"Unsupported engine: {engine}")

# Example usage
context = "This is the context for the prompt."
system_message = "You are a helpful assistant."
user_message = "What can you tell me about the context?"

engines = ["openai", "anthropic", "ollama"]

for engine in engines:
    print(f"Running prompt on {engine}:")
    response = run_prompt(context, system_message, user_message, engine)
    print(response)
    print()
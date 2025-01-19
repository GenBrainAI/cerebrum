import os
import random
from langchain.llms import OpenAI, Anthropic, HuggingFaceHub
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.prompts import PromptTemplate

# Set up environment variables for API keys
os.environ["OPENAI_API_KEY"] = "your_openai_api_key"
os.environ["ANTHROPIC_API_KEY"] = "your_anthropic_api_key"
os.environ["HUGGINGFACEHUB_API_TOKEN"] = "your_huggingface_api_token"

# Define the list of LLMs to use
llms = [
    OpenAI(model_name="gpt-4o"),
    OpenAI(model_name="gpt-4o"),
    Anthropic(model="claude-v1"),
    HuggingFaceHub(repo_id="stabilityai/stable-diffusion-3-medium", model_kwargs={"temperature": 0.7}),
]

# Set up the vector database
persist_directory = "thinking_process_db"
embedding = OpenAIEmbeddings()
vectordb = Chroma(persist_directory=persist_directory, embedding_function=embedding)

# Function to get user input for token budget, context, and left/right brain LLMs
def get_user_input():
    while True:
        try:
            budget = int(input("Enter the token budget for the thinking process: "))
            context = input("Enter the context or starting direction for the thinking process: ")
            left_brain_llm = input("Enter the LLM for the left brain (leave blank for random selection): ")
            right_brain_llm = input("Enter the LLM for the right brain (leave blank for random selection): ")
            return budget, context, left_brain_llm, right_brain_llm
        except ValueError:
            print("Invalid input. Please enter a valid integer for the token budget.")

# Function to select an LLM based on user input or randomly
def select_llm(llm_name):
    if llm_name:
        for llm in llms:
            if llm.__class__.__name__.lower() == llm_name.lower():
                return llm
    return random.choice(llms)

# Function to run the LLM with left/right brain process
def llm(prompt, left_brain_llm, right_brain_llm):
    left_brain_response = left_brain_llm(prompt)
    right_brain_response = right_brain_llm(prompt)
    combined_response = f"Left Brain: {left_brain_response}\nRight Brain: {right_brain_response}"
    return combined_response

# Function for idea generation
def idea_generation(context, left_brain_llm, right_brain_llm):
    prompt = f"Generate initial ideas related to the following context:\n{context}\n"
    ideas = llm(prompt, left_brain_llm, right_brain_llm)
    return ideas

# Function for imagination
def imagination(ideas, left_brain_llm, right_brain_llm):
    prompt = f"Imagine and create mental representations for the following ideas:\n{ideas}\n"
    imagined_ideas = llm(prompt, left_brain_llm, right_brain_llm)
    return imagined_ideas

# Function for consideration and evaluation
def consideration_and_evaluation(imagined_ideas, left_brain_llm, right_brain_llm):
    prompt = f"Consider and evaluate the feasibility, practicality, and potential outcomes of the following ideas:\n{imagined_ideas}\n"
    evaluated_ideas = llm(prompt, left_brain_llm, right_brain_llm)
    return evaluated_ideas

# Function for refinement and iteration
def refinement_and_iteration(evaluated_ideas, left_brain_llm, right_brain_llm):
    prompt = f"Refine and iterate on the following ideas, asking questions and seeking additional information:\n{evaluated_ideas}\n"
    refined_ideas = llm(prompt, left_brain_llm, right_brain_llm)
    return refined_ideas

# Function for integration and consolidation
def integration_and_consolidation(refined_ideas, context, left_brain_llm, right_brain_llm):
    prompt = f"Integrate and consolidate the refined ideas into the broader context of existing knowledge and experiences:\n{refined_ideas}\n\nContext: {context}\n"
    consolidated_ideas = llm(prompt, left_brain_llm, right_brain_llm)
    return consolidated_ideas

# Function to run the thinking process
def run_thinking_process(token_budget, context, left_brain_llm, right_brain_llm):
    total_tokens_used = 0
    conversation_history = []

    while total_tokens_used < token_budget:
        # Idea Generation
        ideas = idea_generation(context, left_brain_llm, right_brain_llm)
        conversation_history.append(f"Idea Generation: {ideas}")

        # Imagination
        imagined_ideas = imagination(ideas, left_brain_llm, right_brain_llm)
        conversation_history.append(f"Imagination: {imagined_ideas}")

        # Consideration and Evaluation
        evaluated_ideas = consideration_and_evaluation(imagined_ideas, left_brain_llm, right_brain_llm)
        conversation_history.append(f"Consideration and Evaluation: {evaluated_ideas}")

        # Refinement and Iteration
        refined_ideas = refinement_and_iteration(evaluated_ideas, left_brain_llm, right_brain_llm)
        conversation_history.append(f"Refinement and Iteration: {refined_ideas}")

        # Integration and Consolidation
        consolidated_ideas = integration_and_consolidation(refined_ideas, context, left_brain_llm, right_brain_llm)
        conversation_history.append(f"Integration and Consolidation: {consolidated_ideas}")

        # Update token count
        total_tokens_used += sum(left_brain_llm.get_num_tokens(step) + right_brain_llm.get_num_tokens(step) for step in conversation_history[-5:])

        # Print the consolidated ideas
        print(f"Consolidated Ideas: {consolidated_ideas}")

    # Finalization process
    print("Token budget exhausted. Finalizing the thinking process...")
    finalization_llm = OpenAI(model_name="gpt-4o")
    finalization_prompt = "Finalize the thinking process and provide the user with the most significant insights and ideas generated."
    finalization_response = finalization_llm(finalization_prompt, stop=None, max_tokens=100000)
    print(f"Final Insights:\n{finalization_response}")

    # Ask user if they want to add more tokens to the budget
    add_more_tokens = input("Do you want to add more tokens to the budget? (yes/no): ")
    if add_more_tokens.lower() == "yes":
        additional_budget = int(input("Enter the additional token budget: "))
        token_budget += additional_budget
        print(f"Added {additional_budget} tokens to the budget. New budget: {token_budget}")
        run_thinking_process(token_budget, context, left_brain_llm, right_brain_llm)
    else:
        print("Thinking process completed.")

# Run the thinking process
token_budget, context, left_brain_llm_name, right_brain_llm_name = get_user_input()
left_brain_llm = select_llm(left_brain_llm_name)
right_brain_llm = select_llm(right_brain_llm_name)
run_thinking_process(token_budget, context, left_brain_llm, right_brain_llm)

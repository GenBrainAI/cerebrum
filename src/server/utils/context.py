


def prepare_context(chat_prompt, prompt, message_history, use_functions):
    # todo make it configurable
    model = 'gpt-4o-mini' if use_functions else 'gpt-4o-mini'
    tokens = calc_tokens(chat_prompt, message_history, model, prompt)
    if tokens > max_tokens(model):
        raise HTTPException(status_code=500,
                            detail=f'Too many tokens, {tokens} > max tokens {max_tokens(model)} for {model}')
    return model


def calc_tokens(chat_prompt, message_history, model, prompt):
    encoding = tiktoken.encoding_for_model(model)
    tokens = 0
    tokens = tokens + len(encoding.encode(chat_prompt.messages[0].content))
    message_history.add_message(HumanMessage(content=prompt, ))
    for message in message_history.messages:
        tokens = tokens + len(encoding.encode(message.content))
    return tokens


def max_tokens(model):
    if model == 'gpt-3.5-turbo-0613':
        return 4096
    if model == 'gpt-3.5-turbo-16k-0613':
        return 16385
    elif model == 'gpt-3.5-turbo-1106':
        return 16385
    elif model == 'gpt-4-0613':
        return 8192
    elif model == 'gpt-4-32k-0613':
        return 32768
    elif model == 'gpt-4-turbo-preview':
        return 128000
    elif model == 'gpt-4':
        return 8192
    elif model == 'gpt-4o':
        return 8192


# get messages the can fit to the model limitation,
# this function iterate over the messages backwards
# calculate the length of each message, until the sum of tokens
# reaches the model limitation, then return the messages
# without the last one (keeping 1000 tokens for the response)
# the function also checks for duplicated messages and exclude them
def get_messages_per_model_limit(model: str, message_history: MongoDBChatMessageHistory):
    max_model_tokens = max_tokens(model) - 1000  # Reserve 1000 tokens for the response
    encoding = tiktoken.encoding_for_model(model)

    total_tokens = 0
    unique_message_hashes = set()
    included_messages = []

    # Function to create a hash of a message content
    def hash_content(content):
        return hashlib.sha256(content.encode()).hexdigest()

    # Iterate over the messages in reverse order
    for message in reversed(message_history.messages):
        message_hash = hash_content(message.content)

        # Skip duplicate messages based on hash
        if message_hash in unique_message_hashes:
            continue
        unique_message_hashes.add(message_hash)

        message_token_count = len(encoding.encode(message.content))
        total_tokens += message_token_count

        # If adding this message would exceed the token limit, break the loop
        if total_tokens > max_model_tokens:
            break

        included_messages.append(message)

    # Reverse the message list, so it's in the original order
    return list(reversed(included_messages))


# In case a message is too long, we can summarise it, to shorter version
# we should check the length of the message, select the model that can handle it
# and then summarise it to fit the max tokens of the given model
# we should use the following example
#     messages = [{"role": "user", "content": "please summarise this message, it is too long"}]
#     client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
#     response = client.chat.completions.create(
#         model='gpt-3.5-turbo-0613',
#         messages=messages,
#     )
#
#   in case the response is too long, we should summarise it again, until it fits the model by given factor
def summarise_response(model: str, message: str, factor: float = 0.5):
    # Ensure the factor is between 0 and 1
    factor = max(0., min(factor, 1))

    # Check and trim the original message if needed
    trimmed_message = check_and_trim_message(message)

    # Calculate the desired maximum length of the summary
    max_length = int(len(trimmed_message) * factor)

    # Function to generate a summary
    def generate_summary(content):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Please summarize the following content."},
                    {"role": "user", "content": content}
                ]
            )
            return response.choices[0].message['content'].strip()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Initial summary generation
    summary = generate_summary(trimmed_message)

    # If the summary is still too long, repeat the summarization
    while len(summary) > max_length:
        summary = generate_summary(summary)

    # Final check if the summary fits the model's token limit
    final_summary = check_and_trim_message(summary)

    return final_summary


def check_and_trim_message(content, encoding, max_model_tokens):
    # Calculate the current number of tokens in the message
    current_token_count = len(encoding.encode(content))

    # If the current token count is within the model's limit, return the original content
    if current_token_count <= max_model_tokens:
        return content

    # Calculate the ratio of max tokens to current tokens
    trim_ratio = max_model_tokens / current_token_count

    # Apply a threshold to avoid trimming too much in case of slightly exceeding the limit
    trim_ratio *= 0.90

    # Calculate the approximate character count to keep
    char_count_to_keep = int(len(content) * trim_ratio)

    # Trim the message
    return content[:char_count_to_keep]

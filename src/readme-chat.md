# Cerebrum Chat Interface

A Streamlit-based chat interface for the Cerebrum AI framework that enables interactive conversations while maintaining Cerebrum's task-based architecture.

## Project Structure

```
cerebrum/
├── app/
│   └── chat.py              # Streamlit chat application
├── src/                     # Existing Cerebrum source code
├── requirements.txt         # Project dependencies
└── README.md               # This file
```

## Prerequisites

- Python 3.8+
- Cerebrum and its dependencies installed
- Streamlit

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/cerebrum.git
cd cerebrum
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Add any required API keys to your environment variables or .env file:
```bash
export OPENAI_API_KEY='your-api-key'
export ANTHROPIC_API_KEY='your-api-key'
# Add any other required API keys
```

## Running the Chat Interface

1. Navigate to the project directory:
```bash
cd cerebrum
```

2. Run the Streamlit app:
```bash
streamlit run app/chat.py
```

3. The chat interface will automatically open in your default web browser. If it doesn't, navigate to:
```
http://localhost:8501
```

## Using the Chat Interface

### Loading a State
1. In the sidebar, you can optionally specify a state file path to load a previous Cerebrum state
2. Click "Load State" to load the specified state

### Starting a New Chat
1. Click "New Chat" in the sidebar to start a fresh conversation
2. A new TasksManager and Task will be created automatically

### Accessing Previous Chats
1. Previous chats are listed in the sidebar
2. Click on any chat to load its conversation history

### Having a Conversation
1. Type your message in the input box at the bottom of the screen
2. Press Enter or click the send button
3. The AI will respond, with the response appearing to stream in
4. The conversation is automatically saved in Cerebrum's persistence model

### Navigation Tips
- Use the sidebar to switch between different chats
- Scroll up to view conversation history
- The chat interface will automatically scroll to the latest message

## Troubleshooting

1. If you see an error about missing API keys:
   - Make sure all required API keys are set in your environment
   - Restart the Streamlit application

2. If the state file fails to load:
   - Check that the file path is correct
   - Ensure the state file is in the correct format
   - Try using the default state by leaving the state file path empty

3. If the chat interface appears blank:
   - Refresh the page
   - Check the terminal for any error messages
   - Ensure all dependencies are correctly installed

## Development

The chat interface is designed to be extensible. Key files and their purposes:

- `app/chat.py`: Main Streamlit application
  - Contains the chat interface logic
  - Manages communication with Cerebrum's backend
  - Handles state management and persistence

To modify the interface:
1. Make changes to `app/chat.py`
2. The Streamlit server will automatically reload with your changes
3. Test thoroughly to ensure compatibility with Cerebrum's architecture

## Notes

- The chat interface maintains Cerebrum's task-based architecture while providing a user-friendly experience
- All conversations are stored in Cerebrum's persistence model
- The interface supports multiple chat sessions through TasksManagers
- The streaming effect is simulated for a smoother user experience
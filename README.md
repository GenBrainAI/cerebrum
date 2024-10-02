# Cerebrum: Self-Evolving AI Agentic Framework by GenBrain.ai

## Project Goals and Rationale

Cerebrum is a cutting-edge, self-evolving AI agentic framework designed to revolutionize how enterprises develop, implement, and maintain AI systems. As a core component of GenBrain.ai, Cerebrum aims to:

1. **Self-Understanding and Extension**: Develop an AI system capable of comprehending its own codebase and extending its capabilities autonomously.

2. **Multi-Framework Integration**: Seamlessly integrate and utilize various agentic frameworks such as CrewAI, AutoGen, phidata, LlamaIndex, and LangGraph.

3. **Adaptive Problem Solving**: Generate and apply custom agentic frameworks tailored to specific problem types, enhancing its problem-solving capabilities over time.

4. **Continuous Self-Improvement**: Implement mechanisms for ongoing self-analysis, optimization, and expansion of its functionalities.

5. **Enterprise-Grade AI Operations**: Simplify the implementation of complex AI agentic systems for enterprises, bridging the expertise gap in AI development and maintenance.

The rationale behind Cerebrum is to create an AI system that not only solves complex problems but also evolves and improves itself, reducing the need for constant human intervention in AI development and maintenance.

## General Structure of the Code

Cerebrum is built with a modular and extensible architecture, organized into several key components:

1. **Server**: The core FastAPI application (`main.py`) that serves as the entry point and API layer.

2. **Models**: Pydantic models (`models/`) defining the data structures used throughout the application.

3. **Controllers**: Business logic handlers (`controllers/`) managing various functionalities:
   - `tasks_controller.py`: Manages task creation and execution.
   - `agents_controller.py`: Handles agent creation and management.
   - `assistants_controller.py`: Manages AI assistants.
   - `openapi.py`: Processes OpenAPI specifications for tool generation.

4. **Persistence**: Data storage and retrieval layer (`persistence/`) with support for in-memory and potentially other storage backends.

5. **Tools**: Implementations of various tools and integrations (`tools/`) that Cerebrum can use, such as GitHub integration, file operations, and REST API proxying.

6. **APIs**: API route definitions (`apis/`) organized by functionality.

7. **Utils**: Utility functions and helpers (`utils/`) for common operations.

8. **Notebooks**: Jupyter notebooks (`notebooks/`) for interactive development and testing.

The codebase is designed to be modular, allowing for easy extension and integration of new agentic frameworks and tools. The core functionality revolves around creating, managing, and executing tasks using various AI models and tools, with the ability to self-modify and extend its capabilities.

## Getting Started

To set up and run the Cerebrum project:

1. **Clone the Repository**:
   ```
   git clone https://github.com/GenBrainAI/cerebrum.git
   cd cerebrum
   ```

2. **Set Up a Virtual Environment**:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. **Install Dependencies**:
   ```
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**:
   Create a `.env` file in the project root and add necessary API keys and configurations:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   GITHUB_ACCESS_TOKEN=your_github_token
   GITHUB_REPO_NAME=GenBrainAI/cerebrum
   ```

5. **Run the FastAPI Server**:
   ```
   uvicorn src.server.main:app --reload
   ```

6. **Access the API Documentation**:
   Open a web browser and go to `http://localhost:8000/docs` to view the Swagger UI for API documentation and testing.

7. **Explore and Develop**:
   - Use the Jupyter notebooks in the `notebooks/` directory to interact with Cerebrum interactively.
   - Implement new tools in the `src/server/tools/` directory.
   - Extend agentic capabilities by modifying `src/server/controllers/agents_controller.py`.

8. **Contributing**:
   - Fork the repository and create a new branch for your feature or bug fix.
   - Ensure your code follows the project's coding standards and includes appropriate tests.
   - Submit a pull request with a clear description of your changes and their rationale.

By following these steps, you'll have a local instance of Cerebrum running and be ready to explore its capabilities or contribute to its development.

Remember to regularly check for updates and new features as Cerebrum continues to evolve and improve its self-modification capabilities.


Hello Github 2024-10-02 16:38:38
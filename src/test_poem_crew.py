import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from crewai.tools import BaseTool
from src.server.controllers.agents_controller import create_crew
from src.server.models.agent import CreateCrewRequest, AgentModel, TaskModel, ToolModel
from src.server.controllers.curried_proxy import CurriedProxy

class FileWriterTool(BaseTool):
    """Tool for writing content to a file."""
    name: str = "FileTools.write_file"
    description: str = "Write content to a file at the specified path"

    def _run(self, file_path: str, content: str) -> str:
        """Write content to the specified file.
        
        Args:
            file_path: Path to write the file to
            content: Content to write to the file
            
        Returns:
            A message indicating success
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(content)
            return f"Successfully wrote content to {file_path}"
        except Exception as e:
            return f"Failed to write to file: {str(e)}"

    async def _arun(self, file_path: str, content: str) -> str:
        """Async version of _run."""
        # For file operations, we can just call the sync version
        # since file I/O is already handled by the OS
        return self._run(file_path=file_path, content=content)

async def setup_and_run_poem():
    """Set up and run a CrewAI configuration for poem writing."""
    try:
        # Read the context poem
        poem_path = Path("docs/non_git_files/mom_spaghtii.txt")
        if not poem_path.exists():
            raise FileNotFoundError(f"Context poem not found at {poem_path}")
            
        with open(poem_path, 'r', encoding='utf-8') as f:
            context_poem = f.read()
        print("📚 Loaded context poem")

        # Create and register the tool
        file_writer = FileWriterTool()
        curried_proxy = CurriedProxy()
        curried_proxy.add_tool("FileTools.write_file", file_writer)
        print("🛠️ Registered file writer tool")

        # Create CrewAI configuration request
        create_crew_request = CreateCrewRequest(
            description="Poem Writing Crew",
            agents=[
                AgentModel(
                    role="Creative Poet",
                    goal="Write a powerful poem in the style of the provided context",
                    backstory="""Expert poet specializing in creating emotionally charged verses. 
                    Analyzes reference material carefully to match style and emotional impact.
                    Has a deep understanding of narrative structure and poetic devices.""",
                    tools=[
                        ToolModel(
                            name="FileTools.write_file",
                            description="Write content to a file at the specified path"
                        )
                    ]
                )
            ],
            tasks=[
                TaskModel(
                    description=f"""Study this reference poem and write a new one in the same style:

{context_poem}

The new poem should:
1. Match the emotional intensity and raw authenticity
2. Use similar narrative structure with a clear progression
3. Tell a compelling personal story about ambition and struggle
4. Incorporate vivid imagery and internal monologue
5. Build to a powerful emotional climax
6. Return the poem as your response""",
                    expected_output="A new poem in the same style as the reference",
                    agent_role="Creative Poet"
                )
            ]
        )

        # Create the crew using the controller
        crew = await create_crew(create_crew_request, curried_proxy)

        # Ensure output directory exists
        os.makedirs("output", exist_ok=True)

        # Execute the crew's task
        print("\n🚀 Starting crew execution...")
        result = crew.kickoff()
        
        print("\n✅ Crew execution complete")
        
        # Extract the poem from the result and save it
        if hasattr(result, 'raw'):
            poem = str(result.raw)
            # Save the poem to a file
            output_path = Path("output/new_poem.txt")
            with open(output_path, 'w') as f:
                f.write(poem)
            print("\n📝 New poem written to:", output_path)
            print("\nNew Poem:\n")
            print(poem)
        else:
            print("\n❌ Could not extract poem from result:", type(result))
            print("Available attributes:", dir(result))

        return result

    except Exception as e:
        print(f"❌ Error in poem crew execution: {str(e)}")
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(setup_and_run_poem())
# Cerebrum Dynamic Tools and CrewAI Integration Planning

## Background

Cerebrum is designed as a self-modifying system that grows and evolves through natural conversation. The dynamic tools feature is one of the key pillars of self-awareness, allowing the system to extend its own capabilities by creating and integrating new tools.

### Current Implementation
- Dynamic tools loader watches the `src/tools` directory for changes
- New tools are automatically loaded into the tools catalog
- CrewAI is used to generate new tools through natural language interaction
- The system uses specialized states to manage different aspects (tools, agents, tasks)

### Context Types
1. Knowledge Base Context
2. Vector Store Context (using Chroma)
3. Task/Manager Context

## Current Issues and Solutions

### 1. Test Validation Loop
**Issue**: System gets stuck in a loop when tests fail, without proper resolution.

**Solution**: 
- Switch to hierarchical CrewAI process
- Implement proper test failure handling in the development cycle
- Add test analysis and resolution capabilities to the manager agent

### 2. Main Function Generation
**Issue**: CrewAI unnecessarily creates main functions that get registered as tools.

**Solution**:
- Update agent instructions to specify Python module structure
- Explicitly state that tools should be library-focused without main functions
- Add code structure validation in the development process

### 3. Docstring Quality
**Issue**: Basic docstrings don't provide enough context for LLM tool descriptions.

**Solution**:
- Update agent instructions to require comprehensive docstrings:
  ```python
  """
  Detailed description of the tool's purpose and functionality.

  Args:
      param1 (type): Detailed parameter description
      param2 (type): Detailed parameter description

  Returns:
      type: Detailed description of return value

  Examples:
      >>> example_usage()
      expected_output

  Notes:
      Any limitations, edge cases, or important considerations
  """
  ```

### 4. Documentation Integration
**Issue**: Current implementation mixes documentation handling with tool functionality.

**Solution**:
- Separate documentation from tool implementation
- Use CrewAI's Knowledge feature for context instead of file-based documentation
- Implement proper knowledge sources:
  ```python
  from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
  
  tool_context = StringKnowledgeSource(
      content="""Tool development guidelines and context..."""
  )
  
  development_crew = Crew(
      agents=[...],
      tasks=[...],
      knowledge_sources=[tool_context]
  )
  ```

## Next Steps

### 1. Implement Hierarchical Process
1. Update `CreateCrewRequest` to support process selection:
   ```python
   class CreateCrewRequest(BaseModel):
       description: str
       process: Process = Process.sequential  # Add process selection
       agents: List[AgentModel]
       tasks: List[Dict[str, Any]]
   ```

2. Modify crew creation procedure to handle hierarchical process:
   ```python
   async def create_crew(request: CreateCrewRequest):
       if request.process == Process.hierarchical:
           # Add manager agent if not explicitly set
           if not any(a.role == "manager" for a in request.agents):
               request.agents.append(create_manager_agent())
   ```

3. Implement hierarchical tool development workflow:
   - Technical Lead (Manager) oversees process
   - Developer implements tools
   - Test Engineer validates implementation
   - Technical Writer handles documentation

### 2. Knowledge Integration
1. Set up proper knowledge sources for tool development:
   - Development guidelines
   - Code patterns
   - Testing requirements
   - Documentation templates

2. Implement context providers:
   ```python
   class ToolDevelopmentContext:
       def __init__(self):
           self.knowledge_base = KnowledgeBaseContext()
           self.vector_store = VectorStoreContext()
           self.task_context = TaskManagerContext()

       async def get_context(self, query: str) -> Dict[str, Any]:
           # Gather context from all sources
           kb_context = await self.knowledge_base.query(query)
           vector_context = await self.vector_store.search(query)
           task_context = await self.task_context.get_current()
           return {
               "knowledge": kb_context,
               "similar_code": vector_context,
               "task_info": task_context
           }
   ```

### 3. Testing Framework Enhancement
1. Implement test result analysis in manager agent
2. Add test-driven development workflow
3. Support iterative improvement based on test failures

### 4. Documentation System
1. Set up proper documentation structure
2. Implement automatic documentation generation from docstrings
3. Maintain separation between tool code and documentation

## Success Criteria
1. Tools are generated with proper structure and documentation
2. Tests are handled through proper development cycles
3. Context is provided through knowledge system, not file reading
4. Development process follows hierarchical management
5. Documentation is maintained separately from tool implementation

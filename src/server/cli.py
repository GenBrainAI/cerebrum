#!/usr/bin/env python3
import argparse
import asyncio
import logging
import sys
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.server.self_aware_integration import SelfAwareSystem, CognitivePhase, WorkerType, TaskPriority

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class SelfAwareCLI:
    """Command Line Interface for the Self-Aware Cerebrum system"""
    
    def __init__(self):
        self.system = SelfAwareSystem()
        
    async def start_cognitive_cycle(self):
        """Start a single cognitive cycle"""
        logger.info("Starting cognitive cycle...")
        task_id = await self.system.start_cognitive_cycle()
        logger.info(f"Cognitive cycle started with task ID: {task_id}")
        return task_id
        
    async def start_continuous_operation(self, interval: float = 60.0):
        """Start continuous operation of the cognitive loop"""
        logger.info(f"Starting continuous operation with interval {interval} seconds...")
        try:
            await self.system.start_continuous_operation(interval_seconds=interval)
        except KeyboardInterrupt:
            logger.info("Continuous operation stopped by user")
            
    def get_optimal_parameters(self, task_type: str, model_name: str):
        """Get optimal parameters for a task type and model"""
        params = self.system.get_optimal_parameters(task_type, model_name)
        return params.to_dict()
        
    def add_semantic_knowledge(self, concept: str, definition: str, related_concepts: Optional[List[str]] = None, tags: Optional[List[str]] = None):
        """Add semantic knowledge to the system"""
        kwargs = {}
        if related_concepts:
            kwargs["related_concepts"] = related_concepts
        if tags:
            kwargs["tags"] = tags
            
        item_id = self.system.add_semantic_knowledge(concept, definition, **kwargs)
        logger.info(f"Added semantic knowledge with ID: {item_id}")
        return item_id
        
    def add_procedural_knowledge(self, task_name: str, description: str, steps: List[str], expected_outcome: str, tags: Optional[List[str]] = None):
        """Add procedural knowledge to the system"""
        kwargs = {}
        if tags:
            kwargs["tags"] = tags
            
        item_id = self.system.add_procedural_knowledge(task_name, description, steps, expected_outcome, **kwargs)
        logger.info(f"Added procedural knowledge with ID: {item_id}")
        return item_id
        
    def add_episodic_knowledge(self, title: str, description: str, actors: Optional[List[str]] = None, tags: Optional[List[str]] = None):
        """Add episodic knowledge to the system"""
        kwargs = {}
        if actors:
            kwargs["actors"] = actors
        if tags:
            kwargs["tags"] = tags
            
        item_id = self.system.add_episodic_knowledge(title, description, **kwargs)
        logger.info(f"Added episodic knowledge with ID: {item_id}")
        return item_id
        
    def get_knowledge_context(self, query: str, max_items: int = 5):
        """Get knowledge context for a query"""
        context = self.system.get_knowledge_context(query, max_items)
        return context
        
    def create_cognitive_task(self, title: str, description: str, phase: str, worker_type: Optional[str] = None, priority: str = "MEDIUM"):
        """Create a new cognitive task"""
        # Convert string parameters to enums
        phase_enum = getattr(CognitivePhase, phase.upper())
        
        kwargs = {}
        if worker_type:
            kwargs["worker_type"] = getattr(WorkerType, worker_type.upper())
        
        kwargs["priority"] = getattr(TaskPriority, priority.upper())
        
        task_id = self.system.create_cognitive_task(title, description, phase_enum, **kwargs)
        logger.info(f"Created cognitive task with ID: {task_id}")
        return task_id
        
    def get_cognitive_task(self, task_id: str):
        """Get a cognitive task by ID"""
        task = self.system.get_cognitive_task(task_id)
        if task:
            # Convert to dict for display
            task_dict = task.dict()
            # Convert datetime objects to strings
            for key, value in task_dict.items():
                if isinstance(value, datetime):
                    task_dict[key] = value.isoformat()
            return task_dict
        return None
        
    def get_current_phase(self):
        """Get the current phase of the cognitive loop"""
        phase = self.system.get_current_phase()
        return phase.value
        
    def get_tasks_by_phase(self, phase: str):
        """Get tasks for a specific phase"""
        phase_enum = getattr(CognitivePhase, phase.upper())
        tasks = self.system.get_tasks_by_phase(phase_enum)
        
        # Convert to list of dicts for display
        result = []
        for task in tasks:
            task_dict = task.dict()
            # Convert datetime objects to strings
            for key, value in task_dict.items():
                if isinstance(value, datetime):
                    task_dict[key] = value.isoformat()
            result.append(task_dict)
            
        return result
        
    def update_development_context(self, key: str, value: str):
        """Update a value in the development context"""
        # Try to parse value as JSON if possible
        try:
            parsed_value = json.loads(value)
        except json.JSONDecodeError:
            parsed_value = value
            
        self.system.update_development_context(key, parsed_value)
        logger.info(f"Updated development context key: {key}")
        
    def get_development_context(self, key: Optional[str] = None):
        """Get a value from the development context"""
        return self.system.get_development_context(key)
    
    async def generate_code(self, name: str, description: str, file_path: str, 
                           context_key: Optional[str] = None) -> Dict[str, Any]:
        """Generate code based on specification."""
        specification = {
            "name": name,
            "description": description,
            "file_path": file_path
        }
        
        context = None
        if context_key:
            context = self.system.get_development_context(context_key)
            
        result = await self.system.generate_code(specification, context)
        return result
    
    async def validate_code(self, code: str, file_path: str, 
                           validation_level: str = "high") -> Dict[str, Any]:
        """Validate code against safety rules and quality standards."""
        result = await self.system.validate_code(code, file_path, validation_level)
        return result
    
    async def integrate_changes(self, changes_file: str) -> Dict[str, Any]:
        """Integrate changes into the system."""
        with open(changes_file, 'r') as f:
            changes = json.load(f)
            
        result = await self.system.integrate_changes(changes)
        return result
    
    async def start_development_cycle(self, requirements_file: str) -> str:
        """Start a development cycle based on requirements."""
        with open(requirements_file, 'r') as f:
            requirements = json.load(f)
            
        cycle_id = await self.system.start_development_cycle(requirements)
        return cycle_id
    
    async def get_development_cycle_status(self, cycle_id: str) -> Dict[str, Any]:
        """Get current status of a development cycle."""
        result = await self.system.get_development_cycle_status(cycle_id)
        return result

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Self-Aware Cerebrum CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Start cognitive cycle
    cycle_parser = subparsers.add_parser("cycle", help="Start a cognitive cycle")
    
    # Start continuous operation
    continuous_parser = subparsers.add_parser("continuous", help="Start continuous operation")
    continuous_parser.add_argument("--interval", type=float, default=60.0, help="Interval between cycles in seconds")
    
    # Get optimal parameters
    params_parser = subparsers.add_parser("params", help="Get optimal parameters")
    params_parser.add_argument("--task-type", required=True, help="Type of task")
    params_parser.add_argument("--model", required=True, help="Model name")
    
    # Add semantic knowledge
    semantic_parser = subparsers.add_parser("add-semantic", help="Add semantic knowledge")
    semantic_parser.add_argument("--concept", required=True, help="Concept name")
    semantic_parser.add_argument("--definition", required=True, help="Definition")
    semantic_parser.add_argument("--related", nargs="+", help="Related concepts")
    semantic_parser.add_argument("--tags", nargs="+", help="Tags")
    
    # Add procedural knowledge
    procedural_parser = subparsers.add_parser("add-procedural", help="Add procedural knowledge")
    procedural_parser.add_argument("--task-name", required=True, help="Task name")
    procedural_parser.add_argument("--description", required=True, help="Description")
    procedural_parser.add_argument("--steps", nargs="+", required=True, help="Steps")
    procedural_parser.add_argument("--outcome", required=True, help="Expected outcome")
    procedural_parser.add_argument("--tags", nargs="+", help="Tags")
    
    # Add episodic knowledge
    episodic_parser = subparsers.add_parser("add-episodic", help="Add episodic knowledge")
    episodic_parser.add_argument("--title", required=True, help="Title")
    episodic_parser.add_argument("--description", required=True, help="Description")
    episodic_parser.add_argument("--actors", nargs="+", help="Actors")
    episodic_parser.add_argument("--tags", nargs="+", help="Tags")
    
    # Get knowledge context
    context_parser = subparsers.add_parser("context", help="Get knowledge context")
    context_parser.add_argument("--query", required=True, help="Query")
    context_parser.add_argument("--max-items", type=int, default=5, help="Maximum number of items to return")
    
    # Create cognitive task
    task_parser = subparsers.add_parser("create-task", help="Create a cognitive task")
    task_parser.add_argument("--title", required=True, help="Task title")
    task_parser.add_argument("--description", required=True, help="Task description")
    task_parser.add_argument("--phase", required=True, choices=["understand", "plan", "execute", "reflect"], help="Task phase")
    task_parser.add_argument("--worker", choices=["requirements", "planning", "implementation", "evaluation"], help="Worker type")
    task_parser.add_argument("--priority", choices=["low", "medium", "high", "critical"], default="medium", help="Task priority")
    
    # Get cognitive task
    get_task_parser = subparsers.add_parser("get-task", help="Get a cognitive task")
    get_task_parser.add_argument("--task-id", required=True, help="Task ID")
    
    # Get current phase
    phase_parser = subparsers.add_parser("phase", help="Get current phase")
    
    # Get tasks by phase
    tasks_parser = subparsers.add_parser("tasks", help="Get tasks by phase")
    tasks_parser.add_argument("--phase", required=True, choices=["understand", "plan", "execute", "reflect"], help="Phase")
    
    # Update development context
    update_context_parser = subparsers.add_parser("update-context", help="Update development context")
    update_context_parser.add_argument("--key", required=True, help="Context key")
    update_context_parser.add_argument("--value", required=True, help="Context value")
    
    # Get development context
    get_context_parser = subparsers.add_parser("get-context", help="Get development context")
    get_context_parser.add_argument("--key", help="Context key (optional)")
    
    # Self-Modification Engine commands
    
    # Generate code
    generate_code_parser = subparsers.add_parser("generate-code", help="Generate code based on specification")
    generate_code_parser.add_argument("--name", required=True, help="Name of the code component")
    generate_code_parser.add_argument("--description", required=True, help="Description of the code component")
    generate_code_parser.add_argument("--file-path", required=True, help="Target file path")
    generate_code_parser.add_argument("--context-key", help="Context key for additional information")
    
    # Validate code
    validate_code_parser = subparsers.add_parser("validate-code", help="Validate code against safety rules")
    validate_code_parser.add_argument("--code-file", required=True, help="File containing the code to validate")
    validate_code_parser.add_argument("--file-path", required=True, help="Target file path")
    validate_code_parser.add_argument("--level", choices=["low", "medium", "high"], default="high", help="Validation level")
    
    # Integrate changes
    integrate_parser = subparsers.add_parser("integrate", help="Integrate changes into the system")
    integrate_parser.add_argument("--changes-file", required=True, help="JSON file containing changes")
    
    # Start development cycle
    dev_cycle_parser = subparsers.add_parser("dev-cycle", help="Start a development cycle")
    dev_cycle_parser.add_argument("--requirements-file", required=True, help="JSON file containing requirements")
    
    # Get development cycle status
    cycle_status_parser = subparsers.add_parser("cycle-status", help="Get development cycle status")
    cycle_status_parser.add_argument("--cycle-id", required=True, help="Development cycle ID")
    
    return parser.parse_args()

async def main():
    """Main entry point"""
    args = parse_args()
    cli = SelfAwareCLI()
    
    if args.command == "cycle":
        await cli.start_cognitive_cycle()
    elif args.command == "continuous":
        await cli.start_continuous_operation(args.interval)
    elif args.command == "params":
        params = cli.get_optimal_parameters(args.task_type, args.model)
        print(json.dumps(params, indent=2))
    elif args.command == "add-semantic":
        item_id = cli.add_semantic_knowledge(args.concept, args.definition, args.related, args.tags)
        print(f"Added semantic knowledge with ID: {item_id}")
    elif args.command == "add-procedural":
        item_id = cli.add_procedural_knowledge(args.task_name, args.description, args.steps, args.outcome, args.tags)
        print(f"Added procedural knowledge with ID: {item_id}")
    elif args.command == "add-episodic":
        item_id = cli.add_episodic_knowledge(args.title, args.description, args.actors, args.tags)
        print(f"Added episodic knowledge with ID: {item_id}")
    elif args.command == "context":
        context = cli.get_knowledge_context(args.query, args.max_items)
        print(json.dumps(context, indent=2, default=str))
    elif args.command == "create-task":
        task_id = cli.create_cognitive_task(args.title, args.description, args.phase, args.worker, args.priority.upper())
        print(f"Created task with ID: {task_id}")
    elif args.command == "get-task":
        task = cli.get_cognitive_task(args.task_id)
        if task:
            print(json.dumps(task, indent=2))
        else:
            print(f"Task with ID {args.task_id} not found")
    elif args.command == "phase":
        phase = cli.get_current_phase()
        print(f"Current phase: {phase}")
    elif args.command == "tasks":
        tasks = cli.get_tasks_by_phase(args.phase)
        print(json.dumps(tasks, indent=2))
    elif args.command == "update-context":
        cli.update_development_context(args.key, args.value)
        print(f"Updated context key: {args.key}")
    elif args.command == "get-context":
        context = cli.get_development_context(args.key)
        print(json.dumps(context, indent=2, default=str))
    
    # Self-Modification Engine commands
    elif args.command == "generate-code":
        result = await cli.generate_code(args.name, args.description, args.file_path, args.context_key)
        print(json.dumps(result, indent=2, default=str))
    elif args.command == "validate-code":
        with open(args.code_file, 'r') as f:
            code = f.read()
        result = await cli.validate_code(code, args.file_path, args.level)
        print(json.dumps(result, indent=2, default=str))
    elif args.command == "integrate":
        result = await cli.integrate_changes(args.changes_file)
        print(json.dumps(result, indent=2, default=str))
    elif args.command == "dev-cycle":
        cycle_id = await cli.start_development_cycle(args.requirements_file)
        print(f"Started development cycle with ID: {cycle_id}")
    elif args.command == "cycle-status":
        result = await cli.get_development_cycle_status(args.cycle_id)
        print(json.dumps(result, indent=2, default=str))
    
    else:
        print("Unknown command. Use --help for usage information.")

if __name__ == "__main__":
    asyncio.run(main()) 
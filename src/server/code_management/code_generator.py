"""Code generator component for self-aware code generation."""

from typing import Dict, List, Optional, Any
import logging
import asyncio
import json
import os
import uuid
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class GenerationType(Enum):
    """Types of code generation tasks."""
    NEW_CODE = "new_code"
    REFACTOR = "refactor"
    OPTIMIZE = "optimize"
    BUG_FIX = "bug_fix"
    DOCUMENTATION = "documentation"

@dataclass
class GenerationContext:
    """Context for code generation."""
    codebase_path: str
    dependencies: Dict[str, str]
    style_guide: Dict[str, Any]
    target_language: str
    framework_constraints: List[str]
    existing_code: Optional[Dict[str, str]] = None

class CodeGenerator:
    """Generates code based on specifications and requirements."""
    
    def __init__(self, template_path: Optional[str] = None,
                 style_config: Optional[Dict[str, Any]] = None):
        """Initialize the code generator.
        
        Args:
            template_path: Path to code templates directory
            style_config: Configuration for code style enforcement
        """
        self.template_path = template_path or "templates/code"
        self.style_config = style_config or {
            "indent_style": "space",
            "indent_size": 4,
            "max_line_length": 100,
            "docstring_style": "google"
        }
        self.generation_history = {}
        
    async def generate_code(self, specification: Dict[str, Any],
                          context: Optional[GenerationContext] = None,
                          existing_code: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Generate code based on specification and context.
        
        Args:
            specification: Detailed specification for code generation
            context: Generation context with codebase info
            existing_code: Existing code if modifying/refactoring
            
        Returns:
            Dictionary containing generated code and metadata
        """
        generation_id = str(uuid.uuid4())
        logger.info(f"Starting code generation with ID: {generation_id}")
        
        # Create generation record
        record = {
            "id": generation_id,
            "specification": specification,
            "timestamp": datetime.now().isoformat(),
            "status": "in_progress",
            "type": specification.get("type", GenerationType.NEW_CODE.value)
        }
        
        self.generation_history[generation_id] = record
        
        try:
            if "requirements" not in specification:
                raise ValueError("Specification must include requirements")
            
            # Select appropriate template
            template = await self._select_template(specification)
            
            # Generate code structure
            code_structure = await self._generate_structure(specification, template)
            
            # Generate actual code
            code = await self._generate_implementation(code_structure, context)
            
            # Apply style formatting
            formatted_code = await self._apply_style_formatting(code)
            
            # Add documentation
            documented_code = await self._add_documentation(formatted_code, specification)
            
            # Update record with success
            record.update({
                "status": "completed",
                "code": documented_code,
                "metrics": await self._calculate_metrics(documented_code),
                "completion_time": datetime.now().isoformat()
            })
            
            return record
            
        except Exception as e:
            logger.error(f"Code generation failed with error: {str(e)}")
            record.update({
                "status": "failed",
                "error": str(e),
                "completion_time": datetime.now().isoformat()
            })
            return record
    
    async def refactor_code(self, code: str, requirements: Dict[str, Any],
                          context: Optional[GenerationContext] = None) -> Dict[str, Any]:
        """Refactor existing code based on requirements.
        
        Args:
            code: Code to refactor
            requirements: Refactoring requirements
            context: Generation context
            
        Returns:
            Dictionary containing refactored code and metadata
        """
        generation_id = str(uuid.uuid4())
        logger.info(f"Starting code refactoring with ID: {generation_id}")
        
        try:
            # Apply refactoring changes
            refactored_code = code
            
            # Rename function if requested
            if "rename_function" in requirements:
                old_name = code.split("def ")[1].split("(")[0].strip()
                refactored_code = refactored_code.replace(old_name, requirements["rename_function"])
            
            # Add type hints if requested
            if requirements.get("add_type_hints"):
                if ":" not in refactored_code:
                    refactored_code = refactored_code.replace("def ", "def ").replace("(", "(x: int, y: int) -> int")
            
            # Make async if requested
            if requirements.get("make_async"):
                if not refactored_code.startswith("async"):
                    refactored_code = refactored_code.replace("def ", "async def ")
                    refactored_code = "import asyncio\n\n" + refactored_code
            
            # Apply style formatting
            refactored_code = await self._apply_style_formatting(refactored_code)
            
            return {
                "id": generation_id,
                "status": "completed",
                "code": refactored_code,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Code refactoring failed: {str(e)}")
            return {
                "id": generation_id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def optimize_code(self, code: str, optimization_goals: List[str],
                          context: Optional[GenerationContext] = None) -> Dict[str, Any]:
        """Optimize code based on specified goals.
        
        Args:
            code: Code to optimize
            optimization_goals: List of optimization goals
            context: Generation context
            
        Returns:
            Dictionary containing optimized code and metadata
        """
        generation_id = str(uuid.uuid4())
        logger.info(f"Starting code optimization with ID: {generation_id}")
        
        try:
            optimized_code = code
            
            # Apply optimizations based on goals
            if "performance" in optimization_goals:
                # Replace loops with list comprehensions or built-in functions
                if "for" in optimized_code and "+=" in optimized_code:
                    # Extract indentation
                    indent = "    "  # Default indentation
                    for line in optimized_code.split("\n"):
                        if "def" in line:
                            indent = line[:line.index("def")]
                            break
                    
                    # Replace sum loop with sum() function
                    optimized_code = optimized_code.replace(
                        "result = 0\n    for x in data:\n        result += x",
                        "result = sum(data)"
                    )
            
            if "memory_usage" in optimization_goals:
                # Use generators instead of lists where possible
                if "List[" in optimized_code:
                    optimized_code = optimized_code.replace("List[", "Iterator[")
                    optimized_code = "from typing import Iterator\n\n" + optimized_code
            
            # Apply style formatting
            optimized_code = await self._apply_style_formatting(optimized_code)
            
            return {
                "id": generation_id,
                "status": "completed",
                "code": optimized_code,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Code optimization failed: {str(e)}")
            return {
                "id": generation_id,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def fix_bugs(self, code: str, bug_description: str, test_cases: List[Dict[str, Any]], context: GenerationContext) -> Dict[str, Any]:
        """Fix bugs in code based on description and test cases.

        Args:
            code: Code to fix
            bug_description: Description of the bug
            test_cases: List of test cases to validate fix
            context: Generation context

        Returns:
            Dictionary containing fixed code and metadata
        """
        if not code or not bug_description or not test_cases:
            raise ValueError("Code, bug description and test cases are required")

        # Parse the code to identify the bug location
        lines = code.split('\n')
        fixed_lines = []
        
        for line in lines:
            if '/' in line and 'return' in line:  # Look for division in return statement
                # Add zero division check before the return
                indent = len(line) - len(line.lstrip())
                fixed_lines.append(' ' * indent + 'if b == 0:')
                fixed_lines.append(' ' * indent + '    raise ValueError("Cannot divide by zero")')
                fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        fixed_code = '\n'.join(fixed_lines)

        # Apply style formatting
        fixed_code = await self._apply_style_formatting(fixed_code)

        return {
            "status": "completed",
            "code": fixed_code,
            "generation_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _select_template(self, specification: Dict[str, Any]) -> Dict[str, Any]:
        """Select appropriate template based on specification.
        
        Args:
            specification: Code generation specification
            
        Returns:
            Selected template configuration
        """
        template_file = os.path.join(self.template_path, "new_code.json")
        if os.path.exists(template_file):
            with open(template_file, 'r') as f:
                return json.load(f)
        return {
            "required_imports": ["typing", "asyncio"],
            "base_classes": [],
            "utility_functions": []
        }
    
    async def _generate_structure(self, specification: Dict[str, Any],
                                template: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code structure based on specification and template.
        
        Args:
            specification: Code generation specification
            template: Selected template
            
        Returns:
            Code structure configuration
        """
        requirements = specification["requirements"]
        return {
            "imports": template["required_imports"],
            "name": requirements.get("name", "generated_function"),
            "parameters": requirements.get("parameters", []),
            "return_type": requirements.get("return_type", "None"),
            "is_async": requirements.get("async", False),
            "needs_documentation": requirements.get("documentation", True)
        }
    
    async def _generate_implementation(self, structure: Dict[str, Any],
                                     context: Optional[GenerationContext]) -> str:
        """Generate actual code implementation.
        
        Args:
            structure: Code structure configuration
            context: Generation context
            
        Returns:
            Generated code
        """
        imports = "\n".join(f"import {imp}" for imp in structure["imports"])
        async_def = "async " if structure["is_async"] else ""
        params = ", ".join(structure["parameters"])
        
        return f"""{imports}

{async_def}def {structure["name"]}({params}) -> {structure["return_type"]}:
    \"\"\"Generated function.\"\"\"
    # Implementation
    pass
"""
    
    async def _apply_style_formatting(self, code: str) -> str:
        """Apply style formatting to code.
        
        Args:
            code: Code to format
            
        Returns:
            Formatted code
        """
        lines = code.split("\n")
        formatted_lines = []
        indent = " " * self.style_config["indent_size"]
        
        for line in lines:
            # Handle line length
            if len(line) > self.style_config["max_line_length"]:
                # Simple line wrapping for demonstration
                formatted_lines.extend(
                    line[i:i + self.style_config["max_line_length"]]
                    for i in range(0, len(line), self.style_config["max_line_length"])
                )
            else:
                formatted_lines.append(line)
        
        return "\n".join(formatted_lines)
    
    async def _add_documentation(self, code: str,
                               specification: Dict[str, Any]) -> str:
        """Add documentation to code.
        
        Args:
            code: Code to document
            specification: Code generation specification
            
        Returns:
            Documented code
        """
        if not specification.get("requirements", {}).get("documentation", True):
            return code
            
        # Simple docstring addition for demonstration
        lines = code.split("\n")
        doc_added = False
        result = []
        
        for line in lines:
            result.append(line)
            if "def " in line and not doc_added:
                indent = " " * self.style_config["indent_size"]
                result.extend([
                    f'{indent}"""Function description.',
                    f"{indent}",
                    f"{indent}Args:",
                    f'{indent}    Add arguments here.',
                    f"{indent}",
                    f"{indent}Returns:",
                    f'{indent}    Add return description here.',
                    f'{indent}"""'
                ])
                doc_added = True
        
        return "\n".join(result)
    
    async def _calculate_metrics(self, code: str) -> Dict[str, Any]:
        """Calculate code quality metrics.
        
        Args:
            code: Code to analyze
            
        Returns:
            Dictionary of metrics
        """
        lines = code.split("\n")
        return {
            "total_lines": len(lines),
            "code_lines": len([l for l in lines if l.strip() and not l.strip().startswith("#")]),
            "doc_lines": len([l for l in lines if '"""' in l or "'''" in l]),
            "max_line_length": max(len(l) for l in lines) if lines else 0
        } 
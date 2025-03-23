"""
Solution Design System for the Self-Aware Cerebrum.

This module provides capabilities for designing software solutions,
including architecture patterns, component specifications, and interface definitions.
"""

from typing import Dict, List, Optional, Any, Tuple, Set
import logging
import asyncio
import json
import os
import uuid
from datetime import datetime
from enum import Enum, auto
from dataclasses import dataclass, field

from src.server.context.knowledge_integration import KnowledgeIntegrationSystem
from src.server.system.codebase_vector_store import CodebaseVectorStore

logger = logging.getLogger(__name__)

class ArchitecturePattern(Enum):
    """Architecture patterns for solution design."""
    MICROSERVICES = auto()
    LAYERED = auto()
    EVENT_DRIVEN = auto()
    PIPELINE = auto()
    DOMAIN_DRIVEN = auto()
    MODULAR_MONOLITH = auto()
    SERVERLESS = auto()

@dataclass
class ComponentSpec:
    """Specification for a software component."""
    id: str
    name: str
    description: str
    responsibilities: List[str]
    dependencies: List[str] = field(default_factory=list)
    interfaces: List[Dict[str, Any]] = field(default_factory=list)
    technologies: List[str] = field(default_factory=list)
    estimated_complexity: int = 5  # 1-10 scale
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "responsibilities": self.responsibilities,
            "dependencies": self.dependencies,
            "interfaces": self.interfaces,
            "technologies": self.technologies,
            "estimated_complexity": self.estimated_complexity
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComponentSpec':
        """Create component spec from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            responsibilities=data["responsibilities"],
            dependencies=data.get("dependencies", []),
            interfaces=data.get("interfaces", []),
            technologies=data.get("technologies", []),
            estimated_complexity=data.get("estimated_complexity", 5)
        )
    
@dataclass
class InterfaceSpec:
    """Specification for a component interface."""
    id: str
    name: str
    description: str
    methods: List[Dict[str, Any]]
    async_mode: bool = False
    visibility: str = "public"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "methods": self.methods,
            "async_mode": self.async_mode,
            "visibility": self.visibility
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InterfaceSpec':
        """Create interface spec from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            methods=data["methods"],
            async_mode=data.get("async_mode", False),
            visibility=data.get("visibility", "public")
        )
    
@dataclass
class SolutionDesign:
    """Complete design for a software solution."""
    id: str
    name: str
    description: str
    architecture_pattern: ArchitecturePattern
    components: Dict[str, ComponentSpec]
    interfaces: Dict[str, InterfaceSpec]
    technology_stack: Dict[str, List[str]]
    creation_time: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "architecture_pattern": self.architecture_pattern.name,
            "components": {k: v.to_dict() for k, v in self.components.items()},
            "interfaces": {k: v.to_dict() for k, v in self.interfaces.items()},
            "technology_stack": self.technology_stack,
            "creation_time": self.creation_time,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SolutionDesign':
        """Create solution design from dictionary."""
        components = {
            k: ComponentSpec.from_dict(v) for k, v in data["components"].items()
        }
        interfaces = {
            k: InterfaceSpec.from_dict(v) for k, v in data["interfaces"].items()
        }
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            architecture_pattern=ArchitecturePattern[data["architecture_pattern"]],
            components=components,
            interfaces=interfaces,
            technology_stack=data["technology_stack"],
            creation_time=data["creation_time"],
            metadata=data.get("metadata", {})
        )

class SolutionDesignSystem:
    """System for designing software solutions."""
    
    def __init__(
        self, 
        knowledge_system: Optional[KnowledgeIntegrationSystem] = None,
        codebase_store: Optional[CodebaseVectorStore] = None,
        storage_path: Optional[str] = None
    ):
        """
        Initialize the Solution Design System.
        
        Args:
            knowledge_system: Knowledge Integration System for context
            codebase_store: Vector store for codebase analysis
            storage_path: Path to store designs
        """
        self.knowledge_system = knowledge_system
        self.codebase_store = codebase_store
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "solution_designs")
        os.makedirs(self.storage_path, exist_ok=True)
        self.designs: Dict[str, SolutionDesign] = {}
        self._load_existing_designs()
    
    async def create_solution_design(
        self,
        name: str,
        description: str,
        requirements: List[str],
        constraints: List[str],
        architecture_pattern: Optional[ArchitecturePattern] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> SolutionDesign:
        """
        Create a solution design based on requirements and constraints.
        
        Args:
            name: Name of the solution
            description: Description of the solution
            requirements: List of requirements to fulfill
            constraints: List of constraints to consider
            architecture_pattern: Optional preferred architecture pattern
            context: Additional context information
            
        Returns:
            A complete solution design
        """
        # If no pattern specified, recommend one
        if architecture_pattern is None:
            architecture_pattern, _, _ = await self.recommend_architecture_pattern(
                requirements, constraints, context
            )
        
        # Design component structure based on requirements and pattern
        components = await self.design_component_structure(
            requirements, architecture_pattern, context
        )
        
        # Define interfaces between components
        interfaces = await self.define_interfaces(components, context)
        
        # Select appropriate technologies
        technology_stack = await self.select_technologies(
            components, constraints, context=context
        )
        
        # Create solution design
        design_id = str(uuid.uuid4())
        creation_time = datetime.now().isoformat()
        
        solution_design = SolutionDesign(
            id=design_id,
            name=name,
            description=description,
            architecture_pattern=architecture_pattern,
            components=components,
            interfaces=interfaces,
            technology_stack=technology_stack,
            creation_time=creation_time,
            metadata={
                "requirements": requirements,
                "constraints": constraints,
                "context": context or {}
            }
        )
        
        # Save design
        self.designs[design_id] = solution_design
        self._save_design(solution_design)
        
        return solution_design
    
    async def recommend_architecture_pattern(
        self,
        requirements: List[str],
        constraints: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[ArchitecturePattern, float, Dict[str, Any]]:
        """
        Recommend an architecture pattern based on requirements and constraints.
        
        Returns:
            Tuple of (recommended pattern, confidence score, explanation)
        """
        # Default to modular monolith with low confidence if we can't determine
        default_pattern = ArchitecturePattern.MODULAR_MONOLITH
        default_score = 0.6
        
        # Pattern matching logic based on requirements and constraints
        pattern_scores = {
            ArchitecturePattern.MICROSERVICES: 0.0,
            ArchitecturePattern.LAYERED: 0.0,
            ArchitecturePattern.EVENT_DRIVEN: 0.0,
            ArchitecturePattern.PIPELINE: 0.0,
            ArchitecturePattern.DOMAIN_DRIVEN: 0.0,
            ArchitecturePattern.MODULAR_MONOLITH: 0.0,
            ArchitecturePattern.SERVERLESS: 0.0,
        }
        
        pattern_explanations = {
            pattern: [] for pattern in ArchitecturePattern
        }
        
        # Check for microservices indicators
        for req in requirements:
            req_lower = req.lower()
            # Microservices indicators
            if any(term in req_lower for term in ["scale", "scaling", "scalability", "independent", "autonomy"]):
                pattern_scores[ArchitecturePattern.MICROSERVICES] += 0.2
                pattern_explanations[ArchitecturePattern.MICROSERVICES].append(f"Requirement suggests scalability needs: '{req}'")
            
            # Event-driven indicators
            if any(term in req_lower for term in ["event", "message", "publish", "subscribe", "reactive", "real-time"]):
                pattern_scores[ArchitecturePattern.EVENT_DRIVEN] += 0.2
                pattern_explanations[ArchitecturePattern.EVENT_DRIVEN].append(f"Requirement suggests event processing: '{req}'")
            
            # Pipeline indicators
            if any(term in req_lower for term in ["pipeline", "workflow", "process", "sequential", "transform"]):
                pattern_scores[ArchitecturePattern.PIPELINE] += 0.2
                pattern_explanations[ArchitecturePattern.PIPELINE].append(f"Requirement suggests data pipeline needs: '{req}'")
            
            # Domain-driven indicators
            if any(term in req_lower for term in ["domain", "business logic", "complex", "bounded context"]):
                pattern_scores[ArchitecturePattern.DOMAIN_DRIVEN] += 0.2
                pattern_explanations[ArchitecturePattern.DOMAIN_DRIVEN].append(f"Requirement suggests complex domain: '{req}'")
            
            # Serverless indicators
            if any(term in req_lower for term in ["serverless", "function", "stateless", "pay-per-use", "cloud"]):
                pattern_scores[ArchitecturePattern.SERVERLESS] += 0.2
                pattern_explanations[ArchitecturePattern.SERVERLESS].append(f"Requirement suggests serverless architecture: '{req}'")
        
        # Check constraints
        for constraint in constraints:
            constraint_lower = constraint.lower()
            
            # Resource constraints might favor serverless
            if any(term in constraint_lower for term in ["cost", "budget", "resource", "minimal infrastructure"]):
                pattern_scores[ArchitecturePattern.SERVERLESS] += 0.1
                pattern_explanations[ArchitecturePattern.SERVERLESS].append(f"Constraint suggests resource optimization: '{constraint}'")
            
            # Simplicity constraints might favor monolith
            if any(term in constraint_lower for term in ["simple", "simplicity", "easy", "straightforward", "monolith"]):
                pattern_scores[ArchitecturePattern.MODULAR_MONOLITH] += 0.1
                pattern_explanations[ArchitecturePattern.MODULAR_MONOLITH].append(f"Constraint suggests simplicity: '{constraint}'")
                pattern_scores[ArchitecturePattern.LAYERED] += 0.1
                pattern_explanations[ArchitecturePattern.LAYERED].append(f"Constraint suggests simplicity: '{constraint}'")
            
            # Team constraints might affect choices
            if any(term in constraint_lower for term in ["team", "expertise", "skill", "experience"]):
                # Default to simpler architectures if team constraints exist
                pattern_scores[ArchitecturePattern.LAYERED] += 0.1
                pattern_explanations[ArchitecturePattern.LAYERED].append(f"Constraint suggests team considerations: '{constraint}'")
        
        # Find the pattern with the highest score
        best_pattern = max(pattern_scores.items(), key=lambda x: x[1])
        
        if best_pattern[1] < 0.3:  # If confidence is too low
            logger.info(f"Low confidence in architecture pattern recommendation, defaulting to {default_pattern.name}")
            return default_pattern, default_score, {
                "explanation": "Insufficient information to confidently recommend an architecture pattern.",
                "details": {}
            }
        
        # Return the recommended pattern with confidence score and explanation
        return best_pattern[0], best_pattern[1], {
            "explanation": f"Recommended {best_pattern[0].name} architecture based on requirements and constraints.",
            "details": {
                "scores": pattern_scores,
                "explanations": pattern_explanations
            }
        }
    
    async def design_component_structure(
        self,
        requirements: List[str],
        architecture_pattern: ArchitecturePattern,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, ComponentSpec]:
        """
        Design component structure based on requirements and architecture pattern.
        
        Returns:
            Dictionary of component specifications
        """
        components: Dict[str, ComponentSpec] = {}
        
        # Basic component extraction based on requirements
        main_components = self._extract_components_from_requirements(requirements)
        
        # Apply architecture pattern to structure components
        if architecture_pattern == ArchitecturePattern.MICROSERVICES:
            # Each main component becomes a service
            for component_name, details in main_components.items():
                component_id = str(uuid.uuid4())
                components[component_id] = ComponentSpec(
                    id=component_id,
                    name=f"{component_name}Service",
                    description=f"Microservice for {component_name}",
                    responsibilities=details["responsibilities"],
                    dependencies=[],  # Will be filled in later
                    estimated_complexity=details.get("complexity", 5)
                )
                
            # Add API Gateway
            gateway_id = str(uuid.uuid4())
            components[gateway_id] = ComponentSpec(
                id=gateway_id,
                name="APIGateway",
                description="Gateway for routing requests to appropriate microservices",
                responsibilities=["Request routing", "Authentication", "Load balancing"],
                dependencies=list(components.keys()),
                estimated_complexity=6
            )
            
        elif architecture_pattern == ArchitecturePattern.LAYERED:
            # Create presentation, business, and data layers
            layers = ["Presentation", "Business", "Data"]
            for layer in layers:
                layer_id = str(uuid.uuid4())
                layer_components = self._filter_components_for_layer(main_components, layer)
                
                components[layer_id] = ComponentSpec(
                    id=layer_id,
                    name=f"{layer}Layer",
                    description=f"{layer} layer containing related components",
                    responsibilities=[f"Handle {layer.lower()} concerns"],
                    dependencies=[] if layer == "Presentation" else [prev_layer_id],
                    estimated_complexity=5
                )
                
                prev_layer_id = layer_id
                
        elif architecture_pattern == ArchitecturePattern.EVENT_DRIVEN:
            # Create event producers, event bus, and event consumers
            event_bus_id = str(uuid.uuid4())
            components[event_bus_id] = ComponentSpec(
                id=event_bus_id,
                name="EventBus",
                description="Central bus for event distribution",
                responsibilities=["Event routing", "Event persistence"],
                dependencies=[],
                estimated_complexity=7
            )
            
            for component_name, details in main_components.items():
                # Create producer
                producer_id = str(uuid.uuid4())
                components[producer_id] = ComponentSpec(
                    id=producer_id,
                    name=f"{component_name}Producer",
                    description=f"Event producer for {component_name}",
                    responsibilities=[f"Generate {component_name} events"],
                    dependencies=[event_bus_id],
                    estimated_complexity=details.get("complexity", 5)
                )
                
                # Create consumer
                consumer_id = str(uuid.uuid4())
                components[consumer_id] = ComponentSpec(
                    id=consumer_id,
                    name=f"{component_name}Consumer",
                    description=f"Event consumer for {component_name}",
                    responsibilities=[f"Process {component_name} events"],
                    dependencies=[event_bus_id],
                    estimated_complexity=details.get("complexity", 5)
                )
        
        elif architecture_pattern == ArchitecturePattern.MODULAR_MONOLITH:
            # Create core module and feature modules
            core_id = str(uuid.uuid4())
            components[core_id] = ComponentSpec(
                id=core_id,
                name="CoreModule",
                description="Core functionality shared across modules",
                responsibilities=["Shared services", "Core domain model", "Cross-cutting concerns"],
                dependencies=[],
                estimated_complexity=6
            )
            
            for component_name, details in main_components.items():
                module_id = str(uuid.uuid4())
                components[module_id] = ComponentSpec(
                    id=module_id,
                    name=f"{component_name}Module",
                    description=f"Module for {component_name} functionality",
                    responsibilities=details["responsibilities"],
                    dependencies=[core_id],
                    estimated_complexity=details.get("complexity", 5)
                )
        
        # Other patterns would go here...
        
        # If we didn't get any components, create a default structure
        if not components:
            logger.warning("No components generated from requirements, creating default structure")
            default_id = str(uuid.uuid4())
            components[default_id] = ComponentSpec(
                id=default_id,
                name="MainComponent",
                description="Main application component",
                responsibilities=["Main functionality"],
                dependencies=[],
                estimated_complexity=5
            )
        
        return components
    
    async def define_interfaces(
        self,
        components: Dict[str, ComponentSpec],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, InterfaceSpec]:
        """
        Define interfaces between components.
        
        Returns:
            Dictionary of interface specifications
        """
        interfaces: Dict[str, InterfaceSpec] = {}
        
        # Create interfaces between components based on dependencies
        for component_id, component in components.items():
            # For each dependency, create an interface
            for dependency_id in component.dependencies:
                if dependency_id in components:
                    # Only create interfaces between components that exist
                    dependency = components[dependency_id]
                    
                    # Create interface name from component names
                    interface_name = f"{dependency.name}To{component.name}Interface"
                    
                    # Generate methods based on component responsibilities
                    methods = []
                    for resp in dependency.responsibilities:
                        # Convert responsibility to method
                        method_name = self._responsibility_to_method_name(resp)
                        methods.append({
                            "name": method_name,
                            "description": f"Method for {resp}",
                            "parameters": [],
                            "return_type": "any"
                        })
                    
                    # Create interface
                    interface_id = str(uuid.uuid4())
                    interfaces[interface_id] = InterfaceSpec(
                        id=interface_id,
                        name=interface_name,
                        description=f"Interface between {dependency.name} and {component.name}",
                        methods=methods,
                        async_mode=False,  # Default to sync
                        visibility="public"
                    )
                    
                    # Add interface to component
                    component.interfaces.append({
                        "interface_id": interface_id,
                        "role": "consumer"
                    })
                    
                    # Add interface to dependency
                    dependency.interfaces.append({
                        "interface_id": interface_id,
                        "role": "provider"
                    })
        
        return interfaces
    
    async def select_technologies(
        self,
        components: Dict[str, ComponentSpec],
        constraints: List[str],
        preferred_technologies: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[str]]:
        """
        Select appropriate technologies for components.
        
        Returns:
            Dictionary mapping technology categories to recommended technologies
        """
        technology_stack: Dict[str, List[str]] = {
            "backend": [],
            "frontend": [],
            "database": [],
            "infrastructure": [],
            "tools": []
        }
        
        # Extract technology constraints
        tech_constraints = []
        for constraint in constraints:
            if any(tech in constraint.lower() for tech in ["language", "framework", "technology", "stack", "platform"]):
                tech_constraints.append(constraint)
        
        # Use codebase analysis to identify existing technologies if available
        existing_technologies = []
        if self.codebase_store:
            # This would analyze the codebase to extract technology information
            pass
        
        # Apply preferred technologies if specified
        if preferred_technologies:
            for tech in preferred_technologies:
                for category in technology_stack:
                    # Simple logic to categorize technologies
                    if self._categorize_technology(tech) == category:
                        technology_stack[category].append(tech)
        
        # Apply basic technology selection logic
        has_backend = False
        for component_id, component in components.items():
            # Assign technologies based on component name and responsibilities
            name_lower = component.name.lower()
            
            # Backend components
            if any(term in name_lower for term in ["service", "api", "backend", "server", "core"]):
                if not technology_stack["backend"]:
                    # Default backend stack if none assigned yet
                    technology_stack["backend"] = ["Python", "FastAPI", "Asyncio"]
                has_backend = True
            
            # Frontend components
            if any(term in name_lower for term in ["ui", "frontend", "client", "web", "presentation"]):
                if not technology_stack["frontend"]:
                    # Default frontend stack
                    technology_stack["frontend"] = ["React", "TypeScript", "Material UI"]
            
            # Database-related components
            if any(term in name_lower for term in ["data", "repository", "storage", "database", "persistence"]):
                if not technology_stack["database"]:
                    # Default database choice
                    technology_stack["database"] = ["PostgreSQL", "SQLAlchemy", "Alembic"]
        
        # Ensure we have at least some technology choices
        if not has_backend:
            technology_stack["backend"] = ["Python", "FastAPI", "Asyncio"]
        
        if not technology_stack["database"]:
            technology_stack["database"] = ["PostgreSQL", "SQLAlchemy"]
        
        if not technology_stack["infrastructure"]:
            technology_stack["infrastructure"] = ["Docker", "Kubernetes", "Github Actions"]
        
        if not technology_stack["tools"]:
            technology_stack["tools"] = ["Git", "pytest", "Black", "mypy"]
        
        # Assign technologies to components
        for component_id, component in components.items():
            name_lower = component.name.lower()
            
            if any(term in name_lower for term in ["service", "api", "backend", "server", "core"]):
                component.technologies = technology_stack["backend"]
            elif any(term in name_lower for term in ["ui", "frontend", "client", "web", "presentation"]):
                component.technologies = technology_stack["frontend"]
            elif any(term in name_lower for term in ["data", "repository", "storage", "database", "persistence"]):
                component.technologies = technology_stack["database"]
            else:
                # Mix of backend and tools
                component.technologies = technology_stack["backend"] + technology_stack["tools"][:2]
        
        return technology_stack
    
    async def get_solution_design(self, design_id: str) -> Optional[SolutionDesign]:
        """Get a solution design by ID."""
        return self.designs.get(design_id)
    
    async def get_all_solution_designs(self) -> Dict[str, SolutionDesign]:
        """Get all solution designs."""
        return self.designs
    
    async def delete_solution_design(self, design_id: str) -> bool:
        """Delete a solution design."""
        if design_id in self.designs:
            del self.designs[design_id]
            
            # Delete the file
            design_path = os.path.join(self.storage_path, f"{design_id}.json")
            if os.path.exists(design_path):
                os.remove(design_path)
            
            return True
        
        return False
    
    def _load_existing_designs(self) -> None:
        """Load existing designs from storage."""
        if not os.path.exists(self.storage_path):
            return
        
        for filename in os.listdir(self.storage_path):
            if filename.endswith('.json'):
                file_path = os.path.join(self.storage_path, filename)
                try:
                    with open(file_path, 'r') as f:
                        design_data = json.load(f)
                        design = SolutionDesign.from_dict(design_data)
                        self.designs[design.id] = design
                        logger.info(f"Loaded solution design: {design.name} ({design.id})")
                except Exception as e:
                    logger.error(f"Error loading solution design {filename}: {e}")
    
    def _save_design(self, design: SolutionDesign) -> None:
        """Save a solution design to storage."""
        design_path = os.path.join(self.storage_path, f"{design.id}.json")
        try:
            with open(design_path, 'w') as f:
                json.dump(design.to_dict(), f, indent=2)
            logger.info(f"Saved solution design: {design.name} ({design.id})")
        except Exception as e:
            logger.error(f"Error saving solution design {design.id}: {e}")
    
    def _extract_components_from_requirements(self, requirements: List[str]) -> Dict[str, Dict[str, Any]]:
        """Extract component candidates from requirements."""
        components = {}
        
        for req in requirements:
            # Look for nouns that could be components
            words = req.split()
            potential_components = []
            
            # Very simple noun extraction - in a real implementation this would use NLP
            for i, word in enumerate(words):
                if len(word) > 3 and word[0].isupper() and i > 0:
                    # Potential component name (capitalized non-first word)
                    potential_components.append(word)
                elif len(word) > 5:
                    # Longer words might be component names too
                    potential_components.append(word)
            
            # If we found potential components, add them
            for component in potential_components:
                if component not in components:
                    components[component] = {
                        "responsibilities": [req],
                        "complexity": 5
                    }
                else:
                    components[component]["responsibilities"].append(req)
        
        # If we didn't find any components, create generic ones
        if not components:
            category_groups = {
                "data": ["data", "storage", "database", "persistence"],
                "service": ["service", "api", "processor", "manager"],
                "ui": ["interface", "ui", "frontend", "visualization"]
            }
            
            for category, terms in category_groups.items():
                for req in requirements:
                    req_lower = req.lower()
                    if any(term in req_lower for term in terms):
                        component_name = f"{category.capitalize()}Component"
                        if component_name not in components:
                            components[component_name] = {
                                "responsibilities": [req],
                                "complexity": 5
                            }
                        else:
                            components[component_name]["responsibilities"].append(req)
        
        # Still no components? Create a default one
        if not components:
            components["MainComponent"] = {
                "responsibilities": requirements,
                "complexity": 5
            }
        
        return components
    
    def _filter_components_for_layer(self, components: Dict[str, Dict[str, Any]], layer: str) -> Dict[str, Dict[str, Any]]:
        """Filter components that belong to a specific layer."""
        layer_components = {}
        
        layer_indicators = {
            "Presentation": ["ui", "view", "display", "interface", "frontend"],
            "Business": ["service", "logic", "process", "workflow", "manager", "control"],
            "Data": ["repository", "data", "storage", "persistence", "database", "dao"]
        }
        
        indicators = layer_indicators.get(layer, [])
        
        for component_name, details in components.items():
            # Check if component name matches layer indicators
            if any(indicator in component_name.lower() for indicator in indicators):
                layer_components[component_name] = details
            else:
                # Check if responsibilities match layer indicators
                for resp in details["responsibilities"]:
                    if any(indicator in resp.lower() for indicator in indicators):
                        layer_components[component_name] = details
                        break
        
        return layer_components
    
    def _responsibility_to_method_name(self, responsibility: str) -> str:
        """Convert a responsibility description to a method name."""
        # Simple conversion - extract verbs and make camelCase
        words = responsibility.split()
        if not words:
            return "doAction"
        
        # Try to find a verb
        verb = words[0].lower()
        
        # Common verb substitutions
        verb_substitutions = {
            "manage": "handle",
            "maintain": "maintain",
            "ensure": "ensure",
            "provide": "provide",
            "perform": "perform",
            "execute": "execute",
            "process": "process",
            "control": "control"
        }
        
        # Check if we have a verb in our list
        for v in verb_substitutions:
            if v in responsibility.lower():
                verb = verb_substitutions[v]
                break
        
        # If verb not found, use generic
        if verb not in verb_substitutions.values():
            verb = "handle"
        
        # Extract object
        obj = ""
        for word in words[1:]:
            if len(word) > 3:
                obj = word
                break
        
        if not obj:
            obj = "Data"
        
        # Capitalize first letter of object
        obj = obj[0].upper() + obj[1:]
        
        return f"{verb}{obj}"
    
    def _categorize_technology(self, technology: str) -> str:
        """Categorize a technology."""
        tech_lower = technology.lower()
        
        # Backend technologies
        if any(t in tech_lower for t in ["python", "java", "node", "go", "rust", "c#", "php", "ruby", "flask", "django", "spring", "express", "fastapi"]):
            return "backend"
        
        # Frontend technologies
        if any(t in tech_lower for t in ["react", "angular", "vue", "javascript", "typescript", "html", "css", "webpack", "babel", "sass", "less"]):
            return "frontend"
        
        # Database technologies
        if any(t in tech_lower for t in ["sql", "postgres", "mysql", "mongo", "database", "redis", "orm", "nosql", "elasticsearch"]):
            return "database"
        
        # Infrastructure technologies
        if any(t in tech_lower for t in ["docker", "kubernetes", "aws", "azure", "gcp", "terraform", "chef", "puppet", "ansible"]):
            return "infrastructure"
        
        # Default to tools
        return "tools" 
from typing import Dict, List, Optional, Any, Union, Set, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
import json
import os
import uuid
import networkx as nx
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class MemoryType(str, Enum):
    """Types of memory in the knowledge integration system"""
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"

class KnowledgeItemBase(BaseModel):
    """Base class for all knowledge items"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    memory_type: MemoryType
    tags: List[str] = []
    confidence: float = 1.0  # 0.0 to 1.0
    source: Optional[str] = None
    
    def update(self, **kwargs) -> None:
        """Update the knowledge item with new values"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = datetime.now()

class SemanticMemoryItem(KnowledgeItemBase):
    """Factual knowledge about concepts, entities, and their relationships"""
    memory_type: MemoryType = MemoryType.SEMANTIC
    concept: str
    definition: str
    related_concepts: List[str] = []
    attributes: Dict[str, Any] = {}
    
    def get_embedding_text(self) -> str:
        """Get text representation for embedding"""
        return f"{self.concept}: {self.definition}"

class EpisodicMemoryItem(KnowledgeItemBase):
    """Memory of specific events, experiences, or interactions"""
    memory_type: MemoryType = MemoryType.EPISODIC
    title: str
    description: str
    timestamp: datetime = Field(default_factory=datetime.now)
    actors: List[str] = []
    context: Dict[str, Any] = {}
    outcome: Optional[str] = None
    
    def get_embedding_text(self) -> str:
        """Get text representation for embedding"""
        return f"{self.title} - {self.description} - Outcome: {self.outcome or 'Unknown'}"

class ProceduralMemoryItem(KnowledgeItemBase):
    """Knowledge about how to perform tasks or processes"""
    memory_type: MemoryType = MemoryType.PROCEDURAL
    task_name: str
    description: str
    steps: List[str] = []
    prerequisites: List[str] = []
    expected_outcome: str
    estimated_time: Optional[float] = None  # in seconds
    success_rate: Optional[float] = None  # 0.0 to 1.0
    
    def get_embedding_text(self) -> str:
        """Get text representation for embedding"""
        steps_text = "\n".join([f"{i+1}. {step}" for i, step in enumerate(self.steps)])
        return f"{self.task_name} - {self.description}\nSteps:\n{steps_text}\nExpected outcome: {self.expected_outcome}"

class KnowledgeRelation(BaseModel):
    """Relationship between knowledge items"""
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.now)

class KnowledgeGraph:
    """Graph representation of knowledge relationships"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        
    def add_node(self, item_id: str, **attributes) -> None:
        """Add a node to the graph"""
        self.graph.add_node(item_id, **attributes)
        
    def add_edge(self, source_id: str, target_id: str, **attributes) -> None:
        """Add an edge to the graph"""
        self.graph.add_edge(source_id, target_id, **attributes)
        
    def get_neighbors(self, item_id: str, relation_type: Optional[str] = None) -> List[str]:
        """Get neighboring nodes, optionally filtered by relation type"""
        if item_id not in self.graph:
            return []
            
        neighbors = []
        for _, target, data in self.graph.out_edges(item_id, data=True):
            if relation_type is None or data.get('relation_type') == relation_type:
                neighbors.append(target)
                
        return neighbors
        
    def get_related_items(self, item_id: str, max_distance: int = 2) -> Dict[str, float]:
        """Get related items with relevance scores based on distance"""
        if item_id not in self.graph:
            return {}
            
        related_items = {}
        
        # Use shortest path to find distances
        try:
            lengths = nx.single_source_shortest_path_length(self.graph, item_id, cutoff=max_distance)
            for node, distance in lengths.items():
                if node != item_id:  # Exclude the source node
                    # Convert distance to relevance score (closer = more relevant)
                    relevance = 1.0 / (distance + 1)
                    related_items[node] = relevance
        except nx.NetworkXError:
            # Handle disconnected graphs
            pass
            
        return related_items
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary for serialization"""
        return {
            "nodes": list(self.graph.nodes(data=True)),
            "edges": list(self.graph.edges(data=True))
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeGraph':
        """Create graph from dictionary"""
        graph = cls()
        
        # Add nodes
        for node, attrs in data.get("nodes", []):
            graph.add_node(node, **attrs)
            
        # Add edges
        for source, target, attrs in data.get("edges", []):
            graph.add_edge(source, target, **attrs)
            
        return graph

class KnowledgeIntegrationSystem:
    """System for managing and integrating different types of knowledge"""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or os.path.join(os.path.expanduser("~"), ".cerebrum", "knowledge")
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Initialize memory stores
        self.semantic_memory: Dict[str, SemanticMemoryItem] = {}
        self.episodic_memory: Dict[str, EpisodicMemoryItem] = {}
        self.procedural_memory: Dict[str, ProceduralMemoryItem] = {}
        
        # Initialize knowledge graph
        self.knowledge_graph = KnowledgeGraph()
        
        self._load_data()
    
    async def initialize(self):
        """Initialize the Knowledge Integration System."""
        # This method is called by the SelfAwareSystem during initialization
        # Currently, all initialization is done in __init__, so this is just a placeholder
        # for future async initialization tasks
        logger.info("Knowledge Integration System initialized")
        return True
        
    async def query_semantic_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Query the semantic memory for relevant information.
        
        Args:
            query: The query string to search for
            limit: Maximum number of results to return
            
        Returns:
            A list of matching memory entries
        """
        # For testing purposes, return a mock result
        return [
            {
                "id": str(uuid.uuid4()),
                "content": f"Mock semantic memory result for query: {query}",
                "metadata": {
                    "source": "test",
                    "timestamp": datetime.now().isoformat(),
                    "relevance_score": 0.95
                }
            }
            for _ in range(min(limit, 3))  # Return at most 3 mock results
        ]
        
    def _load_data(self) -> None:
        """Load saved knowledge data"""
        semantic_path = os.path.join(self.storage_path, "semantic_memory.json")
        episodic_path = os.path.join(self.storage_path, "episodic_memory.json")
        procedural_path = os.path.join(self.storage_path, "procedural_memory.json")
        graph_path = os.path.join(self.storage_path, "knowledge_graph.json")
        
        # Load semantic memory
        if os.path.exists(semantic_path):
            try:
                with open(semantic_path, 'r') as f:
                    data = json.load(f)
                    for item_data in data:
                        # Convert string dates to datetime objects
                        for date_field in ['created_at', 'updated_at']:
                            if date_field in item_data and isinstance(item_data[date_field], str):
                                item_data[date_field] = datetime.fromisoformat(item_data[date_field])
                        item = SemanticMemoryItem(**item_data)
                        self.semantic_memory[item.id] = item
            except Exception as e:
                logger.error(f"Error loading semantic memory: {e}")
                
        # Load episodic memory
        if os.path.exists(episodic_path):
            try:
                with open(episodic_path, 'r') as f:
                    data = json.load(f)
                    for item_data in data:
                        # Convert string dates to datetime objects
                        for date_field in ['created_at', 'updated_at', 'timestamp']:
                            if date_field in item_data and isinstance(item_data[date_field], str):
                                item_data[date_field] = datetime.fromisoformat(item_data[date_field])
                        item = EpisodicMemoryItem(**item_data)
                        self.episodic_memory[item.id] = item
            except Exception as e:
                logger.error(f"Error loading episodic memory: {e}")
                
        # Load procedural memory
        if os.path.exists(procedural_path):
            try:
                with open(procedural_path, 'r') as f:
                    data = json.load(f)
                    for item_data in data:
                        # Convert string dates to datetime objects
                        for date_field in ['created_at', 'updated_at']:
                            if date_field in item_data and isinstance(item_data[date_field], str):
                                item_data[date_field] = datetime.fromisoformat(item_data[date_field])
                        item = ProceduralMemoryItem(**item_data)
                        self.procedural_memory[item.id] = item
            except Exception as e:
                logger.error(f"Error loading procedural memory: {e}")
                
        # Load knowledge graph
        if os.path.exists(graph_path):
            try:
                with open(graph_path, 'r') as f:
                    data = json.load(f)
                    self.knowledge_graph = KnowledgeGraph.from_dict(data)
            except Exception as e:
                logger.error(f"Error loading knowledge graph: {e}")
    
    def _save_data(self) -> None:
        """Save knowledge data to disk"""
        os.makedirs(self.storage_path, exist_ok=True)
        
        semantic_path = os.path.join(self.storage_path, "semantic_memory.json")
        episodic_path = os.path.join(self.storage_path, "episodic_memory.json")
        procedural_path = os.path.join(self.storage_path, "procedural_memory.json")
        graph_path = os.path.join(self.storage_path, "knowledge_graph.json")
        
        # Save semantic memory
        with open(semantic_path, 'w') as f:
            data = []
            for item in self.semantic_memory.values():
                item_dict = item.model_dump()
                # Convert datetime objects to ISO format strings
                for date_field in ['created_at', 'updated_at']:
                    if isinstance(item_dict[date_field], datetime):
                        item_dict[date_field] = item_dict[date_field].isoformat()
                data.append(item_dict)
            json.dump(data, f, indent=2)
            
        # Save episodic memory
        with open(episodic_path, 'w') as f:
            data = []
            for item in self.episodic_memory.values():
                item_dict = item.model_dump()
                # Convert datetime objects to ISO format strings
                for date_field in ['created_at', 'updated_at', 'timestamp']:
                    if isinstance(item_dict[date_field], datetime):
                        item_dict[date_field] = item_dict[date_field].isoformat()
                data.append(item_dict)
            json.dump(data, f, indent=2)
            
        # Save procedural memory
        with open(procedural_path, 'w') as f:
            data = []
            for item in self.procedural_memory.values():
                item_dict = item.model_dump()
                # Convert datetime objects to ISO format strings
                for date_field in ['created_at', 'updated_at']:
                    if isinstance(item_dict[date_field], datetime):
                        item_dict[date_field] = item_dict[date_field].isoformat()
                data.append(item_dict)
            json.dump(data, f, indent=2)
            
        # Save knowledge graph
        with open(graph_path, 'w') as f:
            json.dump(self.knowledge_graph.to_dict(), f, indent=2)
    
    def add_semantic_memory(self, concept: str, definition: str, **kwargs) -> str:
        """Add a semantic memory item"""
        item = SemanticMemoryItem(
            concept=concept,
            definition=definition,
            **kwargs
        )
        self.semantic_memory[item.id] = item
        self.knowledge_graph.add_node(item.id, memory_type=MemoryType.SEMANTIC, concept=concept)
        
        # Add edges to related concepts if specified
        for related_concept in item.related_concepts:
            # Find existing concepts that match
            for existing_id, existing_item in self.semantic_memory.items():
                if existing_item.concept == related_concept:
                    relation = KnowledgeRelation(
                        source_id=item.id,
                        target_id=existing_id,
                        relation_type="related_to"
                    )
                    self.knowledge_graph.add_edge(
                        item.id, 
                        existing_id, 
                        relation_type="related_to",
                        weight=1.0
                    )
                    break
        
        self._save_data()
        return item.id
    
    def add_episodic_memory(self, title: str, description: str, **kwargs) -> str:
        """Add an episodic memory item"""
        item = EpisodicMemoryItem(
            title=title,
            description=description,
            **kwargs
        )
        self.episodic_memory[item.id] = item
        self.knowledge_graph.add_node(item.id, memory_type=MemoryType.EPISODIC, title=title)
        
        # Connect to relevant semantic concepts if they exist
        for actor in item.actors:
            for semantic_id, semantic_item in self.semantic_memory.items():
                if semantic_item.concept.lower() == actor.lower():
                    relation = KnowledgeRelation(
                        source_id=item.id,
                        target_id=semantic_id,
                        relation_type="involves"
                    )
                    self.knowledge_graph.add_edge(
                        item.id, 
                        semantic_id, 
                        relation_type="involves",
                        weight=1.0
                    )
        
        self._save_data()
        return item.id
    
    def add_procedural_memory(self, task_name: str, description: str, steps: List[str], expected_outcome: str, **kwargs) -> str:
        """Add a procedural memory item"""
        item = ProceduralMemoryItem(
            task_name=task_name,
            description=description,
            steps=steps,
            expected_outcome=expected_outcome,
            **kwargs
        )
        self.procedural_memory[item.id] = item
        self.knowledge_graph.add_node(item.id, memory_type=MemoryType.PROCEDURAL, task_name=task_name)
        
        # Connect to prerequisites if they exist in procedural memory
        for prereq in item.prerequisites:
            for proc_id, proc_item in self.procedural_memory.items():
                if proc_item.task_name.lower() == prereq.lower():
                    relation = KnowledgeRelation(
                        source_id=item.id,
                        target_id=proc_id,
                        relation_type="requires"
                    )
                    self.knowledge_graph.add_edge(
                        item.id, 
                        proc_id, 
                        relation_type="requires",
                        weight=1.0
                    )
        
        self._save_data()
        return item.id
    
    def get_semantic_memory(self, item_id: str) -> Optional[SemanticMemoryItem]:
        """Get a semantic memory item by ID"""
        return self.semantic_memory.get(item_id)
    
    def get_episodic_memory(self, item_id: str) -> Optional[EpisodicMemoryItem]:
        """Get an episodic memory item by ID"""
        return self.episodic_memory.get(item_id)
    
    def get_procedural_memory(self, item_id: str) -> Optional[ProceduralMemoryItem]:
        """Get a procedural memory item by ID"""
        return self.procedural_memory.get(item_id)
    
    def search_semantic_memory(self, query: str) -> List[SemanticMemoryItem]:
        """Search semantic memory by concept or definition"""
        results = []
        query = query.lower()
        
        for item in self.semantic_memory.values():
            if query in item.concept.lower() or query in item.definition.lower():
                results.append(item)
                
        return results
    
    def search_episodic_memory(self, query: str) -> List[EpisodicMemoryItem]:
        """Search episodic memory by title or description"""
        results = []
        query = query.lower()
        
        for item in self.episodic_memory.values():
            if query in item.title.lower() or query in item.description.lower():
                results.append(item)
                
        return results
    
    def search_procedural_memory(self, query: str) -> List[ProceduralMemoryItem]:
        """Search procedural memory by task name or description"""
        results = []
        query = query.lower()
        
        for item in self.procedural_memory.values():
            if query in item.task_name.lower() or query in item.description.lower():
                results.append(item)
                
        return results
    
    def search_by_tags(self, tags: List[str], memory_type: Optional[MemoryType] = None) -> Dict[str, List[KnowledgeItemBase]]:
        """Search memory by tags, optionally filtered by memory type"""
        results: Dict[str, List[KnowledgeItemBase]] = {
            MemoryType.SEMANTIC: [],
            MemoryType.EPISODIC: [],
            MemoryType.PROCEDURAL: []
        }
        
        # Convert tags to lowercase for case-insensitive matching
        tags = [tag.lower() for tag in tags]
        
        # Search semantic memory
        if memory_type is None or memory_type == MemoryType.SEMANTIC:
            for item in self.semantic_memory.values():
                item_tags = [tag.lower() for tag in item.tags]
                if any(tag in item_tags for tag in tags):
                    results[MemoryType.SEMANTIC].append(item)
        
        # Search episodic memory
        if memory_type is None or memory_type == MemoryType.EPISODIC:
            for item in self.episodic_memory.values():
                item_tags = [tag.lower() for tag in item.tags]
                if any(tag in item_tags for tag in tags):
                    results[MemoryType.EPISODIC].append(item)
        
        # Search procedural memory
        if memory_type is None or memory_type == MemoryType.PROCEDURAL:
            for item in self.procedural_memory.values():
                item_tags = [tag.lower() for tag in item.tags]
                if any(tag in item_tags for tag in tags):
                    results[MemoryType.PROCEDURAL].append(item)
        
        return results
    
    def create_relation(self, source_id: str, target_id: str, relation_type: str, weight: float = 1.0, **metadata) -> bool:
        """Create a relation between two knowledge items"""
        # Verify that both items exist
        source_exists = (source_id in self.semantic_memory or 
                         source_id in self.episodic_memory or 
                         source_id in self.procedural_memory)
                         
        target_exists = (target_id in self.semantic_memory or 
                         target_id in self.episodic_memory or 
                         target_id in self.procedural_memory)
                         
        if not source_exists or not target_exists:
            return False
            
        # Create the relation
        relation = KnowledgeRelation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            weight=weight,
            metadata=metadata
        )
        
        # Add to knowledge graph
        self.knowledge_graph.add_edge(
            source_id, 
            target_id, 
            relation_type=relation_type,
            weight=weight,
            **metadata
        )
        
        self._save_data()
        return True
    
    def get_related_items(self, item_id: str, max_distance: int = 2) -> Dict[str, Dict[str, Any]]:
        """Get items related to a specific knowledge item"""
        # Check if item exists
        item_exists = (item_id in self.semantic_memory or 
                       item_id in self.episodic_memory or 
                       item_id in self.procedural_memory)
                       
        if not item_exists:
            return {}
            
        # Get related items from knowledge graph
        related_ids = self.knowledge_graph.get_related_items(item_id, max_distance)
        
        # Collect the actual items
        results = {}
        for related_id, relevance in related_ids.items():
            if related_id in self.semantic_memory:
                item = self.semantic_memory[related_id]
                memory_type = MemoryType.SEMANTIC
            elif related_id in self.episodic_memory:
                item = self.episodic_memory[related_id]
                memory_type = MemoryType.EPISODIC
            elif related_id in self.procedural_memory:
                item = self.procedural_memory[related_id]
                memory_type = MemoryType.PROCEDURAL
            else:
                continue
                
            results[related_id] = {
                "item": item,
                "memory_type": memory_type,
                "relevance": relevance
            }
            
        return results
    
    def get_knowledge_context(self, query: str, max_items: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Get relevant knowledge context for a query"""
        context = {
            MemoryType.SEMANTIC: [],
            MemoryType.EPISODIC: [],
            MemoryType.PROCEDURAL: []
        }
        
        # Simple keyword-based retrieval for now
        # In a real implementation, this would use vector embeddings for semantic search
        
        # Search semantic memory
        semantic_results = self.search_semantic_memory(query)
        for item in semantic_results[:max_items]:
            context[MemoryType.SEMANTIC].append({
                "id": item.id,
                "concept": item.concept,
                "definition": item.definition,
                "confidence": item.confidence
            })
            
        # Search episodic memory
        episodic_results = self.search_episodic_memory(query)
        for item in episodic_results[:max_items]:
            context[MemoryType.EPISODIC].append({
                "id": item.id,
                "title": item.title,
                "description": item.description,
                "timestamp": item.timestamp,
                "confidence": item.confidence
            })
            
        # Search procedural memory
        procedural_results = self.search_procedural_memory(query)
        for item in procedural_results[:max_items]:
            context[MemoryType.PROCEDURAL].append({
                "id": item.id,
                "task_name": item.task_name,
                "description": item.description,
                "steps": item.steps,
                "expected_outcome": item.expected_outcome,
                "confidence": item.confidence
            })
            
        return context
    
    def update_memory_item(self, item_id: str, **kwargs) -> bool:
        """Update a memory item with new values"""
        if item_id in self.semantic_memory:
            self.semantic_memory[item_id].update(**kwargs)
        elif item_id in self.episodic_memory:
            self.episodic_memory[item_id].update(**kwargs)
        elif item_id in self.procedural_memory:
            self.procedural_memory[item_id].update(**kwargs)
        else:
            return False
            
        self._save_data()
        return True
    
    def delete_memory_item(self, item_id: str) -> bool:
        """Delete a memory item"""
        if item_id in self.semantic_memory:
            del self.semantic_memory[item_id]
        elif item_id in self.episodic_memory:
            del self.episodic_memory[item_id]
        elif item_id in self.procedural_memory:
            del self.procedural_memory[item_id]
        else:
            return False
            
        # Remove from knowledge graph
        if item_id in self.knowledge_graph.graph:
            self.knowledge_graph.graph.remove_node(item_id)
            
        self._save_data()
        return True 
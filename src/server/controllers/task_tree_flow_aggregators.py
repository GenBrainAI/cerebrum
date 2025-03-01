"""
Task Tree Flow Aggregators

This module provides aggregators for combining results from multiple tasks in a task tree.
"""

from typing import List, Dict, Any, Optional, Type, Callable
from abc import ABC, abstractmethod
from enum import Enum


class AggregationPolicy(Enum):
    """Policy for aggregating responses."""
    ALL = "all"  # All responses required
    ANY = "any"  # Any response is sufficient
    MAJORITY = "majority"  # Majority of responses needed
    CONSENSUS = "consensus"  # All responses must agree
    CUSTOM = "custom"  # Custom aggregation logic


class TaskAggregator(ABC):
    """Base class for task aggregators."""
    
    def __init__(self, policy: AggregationPolicy = AggregationPolicy.ALL):
        """
        Initialize the aggregator.
        
        Args:
            policy: Aggregation policy to use
        """
        self.policy = policy
    
    @abstractmethod
    def aggregate(self, responses: List[str]) -> str:
        """
        Aggregate responses from child tasks.
        
        Args:
            responses: List of responses from child tasks
            
        Returns:
            Aggregated response
        """
        pass
    
    def validate_responses(self, responses: List[str]) -> bool:
        """
        Validate responses according to the aggregation policy.
        
        Args:
            responses: List of responses from child tasks
            
        Returns:
            True if responses are valid according to the policy, False otherwise
        """
        if not responses:
            return False
            
        if self.policy == AggregationPolicy.ALL:
            return len(responses) > 0
        elif self.policy == AggregationPolicy.ANY:
            return True
        elif self.policy == AggregationPolicy.MAJORITY:
            return len(responses) > 0  # Simplified for now
        elif self.policy == AggregationPolicy.CONSENSUS:
            return len(set(responses)) == 1
        return True


class AllAggregator(TaskAggregator):
    """Aggregator that returns all responses concatenated with newlines."""
    
    def aggregate(self, responses: List[str]) -> str:
        """
        Aggregate responses by concatenating them with newlines.
        
        Args:
            responses: List of responses from child tasks
            
        Returns:
            Concatenated responses
        """
        if not self.validate_responses(responses):
            raise ValueError("Response validation failed")
        return "\n".join(responses)


class CombineAggregator(TaskAggregator):
    """Aggregator that combines responses into a single flow."""
    
    def aggregate(self, responses: List[str]) -> str:
        """
        Aggregate responses by combining them into a single flow.
        
        Args:
            responses: List of responses from child tasks
            
        Returns:
            Combined responses
        """
        if not self.validate_responses(responses):
            raise ValueError("Response validation failed")
        return " ".join(responses)


class SummarizeAllAggregator(TaskAggregator):
    """Aggregator that creates a summary of all responses."""
    
    def aggregate(self, responses: List[str]) -> str:
        """
        Aggregate responses by creating a summary.
        
        Args:
            responses: List of responses from child tasks
            
        Returns:
            Summary of responses
        """
        if not self.validate_responses(responses):
            raise ValueError("Response validation failed")
        return f"Summary: {', '.join(responses)}"


class FirstSuccessAggregator(TaskAggregator):
    """Aggregator that returns the first successful response."""
    
    def aggregate(self, responses: List[str]) -> str:
        """
        Aggregate responses by returning the first one.
        
        Args:
            responses: List of responses from child tasks
            
        Returns:
            First response or empty string if no responses
        """
        if not self.validate_responses(responses):
            raise ValueError("Response validation failed")
        return responses[0] if responses else ""


class MajorityAggregator(TaskAggregator):
    """Aggregator that selects the response with the majority of votes."""
    
    def __init__(self, threshold: float = 0.5):
        """
        Initialize the aggregator.
        
        Args:
            threshold: Minimum fraction of votes required for a response to be selected
        """
        super().__init__(AggregationPolicy.MAJORITY)
        self.threshold = threshold
    
    def aggregate(self, responses: List[str]) -> str:
        """
        Aggregate responses by selecting the one with the majority of votes.
        
        Args:
            responses: List of responses from child tasks
            
        Returns:
            Response with the majority of votes or a message if no majority
        """
        if not responses:
            return ""
        
        # Count occurrences of each response
        counts = {}
        for response in responses:
            counts[response] = counts.get(response, 0) + 1
        
        # Find the most common response
        most_common = max(counts.items(), key=lambda x: x[1])
        
        # Check if it meets the threshold
        if most_common[1] / len(responses) >= self.threshold:
            return most_common[0]
        else:
            return "No majority reached"


class ConsensusAggregator(TaskAggregator):
    """Aggregator that requires consensus among responses."""
    
    def __init__(self, threshold: float = 1.0):
        """
        Initialize the aggregator.
        
        Args:
            threshold: Minimum fraction of agreement required for consensus
        """
        super().__init__(AggregationPolicy.CONSENSUS)
        self.threshold = threshold
    
    def aggregate(self, responses: List[str]) -> str:
        """
        Aggregate responses by requiring consensus.
        
        Args:
            responses: List of responses from child tasks
            
        Returns:
            Consensus response or a message if no consensus
        """
        if not responses:
            raise ValueError("No responses to aggregate")
            
        # Count occurrences of each response
        response_counts = {}
        for response in responses:
            response_counts[response] = response_counts.get(response, 0) + 1

        # Find responses that meet the threshold
        total = len(responses)
        consensus_responses = [
            resp for resp, count in response_counts.items()
            if count / total >= self.threshold
        ]

        if not consensus_responses:
            return "No consensus reached"
            
        return "\n".join(consensus_responses)


class FilterAggregator(TaskAggregator):
    """Aggregator that filters responses based on a condition."""
    
    def __init__(self, condition: Callable[[str], bool], policy: AggregationPolicy = AggregationPolicy.ALL):
        """
        Initialize the aggregator.
        
        Args:
            condition: Function that takes a response and returns True if it should be included
            policy: Aggregation policy to use
        """
        super().__init__(policy)
        self.condition = condition
    
    def aggregate(self, responses: List[str]) -> str:
        """
        Aggregate responses by filtering them.
        
        Args:
            responses: List of responses from child tasks
            
        Returns:
            Filtered responses
        """
        if not self.validate_responses(responses):
            raise ValueError("Response validation failed")
        filtered = [r for r in responses if self.condition(r)]
        return "\n".join(filtered)


class PrioritizeAggregator(TaskAggregator):
    """Aggregator that prioritizes responses based on a scoring function."""
    
    def __init__(self, score_func: Callable[[str], float], policy: AggregationPolicy = AggregationPolicy.ALL):
        """
        Initialize the aggregator.
        
        Args:
            score_func: Function that takes a response and returns a score
            policy: Aggregation policy to use
        """
        super().__init__(policy)
        self.score_func = score_func
    
    def aggregate(self, responses: List[str]) -> str:
        """
        Aggregate responses by prioritizing them.
        
        Args:
            responses: List of responses from child tasks
            
        Returns:
            Prioritized responses
        """
        if not self.validate_responses(responses):
            raise ValueError("Response validation failed")
        scored = [(r, self.score_func(r)) for r in responses]
        sorted_responses = sorted(scored, key=lambda x: x[1], reverse=True)
        return "\n".join(f"[Score: {score:.2f}] {response}" 
                        for response, score in sorted_responses)


# Registry of aggregator types
AGGREGATOR_REGISTRY: Dict[str, Type[TaskAggregator]] = {
    "all": AllAggregator,
    "combine": CombineAggregator,
    "summarize_all": SummarizeAllAggregator,
    "first_success": FirstSuccessAggregator,
    "majority": MajorityAggregator,
    "consensus": ConsensusAggregator,
    "filter": FilterAggregator,
    "prioritize": PrioritizeAggregator
}


def create_aggregator(aggregator_type: str, **kwargs) -> TaskAggregator:
    """
    Create an aggregator of the specified type.
    
    Args:
        aggregator_type: Type of aggregator to create
        **kwargs: Additional arguments to pass to the aggregator constructor
        
    Returns:
        Aggregator instance
        
    Raises:
        ValueError: If the aggregator type is not recognized
    """
    if aggregator_type not in AGGREGATOR_REGISTRY:
        raise ValueError(f"Unknown aggregator type: {aggregator_type}")
    
    return AGGREGATOR_REGISTRY[aggregator_type](**kwargs) 
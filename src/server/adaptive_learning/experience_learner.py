from typing import Dict, List, Optional
from dataclasses import dataclass
import asyncio
from datetime import datetime

@dataclass
class Experience:
    """Represents a system experience."""
    id: str
    type: str
    context: Dict
    outcome: Dict
    timestamp: datetime
    metadata: Dict

@dataclass
class Pattern:
    """Represents a learned pattern."""
    type: str
    context_features: List[str]
    success_indicators: List[str]
    confidence: float
    support: int
    metadata: Dict

@dataclass
class SuccessFactor:
    """Represents an identified success factor."""
    name: str
    impact_score: float
    confidence: float
    contexts: List[str]
    evidence: List[Dict]

class ExperienceLearner:
    """Learns from system experiences and interactions."""
    
    def __init__(self, knowledge_system, episodic_memory):
        self.knowledge_system = knowledge_system
        self.episodic_memory = episodic_memory
        self.learned_patterns: Dict[str, List[Pattern]] = {}
        self.success_factors: Dict[str, List[SuccessFactor]] = {}
        self.failure_lessons: Dict[str, List[Dict]] = {}
        self.adapted_strategies: Dict[str, Dict] = {}
        
    async def extract_patterns(self, experience_type: str) -> List[Pattern]:
        """
        Extract patterns from past experiences.
        
        Args:
            experience_type (str): Type of experience to analyze
            
        Returns:
            List[Pattern]: Extracted patterns
        """
        # Get relevant experiences from episodic memory
        experiences = await self.episodic_memory.get_experiences(
            experience_type=experience_type,
            min_count=100  # Need sufficient data for pattern extraction
        )
        
        if not experiences:
            return []
            
        patterns = []
        
        # Group experiences by context features
        context_groups = self._group_by_context_features(experiences)
        
        # Analyze each context group for patterns
        for context_features, group in context_groups.items():
            # Calculate success rate for this context
            success_rate = self._calculate_success_rate(group)
            
            # If success rate is significant, extract pattern
            if success_rate > 0.7:  # 70% success threshold
                pattern = Pattern(
                    type=experience_type,
                    context_features=context_features.split(","),
                    success_indicators=self._extract_success_indicators(group),
                    confidence=success_rate,
                    support=len(group),
                    metadata={
                        "discovered_at": datetime.now().isoformat(),
                        "last_validated": datetime.now().isoformat(),
                        "validation_count": 1
                    }
                )
                patterns.append(pattern)
                
        # Store patterns in knowledge system
        await self.knowledge_system.store_patterns(
            experience_type, patterns
        )
        
        # Update learned patterns cache
        self.learned_patterns[experience_type] = patterns
        
        return patterns
        
    async def identify_success_factors(self, goal_type: str) -> List[SuccessFactor]:
        """
        Identify factors that contribute to successful goal achievement.
        
        Args:
            goal_type (str): Type of goal to analyze
            
        Returns:
            List[SuccessFactor]: Identified success factors
        """
        # Get relevant experiences
        experiences = await self.episodic_memory.get_experiences(
            goal_type=goal_type,
            outcome_type="success",
            min_count=50
        )
        
        if not experiences:
            return []
            
        # Extract common factors from successful experiences
        success_factors = []
        
        # Group experiences by context features
        context_groups = self._group_by_context_features(experiences)
        
        for context_features, group in context_groups.items():
            # Calculate impact score for this factor
            impact_score = self._calculate_impact_score(
                group, context_features
            )
            
            if impact_score > 0.5:  # Significant impact threshold
                factor = SuccessFactor(
                    name=context_features,
                    impact_score=impact_score,
                    confidence=self._calculate_confidence(len(group)),
                    contexts=[exp.context["type"] for exp in group],
                    evidence=[{
                        "experience_id": exp.id,
                        "outcome": exp.outcome
                    } for exp in group]
                )
                success_factors.append(factor)
                
        # Store success factors in knowledge system
        await self.knowledge_system.store_success_factors(
            goal_type, success_factors
        )
        
        # Update success factors cache
        self.success_factors[goal_type] = success_factors
        
        return success_factors
        
    async def learn_from_failures(self, failure_type: str) -> List[Dict]:
        """
        Learn from past failures to improve future performance.
        
        Args:
            failure_type (str): Type of failure to analyze
            
        Returns:
            List[Dict]: Learned lessons from failures
        """
        # Get relevant failure experiences
        experiences = await self.episodic_memory.get_experiences(
            outcome_type="failure",
            failure_type=failure_type,
            min_count=20
        )
        
        if not experiences:
            return []
            
        lessons = []
        
        # Group failures by root cause
        cause_groups = self._group_by_root_cause(experiences)
        
        for cause, group in cause_groups.items():
            # Analyze failure patterns
            pattern = self._analyze_failure_pattern(group)
            
            # Generate preventive measures
            preventive_measures = self._generate_preventive_measures(
                pattern
            )
            
            lesson = {
                "failure_type": failure_type,
                "root_cause": cause,
                "pattern": pattern,
                "preventive_measures": preventive_measures,
                "confidence": self._calculate_confidence(len(group)),
                "evidence": [exp.id for exp in group],
                "learned_at": datetime.now().isoformat()
            }
            lessons.append(lesson)
            
        # Store lessons in knowledge system
        await self.knowledge_system.store_failure_lessons(
            failure_type, lessons
        )
        
        # Update failure lessons cache
        self.failure_lessons[failure_type] = lessons
        
        return lessons
        
    async def adapt_strategies(self, context_type: str) -> Dict:
        """
        Adapt strategies based on learned patterns.
        
        Args:
            context_type (str): Type of context to adapt strategies for
            
        Returns:
            Dict: Adapted strategies
        """
        # Get relevant patterns and lessons
        patterns = self.learned_patterns.get(context_type, [])
        lessons = self.failure_lessons.get(context_type, [])
        
        if not patterns and not lessons:
            return {}
            
        # Generate adapted strategies
        strategies = {
            "context_type": context_type,
            "adaptations": [],
            "preventive_measures": [],
            "optimization_rules": []
        }
        
        # Adapt based on successful patterns
        for pattern in patterns:
            if pattern.confidence > 0.8:  # High confidence threshold
                adaptation = {
                    "type": "pattern_based",
                    "pattern": pattern.type,
                    "conditions": pattern.context_features,
                    "actions": self._generate_actions(pattern),
                    "confidence": pattern.confidence
                }
                strategies["adaptations"].append(adaptation)
                
        # Add preventive measures from lessons
        for lesson in lessons:
            if lesson["confidence"] > 0.7:  # High confidence threshold
                measure = {
                    "type": "preventive",
                    "target": lesson["root_cause"],
                    "actions": lesson["preventive_measures"],
                    "confidence": lesson["confidence"]
                }
                strategies["preventive_measures"].append(measure)
                
        # Generate optimization rules
        strategies["optimization_rules"] = self._generate_optimization_rules(
            patterns, lessons
        )
        
        # Store adapted strategies in knowledge system
        await self.knowledge_system.store_adapted_strategies(
            context_type, strategies
        )
        
        # Update adapted strategies cache
        self.adapted_strategies[context_type] = strategies
        
        return strategies
        
    def _group_by_context_features(
        self, experiences: List[Experience]
    ) -> Dict[str, List[Experience]]:
        """Group experiences by their context features."""
        groups = {}
        for exp in experiences:
            features = ",".join(sorted(exp.context.keys()))
            if features not in groups:
                groups[features] = []
            groups[features].append(exp)
        return groups
        
    def _calculate_success_rate(self, experiences: List[Experience]) -> float:
        """Calculate success rate for a group of experiences."""
        if not experiences:
            return 0.0
        successes = sum(1 for exp in experiences if exp.outcome["success"])
        return successes / len(experiences)
        
    def _extract_success_indicators(
        self, experiences: List[Experience]
    ) -> List[str]:
        """Extract common success indicators from experiences."""
        indicators = set()
        for exp in experiences:
            if exp.outcome["success"]:
                indicators.update(exp.outcome.get("indicators", []))
        return list(indicators)
        
    def _calculate_impact_score(
        self, experiences: List[Experience], factor: str
    ) -> float:
        """Calculate impact score for a success factor."""
        if not experiences:
            return 0.0
        factor_present = sum(
            1 for exp in experiences 
            if factor in exp.context
        )
        return factor_present / len(experiences)
        
    def _calculate_confidence(self, sample_size: int) -> float:
        """Calculate confidence based on sample size."""
        # Simple confidence calculation based on sample size
        # Could be made more sophisticated with statistical methods
        if sample_size < 10:
            return 0.5
        elif sample_size < 50:
            return 0.7
        elif sample_size < 100:
            return 0.8
        else:
            return 0.9
            
    def _group_by_root_cause(
        self, experiences: List[Experience]
    ) -> Dict[str, List[Experience]]:
        """Group failure experiences by root cause."""
        groups = {}
        for exp in experiences:
            cause = exp.outcome.get("root_cause", "unknown")
            if cause not in groups:
                groups[cause] = []
            groups[cause].append(exp)
        return groups
        
    def _analyze_failure_pattern(self, experiences: List[Experience]) -> Dict:
        """Analyze pattern in failure experiences."""
        return {
            "common_contexts": self._extract_common_contexts(experiences),
            "common_factors": self._extract_common_factors(experiences),
            "frequency": len(experiences),
            "impact": self._calculate_failure_impact(experiences)
        }
        
    def _generate_preventive_measures(self, pattern: Dict) -> List[Dict]:
        """Generate preventive measures based on failure pattern."""
        measures = []
        
        # Add context-based checks
        for context in pattern["common_contexts"]:
            measures.append({
                "type": "context_check",
                "context": context,
                "action": "validate_before_execution"
            })
            
        # Add factor-based mitigations
        for factor in pattern["common_factors"]:
            measures.append({
                "type": "factor_mitigation",
                "factor": factor,
                "action": "implement_safeguard"
            })
            
        return measures
        
    def _generate_actions(self, pattern: Pattern) -> List[Dict]:
        """Generate actions based on successful pattern."""
        actions = []
        
        # Add context-based optimizations
        for feature in pattern.context_features:
            actions.append({
                "type": "context_optimization",
                "feature": feature,
                "action": "optimize_for_context"
            })
            
        # Add success indicator-based actions
        for indicator in pattern.success_indicators:
            actions.append({
                "type": "success_promotion",
                "indicator": indicator,
                "action": "promote_success_factor"
            })
            
        return actions
        
    def _generate_optimization_rules(
        self, patterns: List[Pattern], lessons: List[Dict]
    ) -> List[Dict]:
        """Generate optimization rules from patterns and lessons."""
        rules = []
        
        # Add pattern-based rules
        for pattern in patterns:
            if pattern.confidence > 0.8:
                rules.append({
                    "type": "pattern_optimization",
                    "pattern": pattern.type,
                    "conditions": pattern.context_features,
                    "actions": self._generate_actions(pattern)
                })
                
        # Add lesson-based rules
        for lesson in lessons:
            if lesson["confidence"] > 0.7:
                rules.append({
                    "type": "failure_prevention",
                    "target": lesson["root_cause"],
                    "conditions": lesson["pattern"]["common_contexts"],
                    "actions": lesson["preventive_measures"]
                })
                
        return rules
        
    def _extract_common_contexts(self, experiences: List[Experience]) -> List[str]:
        """Extract common contexts from experiences."""
        if not experiences:
            return []
            
        # Get contexts from first experience
        common_contexts = set(experiences[0].context.keys())
        
        # Intersect with contexts from other experiences
        for exp in experiences[1:]:
            common_contexts.intersection_update(exp.context.keys())
            
        return list(common_contexts)
        
    def _extract_common_factors(self, experiences: List[Experience]) -> List[str]:
        """Extract common factors from experiences."""
        if not experiences:
            return []
            
        # Get factors from first experience
        common_factors = set(
            exp.outcome.get("contributing_factors", [])
            for exp in experiences
        )
        
        # Intersect with factors from other experiences
        for exp in experiences[1:]:
            factors = set(exp.outcome.get("contributing_factors", []))
            common_factors.intersection_update(factors)
            
        return list(common_factors)
        
    def _calculate_failure_impact(self, experiences: List[Experience]) -> float:
        """Calculate impact score for failures."""
        if not experiences:
            return 0.0
            
        total_impact = sum(
            exp.outcome.get("impact_score", 0.0)
            for exp in experiences
        )
        return total_impact / len(experiences) 
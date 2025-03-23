from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio

@dataclass
class Feedback:
    """Represents user feedback."""
    id: str
    type: str
    content: str
    context: Dict
    timestamp: datetime
    metadata: Dict

@dataclass
class ImprovementArea:
    """Represents an identified area for improvement."""
    name: str
    priority: float
    confidence: float
    supporting_feedback: List[str]
    metadata: Dict

@dataclass
class ImprovementProposal:
    """Represents a proposed improvement."""
    id: str
    area: str
    description: str
    impact_estimate: float
    complexity_estimate: float
    priority: float
    implementation_steps: List[Dict]
    metadata: Dict

class FeedbackLearner:
    """Learns from user feedback to improve system performance."""
    
    def __init__(self, knowledge_system):
        self.knowledge_system = knowledge_system
        self.feedback_history: List[Feedback] = []
        self.improvement_areas: Dict[str, ImprovementArea] = {}
        self.improvement_proposals: Dict[str, List[ImprovementProposal]] = {}
        self.impact_tracking: Dict[str, Dict] = {}
        
    async def process_feedback(
        self, feedback: Dict, context: Dict
    ) -> Feedback:
        """
        Process and categorize user feedback.
        
        Args:
            feedback (Dict): User feedback to process
            context (Dict): Context in which feedback was given
            
        Returns:
            Feedback: Processed feedback object
        """
        # Create feedback object
        feedback_obj = Feedback(
            id=f"feedback_{len(self.feedback_history)}",
            type=self._determine_feedback_type(feedback),
            content=feedback["content"],
            context=context,
            timestamp=datetime.now(),
            metadata={
                "sentiment": self._analyze_sentiment(feedback["content"]),
                "categories": self._categorize_feedback(feedback["content"]),
                "priority": self._determine_priority(feedback, context)
            }
        )
        
        # Store feedback in history
        self.feedback_history.append(feedback_obj)
        
        # Store in knowledge system
        await self.knowledge_system.store_feedback(feedback_obj)
        
        # Update improvement areas based on new feedback
        await self._update_improvement_areas(feedback_obj)
        
        return feedback_obj
        
    async def identify_improvement_areas(self) -> List[ImprovementArea]:
        """
        Identify areas for improvement based on feedback.
        
        Returns:
            List[ImprovementArea]: Identified improvement areas
        """
        # Group feedback by category
        feedback_groups = self._group_feedback_by_category()
        
        improvement_areas = []
        
        for category, feedback_list in feedback_groups.items():
            # Calculate priority for this area
            priority = self._calculate_area_priority(feedback_list)
            
            # Calculate confidence based on feedback volume and consistency
            confidence = self._calculate_area_confidence(feedback_list)
            
            if confidence > 0.5:  # Minimum confidence threshold
                area = ImprovementArea(
                    name=category,
                    priority=priority,
                    confidence=confidence,
                    supporting_feedback=[f.id for f in feedback_list],
                    metadata={
                        "identified_at": datetime.now().isoformat(),
                        "feedback_count": len(feedback_list),
                        "average_sentiment": self._calculate_average_sentiment(
                            feedback_list
                        )
                    }
                )
                improvement_areas.append(area)
                
        # Sort by priority
        improvement_areas.sort(key=lambda x: x.priority, reverse=True)
        
        # Store in knowledge system
        await self.knowledge_system.store_improvement_areas(improvement_areas)
        
        # Update cache
        self.improvement_areas = {
            area.name: area for area in improvement_areas
        }
        
        return improvement_areas
        
    async def generate_improvement_proposals(
        self, area: str
    ) -> List[ImprovementProposal]:
        """
        Generate proposals for improvements in a specific area.
        
        Args:
            area (str): Area to generate proposals for
            
        Returns:
            List[ImprovementProposal]: Generated improvement proposals
        """
        if area not in self.improvement_areas:
            return []
            
        improvement_area = self.improvement_areas[area]
        
        # Get relevant feedback
        feedback_list = [
            f for f in self.feedback_history
            if f.id in improvement_area.supporting_feedback
        ]
        
        proposals = []
        
        # Generate proposals based on feedback patterns
        patterns = self._identify_feedback_patterns(feedback_list)
        
        for pattern in patterns:
            if pattern["confidence"] > 0.7:  # Minimum confidence threshold
                proposal = ImprovementProposal(
                    id=f"proposal_{len(proposals)}",
                    area=area,
                    description=self._generate_proposal_description(pattern),
                    impact_estimate=self._estimate_impact(pattern),
                    complexity_estimate=self._estimate_complexity(pattern),
                    priority=pattern["priority"],
                    implementation_steps=self._generate_implementation_steps(
                        pattern
                    ),
                    metadata={
                        "generated_at": datetime.now().isoformat(),
                        "pattern_confidence": pattern["confidence"],
                        "supporting_feedback": pattern["feedback_ids"]
                    }
                )
                proposals.append(proposal)
                
        # Sort by priority
        proposals.sort(key=lambda x: x.priority, reverse=True)
        
        # Store in knowledge system
        await self.knowledge_system.store_improvement_proposals(area, proposals)
        
        # Update cache
        self.improvement_proposals[area] = proposals
        
        return proposals
        
    async def track_feedback_impact(
        self, improvement_id: str
    ) -> Dict:
        """
        Track the impact of improvements made based on feedback.
        
        Args:
            improvement_id (str): ID of improvement to track
            
        Returns:
            Dict: Impact tracking data
        """
        # Get improvement data
        improvement = None
        for proposals in self.improvement_proposals.values():
            for proposal in proposals:
                if proposal.id == improvement_id:
                    improvement = proposal
                    break
            if improvement:
                break
                
        if not improvement:
            return {}
            
        # Get feedback before and after improvement
        implementation_time = datetime.fromisoformat(
            improvement.metadata["generated_at"]
        )
        
        before_feedback = [
            f for f in self.feedback_history
            if f.timestamp < implementation_time and
            f.metadata["categories"].intersection(
                set([improvement.area])
            )
        ]
        
        after_feedback = [
            f for f in self.feedback_history
            if f.timestamp >= implementation_time and
            f.metadata["categories"].intersection(
                set([improvement.area])
            )
        ]
        
        # Calculate impact metrics
        impact_data = {
            "improvement_id": improvement_id,
            "area": improvement.area,
            "metrics": {
                "feedback_volume_change": self._calculate_volume_change(
                    before_feedback, after_feedback
                ),
                "sentiment_change": self._calculate_sentiment_change(
                    before_feedback, after_feedback
                ),
                "issue_resolution_rate": self._calculate_resolution_rate(
                    before_feedback, after_feedback
                )
            },
            "analysis": {
                "effectiveness": self._analyze_effectiveness(
                    before_feedback, after_feedback
                ),
                "side_effects": self._analyze_side_effects(
                    before_feedback, after_feedback
                ),
                "user_satisfaction": self._analyze_user_satisfaction(
                    before_feedback, after_feedback
                )
            }
        }
        
        # Store impact data
        await self.knowledge_system.store_improvement_impact(
            improvement_id, impact_data
        )
        
        # Update cache
        self.impact_tracking[improvement_id] = impact_data
        
        return impact_data
        
    def _determine_feedback_type(self, feedback: Dict) -> str:
        """Determine the type of feedback."""
        content = feedback["content"].lower()
        
        if any(word in content for word in ["error", "bug", "issue", "problem"]):
            return "issue"
        elif any(word in content for word in ["suggest", "improve", "enhancement"]):
            return "suggestion"
        elif any(word in content for word in ["thank", "great", "good", "awesome"]):
            return "praise"
        else:
            return "general"
            
    def _analyze_sentiment(self, content: str) -> float:
        """Analyze sentiment of feedback content."""
        # Simple sentiment analysis
        # Could be replaced with more sophisticated NLP
        positive_words = {"good", "great", "excellent", "awesome", "thank"}
        negative_words = {"bad", "poor", "issue", "bug", "problem"}
        
        words = set(content.lower().split())
        
        positive_count = len(words.intersection(positive_words))
        negative_count = len(words.intersection(negative_words))
        
        if positive_count == 0 and negative_count == 0:
            return 0.0
            
        return (positive_count - negative_count) / (positive_count + negative_count)
        
    def _categorize_feedback(self, content: str) -> set:
        """Categorize feedback content."""
        categories = set()
        
        # Performance-related
        if any(word in content.lower() for word in ["slow", "fast", "speed", "performance"]):
            categories.add("performance")
            
        # Functionality-related
        if any(word in content.lower() for word in ["feature", "function", "capability"]):
            categories.add("functionality")
            
        # UI/UX-related
        if any(word in content.lower() for word in ["interface", "ui", "ux", "usability"]):
            categories.add("ui_ux")
            
        # Reliability-related
        if any(word in content.lower() for word in ["crash", "error", "bug", "reliable"]):
            categories.add("reliability")
            
        return categories or {"general"}
        
    def _determine_priority(self, feedback: Dict, context: Dict) -> float:
        """Determine priority of feedback."""
        base_priority = 0.5
        
        # Adjust based on feedback type
        type_adjustments = {
            "issue": 0.3,
            "suggestion": 0.1,
            "praise": 0.0
        }
        base_priority += type_adjustments.get(
            self._determine_feedback_type(feedback), 0.0
        )
        
        # Adjust based on sentiment
        sentiment = self._analyze_sentiment(feedback["content"])
        if sentiment < 0:
            base_priority += abs(sentiment) * 0.2
            
        # Adjust based on context
        if context.get("critical", False):
            base_priority += 0.3
            
        return min(1.0, max(0.0, base_priority))
        
    async def _update_improvement_areas(self, feedback: Feedback):
        """Update improvement areas based on new feedback."""
        # Get existing areas
        areas = await self.identify_improvement_areas()
        
        # Update priorities based on new feedback
        for area in areas:
            if any(cat in feedback.metadata["categories"] for cat in [area.name]):
                area.supporting_feedback.append(feedback.id)
                area.priority = self._calculate_area_priority(
                    [f for f in self.feedback_history 
                     if f.id in area.supporting_feedback]
                )
                
        # Store updated areas
        await self.knowledge_system.store_improvement_areas(areas)
        
    def _group_feedback_by_category(self) -> Dict[str, List[Feedback]]:
        """Group feedback by category."""
        groups = {}
        for feedback in self.feedback_history:
            for category in feedback.metadata["categories"]:
                if category not in groups:
                    groups[category] = []
                groups[category].append(feedback)
        return groups
        
    def _calculate_area_priority(self, feedback_list: List[Feedback]) -> float:
        """Calculate priority for an improvement area."""
        if not feedback_list:
            return 0.0
            
        # Consider feedback priorities and recency
        total_priority = 0.0
        for feedback in feedback_list:
            age_factor = 1.0  # Could implement decay based on age
            total_priority += feedback.metadata["priority"] * age_factor
            
        return total_priority / len(feedback_list)
        
    def _calculate_area_confidence(self, feedback_list: List[Feedback]) -> float:
        """Calculate confidence in an improvement area."""
        if not feedback_list:
            return 0.0
            
        # Consider feedback volume and consistency
        volume_factor = min(1.0, len(feedback_list) / 10)  # Saturate at 10 items
        
        # Calculate sentiment consistency
        sentiments = [f.metadata["sentiment"] for f in feedback_list]
        sentiment_std = self._calculate_std(sentiments)
        consistency_factor = 1.0 - min(1.0, sentiment_std)
        
        return (volume_factor + consistency_factor) / 2
        
    def _calculate_average_sentiment(self, feedback_list: List[Feedback]) -> float:
        """Calculate average sentiment for feedback list."""
        if not feedback_list:
            return 0.0
            
        return sum(f.metadata["sentiment"] for f in feedback_list) / len(feedback_list)
        
    def _identify_feedback_patterns(self, feedback_list: List[Feedback]) -> List[Dict]:
        """Identify patterns in feedback."""
        patterns = []
        
        # Group by common themes/phrases
        theme_groups = self._group_by_themes(feedback_list)
        
        for theme, group in theme_groups.items():
            pattern = {
                "theme": theme,
                "frequency": len(group),
                "confidence": self._calculate_pattern_confidence(group),
                "priority": self._calculate_pattern_priority(group),
                "feedback_ids": [f.id for f in group]
            }
            patterns.append(pattern)
            
        return patterns
        
    def _generate_proposal_description(self, pattern: Dict) -> str:
        """Generate description for improvement proposal."""
        return f"Improvement proposal based on {pattern['theme']} feedback pattern"
        
    def _estimate_impact(self, pattern: Dict) -> float:
        """Estimate potential impact of implementing a pattern-based improvement."""
        return pattern["frequency"] * pattern["confidence"]
        
    def _estimate_complexity(self, pattern: Dict) -> float:
        """Estimate complexity of implementing a pattern-based improvement."""
        # Simple estimation - could be made more sophisticated
        return 0.5
        
    def _generate_implementation_steps(self, pattern: Dict) -> List[Dict]:
        """Generate implementation steps for a pattern-based improvement."""
        return [
            {
                "step": 1,
                "description": f"Implement improvements for {pattern['theme']}",
                "estimated_effort": "medium"
            }
        ]
        
    def _calculate_volume_change(
        self, before: List[Feedback], after: List[Feedback]
    ) -> float:
        """Calculate change in feedback volume."""
        if not before:
            return 1.0 if after else 0.0
            
        before_rate = len(before) / max(1, (before[-1].timestamp - before[0].timestamp).days)
        after_rate = len(after) / max(1, (after[-1].timestamp - after[0].timestamp).days)
        
        return (after_rate - before_rate) / before_rate if before_rate > 0 else 0.0
        
    def _calculate_sentiment_change(
        self, before: List[Feedback], after: List[Feedback]
    ) -> float:
        """Calculate change in sentiment."""
        before_sentiment = self._calculate_average_sentiment(before)
        after_sentiment = self._calculate_average_sentiment(after)
        
        return after_sentiment - before_sentiment
        
    def _calculate_resolution_rate(
        self, before: List[Feedback], after: List[Feedback]
    ) -> float:
        """Calculate issue resolution rate."""
        if not before:
            return 1.0
            
        before_issues = sum(1 for f in before if f.type == "issue")
        after_issues = sum(1 for f in after if f.type == "issue")
        
        if before_issues == 0:
            return 1.0
            
        return 1.0 - (after_issues / before_issues)
        
    def _analyze_effectiveness(
        self, before: List[Feedback], after: List[Feedback]
    ) -> Dict:
        """Analyze effectiveness of improvement."""
        return {
            "sentiment_improvement": self._calculate_sentiment_change(before, after),
            "issue_reduction": self._calculate_resolution_rate(before, after),
            "feedback_reduction": self._calculate_volume_change(before, after)
        }
        
    def _analyze_side_effects(
        self, before: List[Feedback], after: List[Feedback]
    ) -> List[Dict]:
        """Analyze potential side effects of improvement."""
        return []  # Implement side effect analysis
        
    def _analyze_user_satisfaction(
        self, before: List[Feedback], after: List[Feedback]
    ) -> Dict:
        """Analyze change in user satisfaction."""
        return {
            "sentiment_change": self._calculate_sentiment_change(before, after),
            "positive_feedback_ratio": self._calculate_positive_feedback_ratio(after)
        }
        
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if not values:
            return 0.0
            
        mean = sum(values) / len(values)
        squared_diff_sum = sum((x - mean) ** 2 for x in values)
        return (squared_diff_sum / len(values)) ** 0.5
        
    def _group_by_themes(self, feedback_list: List[Feedback]) -> Dict[str, List[Feedback]]:
        """Group feedback by common themes."""
        groups = {}
        for feedback in feedback_list:
            theme = self._extract_main_theme(feedback.content)
            if theme not in groups:
                groups[theme] = []
            groups[theme].append(feedback)
        return groups
        
    def _extract_main_theme(self, content: str) -> str:
        """Extract main theme from feedback content."""
        # Simple implementation - could be enhanced with NLP
        return "general"
        
    def _calculate_pattern_confidence(self, feedback_group: List[Feedback]) -> float:
        """Calculate confidence in a feedback pattern."""
        return self._calculate_area_confidence(feedback_group)
        
    def _calculate_pattern_priority(self, feedback_group: List[Feedback]) -> float:
        """Calculate priority for a feedback pattern."""
        return self._calculate_area_priority(feedback_group)
        
    def _calculate_positive_feedback_ratio(self, feedback_list: List[Feedback]) -> float:
        """Calculate ratio of positive feedback."""
        if not feedback_list:
            return 0.0
            
        positive_count = sum(
            1 for f in feedback_list 
            if f.metadata["sentiment"] > 0
        )
        return positive_count / len(feedback_list) 
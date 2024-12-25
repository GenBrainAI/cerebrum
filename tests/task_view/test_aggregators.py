import pytest
from src.server.controllers.tasks_tree_controller import (
    TaskAggregator, AllAggregator, CombineAggregator, 
    SummarizeAllAggregator, FilterAggregator, 
    PrioritizeAggregator, ConsensusAggregator,
    AggregationPolicy
)

class TestAggregators:
    @pytest.mark.asyncio
    async def test_all_aggregator(self):
        aggregator = AllAggregator()
        responses = ["Response 1", "Response 2"]
        result = aggregator.aggregate(responses)
        assert result == "Response 1\nResponse 2"

    @pytest.mark.asyncio
    async def test_combine_aggregator(self):
        aggregator = CombineAggregator()
        responses = ["Response 1", "Response 2"]
        result = aggregator.aggregate(responses)
        assert result == "Response 1 Response 2"

    @pytest.mark.asyncio
    async def test_summarize_aggregator(self):
        aggregator = SummarizeAllAggregator()
        responses = ["Response 1", "Response 2"]
        result = aggregator.aggregate(responses)
        assert result == "Summary: Response 1, Response 2"

    @pytest.mark.asyncio
    async def test_filter_aggregator(self):
        aggregator = FilterAggregator(lambda x: len(x) > 10)
        responses = ["Short", "Long response"]
        result = aggregator.aggregate(responses)
        assert result == "Long response"

    @pytest.mark.asyncio
    async def test_prioritize_aggregator(self):
        aggregator = PrioritizeAggregator(lambda x: len(x))
        responses = ["Short", "Longer response"]
        result = aggregator.aggregate(responses)
        assert "Longer response" in result
        assert "[Score:" in result

    @pytest.mark.asyncio
    async def test_consensus_aggregator(self):
        aggregator = ConsensusAggregator(threshold=0.5)
        responses = ["A", "A", "B"]
        result = aggregator.aggregate(responses)
        assert result == "A"

    @pytest.mark.asyncio
    async def test_aggregation_policies(self):
        # Test ALL policy
        aggregator = AllAggregator(policy=AggregationPolicy.ALL)
        assert aggregator.validate_responses(["A", "B"])
        assert not aggregator.validate_responses([])

        # Test ANY policy
        aggregator = AllAggregator(policy=AggregationPolicy.ANY)
        assert aggregator.validate_responses(["A"])
        assert not aggregator.validate_responses([])

        # Test MAJORITY policy
        aggregator = AllAggregator(policy=AggregationPolicy.MAJORITY)
        assert aggregator.validate_responses(["A", "A", "B"])
        assert not aggregator.validate_responses([])

        # Test CONSENSUS policy
        aggregator = AllAggregator(policy=AggregationPolicy.CONSENSUS)
        assert aggregator.validate_responses(["A", "A"])
        assert not aggregator.validate_responses(["A", "B"])

    @pytest.mark.asyncio
    async def test_empty_responses(self):
        aggregators = [
            AllAggregator(),
            CombineAggregator(),
            SummarizeAllAggregator(),
            FilterAggregator(lambda x: True),
            PrioritizeAggregator(lambda x: 1),
            ConsensusAggregator()
        ]
        
        for aggregator in aggregators:
            with pytest.raises(ValueError):
                aggregator.aggregate([])

    @pytest.mark.asyncio
    async def test_custom_filter_conditions(self):
        # Test various filter conditions
        contains_error = FilterAggregator(lambda x: "error" in x.lower())
        responses = ["Success", "Error occurred", "Another success"]
        result = contains_error.aggregate(responses)
        assert result == "Error occurred"

        is_json = FilterAggregator(lambda x: x.strip().startswith("{"))
        responses = ["plain text", '{"key": "value"}', "more text"]
        result = is_json.aggregate(responses)
        assert result == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_custom_priority_scoring(self):
        # Test different scoring functions
        error_priority = PrioritizeAggregator(
            lambda x: 10 if "error" in x.lower() else 
                     5 if "warning" in x.lower() else 1
        )
        responses = ["Success", "Warning: check this", "Error: bad thing"]
        result = error_priority.aggregate(responses)
        assert "Error: bad thing" in result.split("\n")[0]

    @pytest.mark.asyncio
    async def test_consensus_thresholds(self):
        responses = ["A", "A", "A", "B", "B"]
        
        # Test different thresholds
        full_consensus = ConsensusAggregator(threshold=1.0)
        with pytest.raises(ValueError):
            full_consensus.aggregate(responses)

        majority = ConsensusAggregator(threshold=0.5)
        result = majority.aggregate(responses)
        assert result == "A"

        any_consensus = ConsensusAggregator(threshold=0.3)
        result = any_consensus.aggregate(responses)
        assert "A" in result and "B" in result 
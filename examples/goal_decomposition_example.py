"""
Example script demonstrating how to use the Goal Decomposition Engine.

This script shows how to:
1. Initialize the Self-Aware System
2. Decompose a high-level goal into subgoals
3. Prioritize subgoals
4. Estimate resources
5. Validate the decomposition
"""

import asyncio
import json
import os
from datetime import datetime

from src.server.self_aware_integration import SelfAwareSystem
from src.server.planning.goal_decomposition import DecompositionStrategy, GoalType

async def main():
    """Run the Goal Decomposition example."""
    print("Initializing Self-Aware System...")
    system = SelfAwareSystem(storage_path="persistent_state/examples")
    await system.initialize()
    
    print("\nCreating a high-level goal...")
    goal = {
        "name": "Implement AI-Powered Code Review System",
        "description": "Develop a system that can automatically review code changes, identify potential issues, and suggest improvements.",
        "type": "DEVELOPMENT",
        "metadata": {
            "priority": "high",
            "owner": "AI Team",
            "deadline": datetime.now().isoformat()
        }
    }
    
    print("\nDecomposing the goal using TOP_DOWN strategy...")
    decomposed_goal = await system.decompose_goal(
        goal=goal,
        strategy="TOP_DOWN"
    )
    
    print(f"\nGoal decomposed successfully with ID: {decomposed_goal['id']}")
    print(f"Goal name: {decomposed_goal['name']}")
    print(f"Goal type: {decomposed_goal['goal_type']}")
    print(f"Strategy used: {decomposed_goal['strategy']}")
    print(f"Number of subgoals: {len(decomposed_goal['subgoals'])}")
    
    print("\nRoot subgoals:")
    for subgoal_id in decomposed_goal['root_subgoal_ids']:
        subgoal = decomposed_goal['subgoals'][subgoal_id]
        print(f"  - {subgoal['name']}: {subgoal['description']}")
    
    print("\nPrioritizing subgoals...")
    prioritized_subgoals = await system.prioritize_subgoals(decomposed_goal['id'])
    
    print("\nPrioritized subgoals (in order of priority):")
    for i, subgoal_id in enumerate(prioritized_subgoals):
        subgoal = decomposed_goal['subgoals'][subgoal_id]
        print(f"  {i+1}. {subgoal['name']} (Priority: {subgoal['priority']})")
    
    print("\nEstimating resources...")
    resource_estimate = await system.estimate_goal_resources(decomposed_goal['id'])
    
    print("\nResource estimates:")
    print(f"  - Total time: {resource_estimate['time_hours']:.1f} hours")
    print(f"  - Complexity: {resource_estimate['complexity']}/10")
    print(f"  - Risk level: {resource_estimate['risk_level']}/10")
    print(f"  - Knowledge requirements: {', '.join(resource_estimate['knowledge_requirements'])}")
    
    print("\nValidating decomposition...")
    validation = await system.validate_goal_decomposition(decomposed_goal['id'])
    
    print("\nValidation results:")
    print(f"  - Valid: {validation['valid']}")
    if validation['warnings']:
        print("  - Warnings:")
        for warning in validation['warnings']:
            print(f"    * {warning}")
    
    print("\nSubgoal tree structure:")
    tree = decomposed_goal['subgoals'][decomposed_goal['root_subgoal_ids'][0]]['children_ids']
    print_tree(decomposed_goal['subgoals'], decomposed_goal['root_subgoal_ids'][0], 0)
    
    print("\nSaving decomposed goal to file...")
    os.makedirs("examples/output", exist_ok=True)
    with open("examples/output/decomposed_goal.json", "w") as f:
        json.dump(decomposed_goal, f, indent=2)
    
    print("\nDecomposed goal saved to examples/output/decomposed_goal.json")

def print_tree(subgoals, subgoal_id, level):
    """Print the subgoal tree structure recursively."""
    subgoal = subgoals[subgoal_id]
    indent = "  " * level
    print(f"{indent}- {subgoal['name']}")
    
    for child_id in subgoal.get('children_ids', []):
        print_tree(subgoals, child_id, level + 1)

if __name__ == "__main__":
    asyncio.run(main()) 
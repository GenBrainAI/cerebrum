# Cerebrum Plugin Handover Demo Script

import sys
import os
import asyncio
import json
from typing import Dict, Any, List
import matplotlib.pyplot as plt
import networkx as nx

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.getcwd(), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import Cerebrum components
from src.server.plugins.plugin_manager import PluginManager
from src.server.plugins.agent_framework_config import AgentFrameworkConfig

async def load_demo_plugins():
    """Load the necessary plugins for demonstration."""
    # Initialize plugin manager
    plugin_manager = PluginManager()
    print("✅ Plugin manager initialized")

    # Configure and load CrewAI
    crewai_config = AgentFrameworkConfig(
        name="crewai",
        version="1.0.0",
        description="CrewAI Plugin for multi-agent collaboration",
        settings={
            "model": "gpt-4o-mini",
            "temperature": 0.7,
            "verbose": True
        }
    )
    crewai_path = os.path.join(project_root, "src/server/plugins/crewai_plugin.py")
    crewai_success = await plugin_manager.load_plugin(crewai_path, crewai_config)
    print(f"CrewAI plugin loaded: {'✅' if crewai_success else '❌'}")

    # Configure and load AutoGen
    autogen_config = AgentFrameworkConfig(
        name="autogen",
        version="1.0.0",
        description="AutoGen Plugin for conversational agents",
        settings={
            "model": "gpt-4o-mini",
            "temperature": 0.5,
            "verbose": True
        }
    )
    autogen_path = os.path.join(project_root, "src/server/plugins/autogen_plugin.py")
    autogen_success = await plugin_manager.load_plugin(autogen_path, autogen_config)
    print(f"AutoGen plugin loaded: {'✅' if autogen_success else '❌'}")

    # Configure and load SmolAgents
    smolagents_config = AgentFrameworkConfig(
        name="smolagents",
        version="1.0.0",
        description="SmolAgents Plugin for lightweight agents",
        settings={
            "model": "gpt-4o-mini",
            "temperature": 0.6,
            "verbose": True
        }
    )
    smolagents_path = os.path.join(project_root, "src/server/plugins/smolagents_plugin.py")
    smolagents_success = await plugin_manager.load_plugin(smolagents_path, smolagents_config)
    print(f"SmolAgents plugin loaded: {'✅' if smolagents_success else '❌'}")

    return plugin_manager, crewai_success and autogen_success and smolagents_success

async def run_multi_plugin_workflow(plugin_manager, topic="AI agents"):
    """Run a workflow that hands off between multiple plugins."""
    results = {
        "steps": [],
        "outputs": {}
    }

    try:
        # Step 1: CrewAI for research
        print("\n🔍 Step 1: CrewAI Research")
        results["steps"].append("Creating CrewAI researcher agent")

        researcher_config = {
            "role": "Researcher",
            "goal": f"Find detailed information about {topic}",
            "backstory": "Expert researcher with broad knowledge of AI and technology",
            "tools": [
                {"name": "web_search", "description": "Search the web for information"}
            ]
        }

        researcher = await plugin_manager.create_agent("crewai", researcher_config)

        research_task = {
            "description": f"Research the latest developments in {topic}, focusing on real-world applications, key technologies, and future trends.",
            "expected_output": "A comprehensive research report with key findings and insights"
        }

        results["steps"].append(f"Executing research task with CrewAI: {research_task['description']}")
        research_result = await plugin_manager.execute_task("crewai", researcher, research_task)
        print(f"✅ CrewAI Research completed")

        if isinstance(research_result, dict) and 'result' in research_result:
            research_output = research_result['result']
        else:
            research_output = research_result

        results["outputs"]["research"] = research_output
        print(f"📝 Research summary: {str(research_output)[:150]}...")

        # Step 2: AutoGen for analysis
        print("\n📊 Step 2: AutoGen Analysis")
        results["steps"].append("Creating AutoGen analyst agent")

        analyst_config = {
            "role": "Analyst",
            "goal": "Analyze research findings and identify key trends and patterns",
            "previous_results": results["outputs"]["research"]
        }

        analyst = await plugin_manager.create_agent("autogen", analyst_config)

        analysis_task = {
            "description": "Analyze the research findings, identify key trends, and extract actionable insights",
            "input_data": {"research": results["outputs"]["research"]}
        }

        results["steps"].append(f"Executing analysis task with AutoGen: {analysis_task['description']}")
        analysis_result = await plugin_manager.execute_task("autogen", analyst, analysis_task)
        print(f"✅ AutoGen Analysis completed")

        if isinstance(analysis_result, dict) and 'result' in analysis_result:
            analysis_output = analysis_result['result']
        else:
            analysis_output = analysis_result

        results["outputs"]["analysis"] = analysis_output
        print(f"📝 Analysis summary: {str(analysis_output)[:150]}...")

        # Step 3: SmolAgents for report generation
        print("\n📝 Step 3: SmolAgents Report Generation")
        results["steps"].append("Creating SmolAgents writer agent")

        report_writer_config = {
            "role": "Writer",
            "goal": "Create a final report based on the research and analysis",
            "previous_results": {
                "research": results["outputs"]["research"],
                "analysis": results["outputs"]["analysis"]
            }
        }

        report_writer = await plugin_manager.create_agent("smolagents", report_writer_config)

        report_task = {
            "description": "Create a comprehensive final report based on the research and analysis, including executive summary, key findings, and recommendations",
            "input_data": {
                "analysis": results["outputs"]["analysis"],
                "research": results["outputs"]["research"]
            }
        }

        results["steps"].append(f"Executing report task with SmolAgents: {report_task['description']}")
        report_result = await plugin_manager.execute_task("smolagents", report_writer, report_task)
        print(f"✅ SmolAgents Report Generation completed")

        if isinstance(report_result, dict) and 'result' in report_result:
            report_output = report_result['result']
        else:
            report_output = report_result

        results["outputs"]["report"] = report_output
        print(f"📝 Report summary: {str(report_output)[:150]}...")

        return results

    except Exception as e:
        print(f"❌ Error in workflow: {str(e)}")
        results["error"] = str(e)
        return results

async def main():
    plugin_manager, success = await load_demo_plugins()
    if success:
        print("\n✅ All plugins loaded successfully")
        workflow_results = await run_multi_plugin_workflow(plugin_manager, "agentic frameworks and their business applications")
        if "report" in workflow_results["outputs"]:
            print("\n🎉 Final Report:")
            print("=" * 80)
            print(workflow_results["outputs"]["report"])
            print("=" * 80)
        else:
            print("❌ No report generated in the workflow")
    else:
        print("⚠️ Some plugins failed to load")

if __name__ == "__main__":
    asyncio.run(main()) 
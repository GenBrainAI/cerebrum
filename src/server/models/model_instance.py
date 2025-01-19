from typing import Any, Dict, List, Optional
import json

class ModelInstance:
    def __init__(self, model_name: str, api_provider: str):
        self.model_name = model_name
        self.api_provider = api_provider
        self.client = None

    async def completion(
        self,
        messages: List[Dict[str, Any]],
        curried_proxy: CurriedProxy,
        tools_catalog: ToolsCatalog
    ) -> Dict[str, Any]:
        """Execute a completion with the given parameters."""
        try:
            # Get tools from curried proxy
            tools = curried_proxy.export_to_openai()

            # Execute completion
            response = await self._execute_completion(messages, tools)

            # Process tool calls if any
            if response.choices[0].finish_reason == "tool_calls":
                tool_calls = response.choices[0].message.tool_calls
                for tool_call in tool_calls:
                    # Execute tool through tools catalog
                    result = await tools_catalog.execute_tool(
                        tool_call.function.name,
                        json.loads(tool_call.function.arguments)
                    )
                    # Add result to messages
                    messages.append({
                        "role": "tool",
                        "name": tool_call.function.name,
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result) if isinstance(result, (dict, list)) else str(result)
                    })

            return response.choices[0].message.content

        except Exception as e:
            error_msg = f"Error in model completion: {str(e)}"
            print(f"❌ {error_msg}")
            raise

    async def _execute_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Any:
        """Execute the actual completion call to the API provider."""
        if self.api_provider == "openai":
            return await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )
        else:
            raise ValueError(f"Unsupported API provider: {self.api_provider}") 
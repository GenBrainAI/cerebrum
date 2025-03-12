from src.server.tools.tools_catalog import ToolsCatalog
from src.server.tools.weather_tool import WeatherTool

def register_weather_tool():
    """Register the weather tool with the ToolsCatalog."""
    print("Registering Weather Tool...")
    
    # Initialize the tools catalog
    catalog = ToolsCatalog()
    
    # Create an instance of the WeatherTool
    weather_tool = WeatherTool()
    
    # Register the WeatherTool instance with the catalog
    registered_names = catalog.register_instance(
        instance=weather_tool,
        name="weather",
        exclude_base_methods=True,
        register_instance_itself=True
    )
    
    print(f"✅ Registered WeatherTool with {len(registered_names)} methods:")
    for name in registered_names:
        print(f"  - {name}")
    
    return registered_names

if __name__ == "__main__":
    register_weather_tool() 
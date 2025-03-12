#!/usr/bin/env python3
"""
Example script showing how to use the WeatherTool in Cerebrum.
"""

import sys
import os
import json
import traceback

# Add the project root to the Python path to help with imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def use_weather_tool():
    """Demonstrate how to use the weather tool in Cerebrum."""
    print("Initializing Cerebrum tools...")
    
    try:
        # Import here to avoid circular imports
        from src.server.tools.weather_tool import WeatherTool
        
        # Create and use the weather tool directly
        weather_tool = WeatherTool()
        
        # Test locations
        test_locations = [
            ("London", "UK"),
            ("New York", "US"),
            ("Tokyo", "JP")
        ]
        
        # Use get_weather method
        print("\nUsing weather.get_weather:")
        for city, country in test_locations:
            try:
                print(f"\nWeather in {city}, {country}:")
                weather_data = weather_tool.get_weather(city, country)
                print(json.dumps(weather_data, indent=2))
            except Exception as e:
                print(f"Error getting weather for {city}, {country}: {str(e)}")
        
        # Use get_forecast method
        print("\nUsing weather.get_forecast:")
        city, country = test_locations[0]  # Use the first location
        try:
            print(f"\nForecast for {city}, {country}:")
            forecast_data = weather_tool.get_forecast(city, country, days=2)
            print(json.dumps(forecast_data, indent=2))
        except Exception as e:
            print(f"Error getting forecast for {city}, {country}: {str(e)}")
            
        print("\nWeather tool integration successful!")
        print("To use the weather tool in the Cerebrum framework:")
        print("1. The tool is registered automatically when the framework initializes")
        print("2. Access it through a CurriedProxy with 'proxy.weather.get_weather' and 'proxy.weather.get_forecast'")
        print("3. Use it in tasks and agents by providing the city and country parameters")
        
    except Exception as e:
        print(f"Error in weather tool example: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    use_weather_tool() 
#!/usr/bin/env python3
"""
Test script for the WeatherTool.
This script tests the WeatherTool directly without using the ToolsCatalog.
"""

from src.server.tools.weather_tool import WeatherTool
import json

def test_weather_tool():
    """Test the WeatherTool's functionality."""
    print("Testing WeatherTool...")
    
    # Create an instance of the WeatherTool
    weather_tool = WeatherTool()
    
    # Test locations
    test_locations = [
        ("London", "UK"),
        ("New York", "US"),
        ("Tokyo", "JP"),
        ("Sydney", "AU"),
        ("Paris", "FR")
    ]
    
    # Test get_weather method
    print("\nTesting get_weather method:")
    for city, country in test_locations:
        try:
            print(f"\nWeather in {city}, {country}:")
            weather_data = weather_tool.get_weather(city, country)
            print(json.dumps(weather_data, indent=2))
        except Exception as e:
            print(f"Error getting weather for {city}, {country}: {str(e)}")
    
    # Test get_forecast method
    print("\nTesting get_forecast method:")
    city, country = test_locations[0]  # Use the first location for forecast test
    try:
        print(f"\nForecast for {city}, {country}:")
        forecast_data = weather_tool.get_forecast(city, country, days=3)
        print(json.dumps(forecast_data, indent=2))
    except Exception as e:
        print(f"Error getting forecast for {city}, {country}: {str(e)}")

if __name__ == "__main__":
    test_weather_tool() 
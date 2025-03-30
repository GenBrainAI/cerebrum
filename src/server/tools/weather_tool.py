import requests
from typing import Dict, Any, Optional
from datetime import datetime
import logging

class WeatherTool:
    """Tool for fetching weather information for a location."""
    
    def __init__(self):
        """Initialize the WeatherTool."""
        # Using WeatherAPI for weather data (has a free tier)
        self.api_base_url = "https://weatherapi-com.p.rapidapi.com/current.json"
        # For RapidAPI, you'd need to sign up for an account and get an API key
        # In a production environment, these should be stored securely as environment variables
        self.headers = {
            "X-RapidAPI-Key": "YOUR_RAPIDAPI_KEY",  # Replace with your RapidAPI key
            "X-RapidAPI-Host": "weatherapi-com.p.rapidapi.com"
        }
    
    def get_weather(self, city: str, country: Optional[str] = None) -> Dict[str, Any]:
        """
        Get current weather information for a specified location.
        
        Args:
            city: The name of the city
            country: Optional country code (e.g., 'US', 'GB', 'JP')
        
        Returns:
            Dictionary containing weather information:
                - temperature: Current temperature in Celsius
                - feels_like: How it feels like in Celsius
                - description: Weather description
                - humidity: Humidity percentage
                - wind_speed: Wind speed in m/s
                - location: Full location name
                - timestamp: Time when data was fetched
        
        Raises:
            Exception: If the weather data cannot be retrieved
        """
        # Special case handling for Paris
        if city and city.lower() == "paris" and not country:
            country = "France"
            logging.info(f"🌍 Added default country (France) for Paris")
        
        # Construct the query parameter
        location_query = city
        if country:
            location_query = f"{city}, {country}"
        
        # Using a public weather API that doesn't require authentication
        # This is a simpler implementation that doesn't require an API key
        url = f"https://wttr.in/{location_query}?format=j1"
        
        # Make the API request
        try:
            response = requests.get(url)
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Parse the JSON response
            weather_data = response.json()
            
            # Extract and format the relevant information from wttr.in API
            current = weather_data.get("current_condition", [{}])[0]
            location_info = weather_data.get("nearest_area", [{}])[0]
            
            location_name = location_info.get("areaName", [{}])[0].get("value", city)
            country_name = location_info.get("country", [{}])[0].get("value", country if country else "")
            
            return {
                "temperature": float(current.get("temp_C", 0)),
                "feels_like": float(current.get("FeelsLikeC", 0)),
                "description": current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
                "humidity": int(current.get("humidity", 0)),
                "wind_speed": float(current.get("windspeedKmph", 0)) / 3.6,  # Convert km/h to m/s
                "precipitation": float(current.get("precipMM", 0)),
                "location": f"{location_name}, {country_name}",
                "timestamp": datetime.now().isoformat()
            }
            
        except requests.exceptions.RequestException as e:
            # Handle any errors that occurred during the request
            raise Exception(f"Failed to retrieve weather data: {str(e)}")
        
        except (KeyError, IndexError, ValueError) as e:
            # Handle errors with parsing the response
            raise Exception(f"Failed to parse weather data: {str(e)}")
    
    def get_forecast(self, city: str, country: Optional[str] = None, days: int = 3) -> Dict[str, Any]:
        """
        Get weather forecast for a specified location.
        
        Args:
            city: The name of the city
            country: Optional country code (e.g., 'US', 'GB', 'JP')
            days: Number of days for forecast (max 3 for the free tier)
        
        Returns:
            Dictionary containing forecast information
        
        Raises:
            Exception: If the forecast data cannot be retrieved
        """
        # Special case handling for Paris
        if city and city.lower() == "paris" and not country:
            country = "France"
            logging.info(f"🌍 Added default country (France) for Paris")
        
        # Construct the query parameter
        location_query = city
        if country:
            location_query = f"{city}, {country}"
        
        # Using wttr.in for forecast data (up to 3 days)
        url = f"https://wttr.in/{location_query}?format=j1"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            weather_data = response.json()
            forecast_data = weather_data.get("weather", [])
            
            # Limit to the requested number of days
            days = min(days, len(forecast_data))
            forecast_data = forecast_data[:days]
            
            location_info = weather_data.get("nearest_area", [{}])[0]
            location_name = location_info.get("areaName", [{}])[0].get("value", city)
            country_name = location_info.get("country", [{}])[0].get("value", country if country else "")
            
            forecasts = []
            for day_data in forecast_data:
                date = day_data.get("date", "Unknown")
                avg_temp = day_data.get("avgtempC", "Unknown")
                max_temp = day_data.get("maxtempC", "Unknown")
                min_temp = day_data.get("mintempC", "Unknown")
                
                # Get hourly data if available
                hourly = day_data.get("hourly", [])
                daily_desc = "No description available"
                
                if hourly and len(hourly) > 0:
                    # Use mid-day description if available
                    mid_day = next((h for h in hourly if h.get("time") == "1200"), hourly[0])
                    weather_desc = mid_day.get("weatherDesc", [{}])
                    if weather_desc and len(weather_desc) > 0:
                        daily_desc = weather_desc[0].get("value", daily_desc)
                
                forecasts.append({
                    "date": date,
                    "avg_temp": avg_temp,
                    "max_temp": max_temp,
                    "min_temp": min_temp,
                    "description": daily_desc
                })
            
            return {
                "location": f"{location_name}, {country_name}",
                "timestamp": datetime.now().isoformat(),
                "forecasts": forecasts
            }
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to retrieve forecast data: {str(e)}")
        
        except (KeyError, IndexError, ValueError) as e:
            raise Exception(f"Failed to parse forecast data: {str(e)}")

# Function to register the weather tool with the catalog
def register_weather_tool(catalog):
    """
    Register the WeatherTool with the provided catalog.
    
    Args:
        catalog: The tools catalog instance
        
    Returns:
        List of registered tool names
    """
    weather_tool = WeatherTool()
    names = catalog.register_instance(
        instance=weather_tool,
        name="weather",
        exclude_base_methods=True,
        register_instance_itself=True
    )
    return names

# Example usage:
# weather_tool = WeatherTool()
# current_weather = weather_tool.get_weather("London", "UK")
# forecast = weather_tool.get_forecast("London", "UK", days=3)
# print(current_weather)
# print(forecast) 
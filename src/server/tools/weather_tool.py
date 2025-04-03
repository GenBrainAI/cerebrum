import requests
from typing import Dict, Any, Optional
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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
        logger.info("🌤️ WeatherTool initialized")
    
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
        logger.info(f"🌤️ Getting weather for city={city}, country={country}")
        
        # Special case handling for Paris
        if city and city.lower() == "paris" and not country:
            country = "France"
            logger.info(f"🌍 Added default country (France) for Paris")
        
        # Construct the query parameter
        location_query = city
        if country:
            location_query = f"{city}, {country}"
        
        logger.info(f"🌍 Constructed location query: {location_query}")
        
        # Using a public weather API that doesn't require authentication
        # This is a simpler implementation that doesn't require an API key
        url = f"https://wttr.in/{location_query}?format=j1"
        logger.info(f"🔗 API URL: {url}")
        
        # Make the API request
        try:
            logger.info(f"📡 Making request to {url}")
            response = requests.get(url)
            
            # Check if the request was successful
            response.raise_for_status()
            
            # Log response status and headers
            logger.info(f"✅ Response status code: {response.status_code}")
            logger.info(f"📋 Response headers: {response.headers}")
            
            # Parse the JSON response
            weather_data = response.json()
            logger.info(f"📊 Response data keys: {weather_data.keys()}")
            
            # Extract and format the relevant information from wttr.in API
            current = weather_data.get("current_condition", [{}])[0]
            location_info = weather_data.get("nearest_area", [{}])[0]
            
            logger.info(f"🌡️ Current condition data: {current}")
            logger.info(f"📍 Location info: {location_info}")
            
            location_name = location_info.get("areaName", [{}])[0].get("value", city)
            country_name = location_info.get("country", [{}])[0].get("value", country if country else "")
            
            result = {
                "temperature": float(current.get("temp_C", 0)),
                "feels_like": float(current.get("FeelsLikeC", 0)),
                "description": current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
                "humidity": int(current.get("humidity", 0)),
                "wind_speed": float(current.get("windspeedKmph", 0)) / 3.6,  # Convert km/h to m/s
                "precipitation": float(current.get("precipMM", 0)),
                "location": f"{location_name}, {country_name}",
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"✅ Successfully parsed weather data: {result}")
            return result
            
        except requests.exceptions.RequestException as e:
            # Handle any errors that occurred during the request
            logger.error(f"❌ Request error: {str(e)}")
            raise Exception(f"Failed to retrieve weather data: {str(e)}")
        
        except (KeyError, IndexError, ValueError) as e:
            # Handle errors with parsing the response
            logger.error(f"❌ Parsing error: {str(e)}")
            if 'response' in locals():
                logger.error(f"❌ Response content: {response.text[:500]}")
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
        # Convert days to integer if it's passed as a string
        try:
            days = int(days)
        except (ValueError, TypeError):
            logger.warning(f"⚠️ Invalid days value: {days}, using default of 3")
            days = 3
            
        logger.info(f"🌤️ Getting forecast for city={city}, country={country}, days={days}")
        
        # Special case handling for Paris
        if city and city.lower() == "paris" and not country:
            country = "France"
            logger.info(f"🌍 Added default country (France) for Paris")
        
        # Construct the query parameter
        location_query = city
        if country:
            location_query = f"{city}, {country}"
        
        logger.info(f"🌍 Constructed location query: {location_query}")
        
        # Using wttr.in for forecast data (up to 3 days)
        url = f"https://wttr.in/{location_query}?format=j1"
        logger.info(f"🔗 API URL: {url}")
        
        try:
            logger.info(f"📡 Making request to {url}")
            response = requests.get(url)
            
            # Log response status and headers
            logger.info(f"✅ Response status code: {response.status_code}")
            logger.info(f"📋 Response headers: {response.headers}")
            
            response.raise_for_status()
            
            weather_data = response.json()
            logger.info(f"📊 Response data keys: {weather_data.keys()}")
            
            forecast_data = weather_data.get("weather", [])
            logger.info(f"📅 Forecast data count: {len(forecast_data)}")
            
            # Limit to the requested number of days
            days = min(days, len(forecast_data))
            forecast_data = forecast_data[:days]
            
            location_info = weather_data.get("nearest_area", [{}])[0]
            logger.info(f"📍 Location info: {location_info}")
            
            location_name = location_info.get("areaName", [{}])[0].get("value", city)
            country_name = location_info.get("country", [{}])[0].get("value", country if country else "")
            
            forecasts = []
            for day_data in forecast_data:
                logger.info(f"📅 Processing day data: {day_data.get('date')}")
                date = day_data.get("date", "Unknown")
                avg_temp = day_data.get("avgtempC", "Unknown")
                max_temp = day_data.get("maxtempC", "Unknown")
                min_temp = day_data.get("mintempC", "Unknown")
                
                # Get hourly data if available
                hourly = day_data.get("hourly", [])
                logger.info(f"🕒 Hourly data count: {len(hourly)}")
                
                daily_desc = "No description available"
                
                if hourly and len(hourly) > 0:
                    # Use mid-day description if available
                    mid_day = next((h for h in hourly if h.get("time") == "1200"), hourly[0])
                    logger.info(f"🕛 Mid-day data: {mid_day}")
                    
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
            
            result = {
                "location": f"{location_name}, {country_name}",
                "timestamp": datetime.now().isoformat(),
                "forecasts": forecasts
            }
            
            logger.info(f"✅ Successfully parsed forecast data: {result}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request error: {str(e)}")
            raise Exception(f"Failed to retrieve forecast data: {str(e)}")
        
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"❌ Parsing error: {str(e)}")
            if 'response' in locals():
                logger.error(f"❌ Response content: {response.text[:500]}")
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
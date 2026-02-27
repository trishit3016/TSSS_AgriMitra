"""Weather service for OpenWeatherMap integration"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Service for fetching weather data from OpenWeatherMap One Call API 3.0.
    
    Features:
    - 8-day weather forecast
    - Precipitation probability, temperature, and humidity
    - Storm risk assessment (48-hour window)
    - Fallback to historical weather averages on API failure
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize weather service.
        
        Args:
            api_key: OpenWeatherMap API key
        """
        self.api_key = api_key or settings.OPENWEATHERMAP_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5/onecall"
        self.has_api_key = bool(self.api_key and self.api_key != "your-openweathermap-api-key")
    
    async def fetch_8day_forecast(
        self,
        latitude: float,
        longitude: float
    ) -> List[Dict[str, Any]]:
        """
        Fetch 8-day weather forecast from OpenWeatherMap.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            
        Returns:
            List of daily forecast dictionaries
        """
        # Check if we have a valid API key
        if not self.has_api_key:
            logger.warning("No valid OpenWeatherMap API key - using mock data")
            return self._generate_mock_forecast()
        
        try:
            logger.info(f"Fetching real weather data for ({latitude}, {longitude})")
            
            # Call OpenWeatherMap One Call API
            url = f"{self.base_url}?lat={latitude}&lon={longitude}&appid={self.api_key}&units=metric&exclude=minutely,hourly,alerts"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            # Parse the daily forecast
            forecast = []
            for day_data in data.get('daily', [])[:8]:  # Get 8 days
                dt = datetime.fromtimestamp(day_data['dt'])
                
                forecast.append({
                    'date': dt.date().isoformat(),
                    'temp_max': day_data['temp']['max'],
                    'temp_min': day_data['temp']['min'],
                    'humidity': day_data['humidity'],
                    'precip_probability': day_data.get('pop', 0.0),  # Probability of precipitation
                    'precip_amount': day_data.get('rain', 0.0),  # Rain in mm
                    'condition': day_data['weather'][0]['main'].lower(),
                    'wind_speed': day_data.get('wind_speed', 0.0)
                })
            
            logger.info(f"✅ Successfully fetched real weather data: {len(forecast)} days")
            return forecast
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenWeatherMap API error: {e.response.status_code} - {e.response.text}")
            return self._generate_mock_forecast()
        except Exception as e:
            logger.error(f"Error fetching weather data: {e}")
            return self._generate_mock_forecast()
    
    def _generate_mock_forecast(self) -> List[Dict[str, Any]]:
        """Generate mock forecast data as fallback"""
        logger.warning("Using MOCK weather data - add OPENWEATHER_API_KEY to .env for real data")
        
        forecast = []
        base_date = datetime.now()
        
        for i in range(8):
            date = base_date + timedelta(days=i)
            forecast.append({
                'date': date.date().isoformat(),
                'temp_max': 32.0 + (i % 3),
                'temp_min': 22.0 + (i % 3),
                'humidity': 75.0 + (i % 10),
                'precip_probability': 0.3 + (i * 0.05),
                'precip_amount': 5.0 if i > 2 else 0.0,
                'condition': 'partly_cloudy' if i < 3 else 'rainy',
                'wind_speed': 15.0 + (i % 5)
            })
        
        return forecast
    
    def parse_forecast(
        self,
        raw_forecast: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Parse raw forecast data and extract key fields.
        
        Args:
            raw_forecast: Raw forecast data from API
            
        Returns:
            Parsed forecast with precipitation, temperature, and humidity
        """
        parsed = []
        
        for day in raw_forecast:
            parsed.append({
                'date': day['date'],
                'temperature': {
                    'max': day['temp_max'],
                    'min': day['temp_min']
                },
                'humidity': day['humidity'],
                'precipitation': {
                    'probability': day['precip_probability'],
                    'amount': day['precip_amount']
                },
                'condition': day['condition'],
                'wind_speed': day.get('wind_speed', 0.0)
            })
        
        return parsed
    
    def assess_storm_risk(
        self,
        forecast: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Assess storm risk within 48-hour window.
        
        Args:
            forecast: Parsed forecast data
            
        Returns:
            Dictionary with storm risk assessment
        """
        # Check first 2 days (48 hours)
        next_48h = forecast[:2]
        
        has_storm_risk = False
        risk_window = None
        impact = None
        
        for i, day in enumerate(next_48h):
            precip_prob = day['precipitation']['probability']
            precip_amount = day['precipitation']['amount']
            wind_speed = day.get('wind_speed', 0.0)
            
            # Storm criteria: high precipitation probability + significant amount
            if precip_prob > 0.6 and precip_amount > 10.0:
                has_storm_risk = True
                risk_window = "next 24 hours" if i == 0 else "24-48 hours"
                
                if precip_amount > 50.0 or wind_speed > 40.0:
                    impact = "Heavy rain and strong winds expected. Harvest immediately to prevent crop damage."
                elif precip_amount > 25.0:
                    impact = "Moderate rain expected. Consider harvesting soon to avoid quality loss."
                else:
                    impact = "Light to moderate rain expected. Monitor conditions closely."
                
                break
        
        return {
            'has_storm_risk': has_storm_risk,
            'risk_window': risk_window,
            'impact': impact
        }
    
    def get_historical_average(
        self,
        latitude: float,
        longitude: float,
        date: datetime
    ) -> Dict[str, Any]:
        """
        Get historical weather average for fallback.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            date: Date for historical data
            
        Returns:
            Historical average weather data
        """
        # Placeholder implementation
        # In production, this would query historical weather database
        
        logger.info(
            f"Fetching historical average for ({latitude}, {longitude}) on {date}"
        )
        
        # Return seasonal averages for India
        month = date.month
        
        # Monsoon season (June-September)
        if 6 <= month <= 9:
            return {
                'temp_max': 30.0,
                'temp_min': 24.0,
                'humidity': 85.0,
                'precip_probability': 0.7,
                'precip_amount': 15.0
            }
        # Winter (December-February)
        elif month in [12, 1, 2]:
            return {
                'temp_max': 25.0,
                'temp_min': 15.0,
                'humidity': 60.0,
                'precip_probability': 0.1,
                'precip_amount': 2.0
            }
        # Summer (March-May)
        else:
            return {
                'temp_max': 38.0,
                'temp_min': 25.0,
                'humidity': 50.0,
                'precip_probability': 0.2,
                'precip_amount': 3.0
            }
    
    async def get_weather_forecast(
        self,
        latitude: float,
        longitude: float,
        use_fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Get complete weather forecast with storm risk assessment.
        
        This is the main entry point for weather data.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            use_fallback: Whether to use historical averages (for testing)
            
        Returns:
            Dictionary containing forecast and risk assessment
        """
        try:
            if use_fallback:
                raise Exception("Using fallback for testing")
            
            # Fetch and parse forecast
            raw_forecast = await self.fetch_8day_forecast(latitude, longitude)
            parsed_forecast = self.parse_forecast(raw_forecast)
            
            # Assess storm risk
            risk_assessment = self.assess_storm_risk(parsed_forecast)
            
            # Determine if using real or mock data
            is_real_data = self.has_api_key
            
            return {
                'forecast': parsed_forecast,
                'risk_assessment': risk_assessment,
                'last_updated': datetime.now().isoformat(),
                'source': 'OpenWeatherMap' if is_real_data else 'Mock_Data',
                'fallback_used': not is_real_data,
                'data_type': 'REAL' if is_real_data else 'MOCK'
            }
            
        except Exception as e:
            logger.warning(f"Weather API failed: {e}. Using historical averages.")
            
            # Fallback to historical averages
            forecast = []
            base_date = datetime.now()
            
            for i in range(8):
                date = base_date + timedelta(days=i)
                historical = self.get_historical_average(latitude, longitude, date)
                
                forecast.append({
                    'date': date.date().isoformat(),
                    'temperature': {
                        'max': historical['temp_max'],
                        'min': historical['temp_min']
                    },
                    'humidity': historical['humidity'],
                    'precipitation': {
                        'probability': historical['precip_probability'],
                        'amount': historical['precip_amount']
                    },
                    'condition': 'historical_average',
                    'wind_speed': 10.0
                })
            
            risk_assessment = self.assess_storm_risk(forecast)
            
            return {
                'forecast': forecast,
                'risk_assessment': risk_assessment,
                'last_updated': datetime.now().isoformat(),
                'source': 'Historical_Average',
                'fallback_used': True,
                'data_type': 'FALLBACK',
                'warning': 'Using historical weather averages due to API unavailability'
            }

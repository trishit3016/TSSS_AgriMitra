"""Supervisor Agent for multi-agent orchestration and recommendation synthesis"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, UTC
import logging

from app.agents.geospatial_agent import GeospatialAgent
from app.agents.agronomist_agent import AgronomistAgent
from app.agents.economist_agent import EconomistAgent
from app.services.weather_service import WeatherService

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """
    Supervisor Agent responsible for:
    - Orchestrating multi-agent workflow (Geospatial, Agronomist, Economist)
    - Synthesizing agent outputs into coherent recommendations
    - Generating explainable reasoning chains
    - Calculating confidence scores and data quality indicators
    - Implementing graceful degradation when data is missing
    
    Requirements: 1.1, 1.5, 3.2, 10.2, 10.5, 10.6
    """
    
    def __init__(self):
        self.geospatial_agent = GeospatialAgent()
        self.agronomist_agent = AgronomistAgent()
        self.economist_agent = EconomistAgent()
        self.weather_service = WeatherService()
    
    async def generate_recommendation(
        self,
        farmer_id: str,
        latitude: float,
        longitude: float,
        crop: str,
        field_size: float,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Generate comprehensive harvest and market recommendation"""
        logger.info(f"Generating recommendation for farmer {farmer_id}: crop={crop}, location=({latitude}, {longitude})")
        
        # Collect data from all agents
        geospatial_data = await self._get_geospatial_data(latitude, longitude)
        weather_data = await self._get_weather_data(latitude, longitude)
        agronomist_data = await self._get_agronomist_data(crop, weather_data.get('current_conditions', {}))
        economist_data = await self._get_economist_data(crop, (latitude, longitude))
        
        # Synthesize recommendation
        recommendation = self._synthesize_recommendation(
            geospatial_data, weather_data, agronomist_data, economist_data, crop, language
        )
        
        # Calculate confidence and data quality
        confidence, data_quality = self._calculate_confidence_and_quality(
            geospatial_data, weather_data, agronomist_data, economist_data
        )
        
        recommendation['confidence'] = confidence
        recommendation['data_quality'] = data_quality
        
        # Generate reasoning chain
        reasoning_chain = self._generate_reasoning_chain(
            recommendation, geospatial_data, weather_data, agronomist_data, economist_data, language
        )
        
        recommendation['reasoning_chain'] = reasoning_chain
        recommendation['timestamp'] = datetime.now(UTC).isoformat()
        
        logger.info(f"Recommendation generated: action={recommendation['action']}, urgency={recommendation['urgency']}, confidence={confidence:.1f}%")
        
        return recommendation
    
    async def _get_geospatial_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get geospatial data from Geospatial Agent"""
        try:
            return await self.geospatial_agent.get_geospatial_data(latitude, longitude)
        except Exception as e:
            logger.error(f"Error getting geospatial data: {e}")
            return {'error': str(e), 'cached': False}
    
    async def _get_weather_data(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get weather forecast and risk assessment"""
        try:
            weather = await self.weather_service.get_weather_forecast(latitude, longitude)
            if weather.get('forecast') and len(weather['forecast']) > 0:
                first_day = weather['forecast'][0]
                weather['current_conditions'] = {
                    'temperature': (first_day['temp_max'] + first_day['temp_min']) / 2,
                    'humidity': first_day['humidity']
                }
            else:
                weather['current_conditions'] = {'temperature': 25.0, 'humidity': 70.0}
            return weather
        except Exception as e:
            logger.error(f"Error getting weather data: {e}")
            return {
                'error': str(e), 'forecast': [],
                'risk_assessment': {'has_storm_risk': False, 'risk_window': None, 'impact': None},
                'current_conditions': {'temperature': 25.0, 'humidity': 70.0}
            }
    
    async def _get_agronomist_data(self, crop: str, current_conditions: Dict[str, float]) -> Dict[str, Any]:
        """Get biological rules and spoilage assessment"""
        try:
            temperature = current_conditions.get('temperature', 25.0)
            humidity = current_conditions.get('humidity', 70.0)
            return self.agronomist_agent.assess_spoilage_risk(crop, temperature, humidity)
        except Exception as e:
            logger.error(f"Error getting agronomist data: {e}")
            return {'error': str(e), 'matched_rules': []}
    
    async def _get_economist_data(self, crop: str, farmer_location: Tuple[float, float]) -> Dict[str, Any]:
        """Get market prices and recommendation"""
        try:
            return self.economist_agent.get_market_recommendation(crop, farmer_location)
        except Exception as e:
            logger.error(f"Error getting economist data: {e}")
            return {'error': str(e), 'best_market': None}
    
    def _synthesize_recommendation(
        self, geospatial_data: Dict[str, Any], weather_data: Dict[str, Any],
        agronomist_data: Dict[str, Any], economist_data: Dict[str, Any],
        crop: str, language: str
    ) -> Dict[str, Any]:
        """Synthesize recommendation from all agent outputs"""
        crop_ready = self._assess_crop_readiness(geospatial_data)
        storm_risk = weather_data.get('risk_assessment', {}).get('has_storm_risk', False)
        spoilage_risk = agronomist_data.get('spoilage_timeline', {}).get('risk_level', 'unknown')
        market_opportunity = economist_data.get('market_opportunity', 'low')
        price_difference = economist_data.get('price_difference', 0.0)
        
        action, urgency, primary_factor = self._determine_action_and_urgency(
            crop_ready, storm_risk, spoilage_risk, market_opportunity, price_difference
        )
        
        primary_message = self._generate_primary_message(
            action, urgency, primary_factor, crop, weather_data, agronomist_data, economist_data, language
        )
        
        reasoning = self._generate_reasoning_summary(
            action, primary_factor, crop_ready, storm_risk, spoilage_risk, market_opportunity, language
        )
        
        return {
            'action': action, 'urgency': urgency, 'primary_message': primary_message,
            'reasoning': reasoning, 'primary_factor': primary_factor, 'crop_ready': crop_ready,
            'indicators': {
                'storm_risk': storm_risk, 'spoilage_risk': spoilage_risk,
                'market_opportunity': market_opportunity, 'price_difference': price_difference
            }
        }
    
    def _assess_crop_readiness(self, geospatial_data: Dict[str, Any]) -> bool:
        """Assess if crop is ready for harvest based on NDVI"""
        ndvi = geospatial_data.get('ndvi')
        if ndvi is None:
            logger.warning("No NDVI data available, assuming crop ready")
            return True
        return ndvi > 0.6
    
    def _determine_action_and_urgency(
        self, crop_ready: bool, storm_risk: bool, spoilage_risk: str,
        market_opportunity: str, price_difference: float
    ) -> Tuple[str, str, str]:
        """Determine action, urgency level, and primary factor"""
        if storm_risk and crop_ready:
            return "harvest_now", "critical", "storm_risk"
        elif storm_risk and not crop_ready:
            return "harvest_now", "high", "storm_risk"
        
        if spoilage_risk == "critical":
            return "harvest_now", "high", "spoilage_risk"
        elif spoilage_risk == "high":
            return "harvest_now", "medium", "spoilage_risk"
        
        if market_opportunity in ["excellent", "good"] and crop_ready:
            if price_difference >= 10:
                return "sell_now", "medium", "market_opportunity"
            else:
                return "sell_now", "low", "market_opportunity"
        
        if spoilage_risk == "medium" and crop_ready:
            return "harvest_now", "low", "spoilage_risk"
        
        return "wait", "low", "optimal_timing"
    
    def _generate_primary_message(
        self, action: str, urgency: str, primary_factor: str, crop: str,
        weather_data: Dict[str, Any], agronomist_data: Dict[str, Any],
        economist_data: Dict[str, Any], language: str
    ) -> str:
        """Generate primary recommendation message"""
        if language == "hi":
            return self._generate_hindi_message(action, urgency, primary_factor, crop, weather_data, agronomist_data, economist_data)
        
        if action == "harvest_now":
            if primary_factor == "storm_risk":
                risk_window = weather_data.get('risk_assessment', {}).get('risk_window', 'soon')
                return f"Harvest your {crop} immediately! Heavy rain expected {risk_window}."
            elif primary_factor == "spoilage_risk":
                time_to_spoilage = agronomist_data.get('spoilage_timeline', {}).get('time_to_spoilage_display', 'soon')
                return f"Harvest your {crop} now! Spoilage risk is high - crop may deteriorate in {time_to_spoilage}."
            else:
                return f"Harvest your {crop} now for best results."
        elif action == "sell_now":
            best_market = economist_data.get('best_market', {}).get('name', 'nearby market')
            price_diff = economist_data.get('price_difference', 0)
            return f"Sell at {best_market} now! You'll earn ₹{price_diff:.2f} more per kg."
        else:
            if primary_factor == "optimal_timing":
                return f"Wait for optimal conditions. Your {crop} will benefit from more time."
            else:
                return f"Monitor conditions closely. We'll alert you when it's time to harvest."
    
    def _generate_hindi_message(
        self, action: str, urgency: str, primary_factor: str, crop: str,
        weather_data: Dict[str, Any], agronomist_data: Dict[str, Any], economist_data: Dict[str, Any]
    ) -> str:
        """Generate primary message in Hindi"""
        crop_hindi = "टमाटर" if crop == "tomato" else "प्याज"
        if action == "harvest_now":
            if primary_factor == "storm_risk":
                return f"अपनी {crop_hindi} की फसल तुरंत काटें! भारी बारिश आने वाली है।"
            elif primary_factor == "spoilage_risk":
                return f"अपनी {crop_hindi} की फसल अभी काटें! खराब होने का खतरा है।"
            else:
                return f"अपनी {crop_hindi} की फसल अभी काटें।"
        elif action == "sell_now":
            best_market = economist_data.get('best_market', {}).get('name', 'बाजार')
            price_diff = economist_data.get('price_difference', 0)
            return f"{best_market} में अभी बेचें! आपको ₹{price_diff:.2f} प्रति किलो अधिक मिलेगा।"
        else:
            return f"इष्टतम स्थितियों की प्रतीक्षा करें। आपकी {crop_hindi} को अधिक समय से लाभ होगा।"
    
    def _generate_reasoning_summary(
        self, action: str, primary_factor: str, crop_ready: bool, storm_risk: bool,
        spoilage_risk: str, market_opportunity: str, language: str
    ) -> str:
        """Generate brief reasoning summary for action banner"""
        if language == "hi":
            return self._generate_hindi_reasoning(action, primary_factor, crop_ready, storm_risk, spoilage_risk, market_opportunity)
        
        reasons = []
        if primary_factor == "storm_risk":
            reasons.append("Heavy rain forecast within 48 hours")
            if crop_ready:
                reasons.append("Crop is ready for harvest")
        elif primary_factor == "spoilage_risk":
            reasons.append(f"Spoilage risk is {spoilage_risk}")
            reasons.append("Current conditions accelerate deterioration")
        elif primary_factor == "market_opportunity":
            reasons.append(f"Market opportunity is {market_opportunity}")
            if crop_ready:
                reasons.append("Crop is ready for sale")
        elif primary_factor == "optimal_timing":
            reasons.append("No immediate threats detected")
            if not crop_ready:
                reasons.append("Crop needs more time to mature")
        
        return " • ".join(reasons)
    
    def _generate_hindi_reasoning(
        self, action: str, primary_factor: str, crop_ready: bool, storm_risk: bool,
        spoilage_risk: str, market_opportunity: str
    ) -> str:
        """Generate reasoning summary in Hindi"""
        reasons = []
        if primary_factor == "storm_risk":
            reasons.append("48 घंटे के भीतर भारी बारिश का पूर्वानुमान")
            if crop_ready:
                reasons.append("फसल कटाई के लिए तैयार है")
        elif primary_factor == "spoilage_risk":
            risk_hindi = {"critical": "गंभीर", "high": "उच्च", "medium": "मध्यम", "low": "कम"}.get(spoilage_risk, spoilage_risk)
            reasons.append(f"खराब होने का जोखिम {risk_hindi} है")
        elif primary_factor == "market_opportunity":
            reasons.append("बाजार में अच्छी कीमत मिल रही है")
        return " • ".join(reasons)
    
    def _calculate_confidence_and_quality(
        self, geospatial_data: Dict[str, Any], weather_data: Dict[str, Any],
        agronomist_data: Dict[str, Any], economist_data: Dict[str, Any]
    ) -> Tuple[float, str]:
        """Calculate confidence score and data quality indicator"""
        confidence = 100.0
        quality_factors = []
        
        if 'error' in geospatial_data:
            confidence -= 25
            quality_factors.append("satellite_error")
        elif not geospatial_data.get('cached', False):
            confidence -= 15
            quality_factors.append("no_satellite_cache")
        elif geospatial_data.get('cache_age_days', 0) > 3:
            confidence -= 10
            quality_factors.append("old_satellite_data")
        
        if 'error' in weather_data:
            confidence -= 20
            quality_factors.append("weather_error")
        elif weather_data.get('fallback_used', False):
            confidence -= 15
            quality_factors.append("weather_fallback")
        
        if 'error' in agronomist_data:
            confidence -= 15
            quality_factors.append("biological_rules_error")
        elif not agronomist_data.get('matched_rules'):
            confidence -= 10
            quality_factors.append("no_matching_rules")
        
        if 'error' in economist_data:
            confidence -= 10
            quality_factors.append("market_error")
        elif economist_data.get('fallback_used', False):
            confidence -= 5
            quality_factors.append("market_fallback")
        elif not economist_data.get('best_market'):
            confidence -= 10
            quality_factors.append("no_market_data")
        
        confidence = max(0.0, min(100.0, confidence))
        
        if confidence >= 90:
            data_quality = "excellent"
        elif confidence >= 75:
            data_quality = "good"
        elif confidence >= 50:
            data_quality = "fair"
        else:
            data_quality = "poor"
        
        logger.info(f"Confidence: {confidence:.1f}%, Quality: {data_quality}, Factors: {quality_factors}")
        
        return confidence, data_quality
    
    def _generate_reasoning_chain(
        self, recommendation: Dict[str, Any], geospatial_data: Dict[str, Any],
        weather_data: Dict[str, Any], agronomist_data: Dict[str, Any],
        economist_data: Dict[str, Any], language: str
    ) -> List[str]:
        """Generate step-by-step reasoning chain"""
        if language == "hi":
            return self._generate_hindi_reasoning_chain(recommendation, geospatial_data, weather_data, agronomist_data, economist_data)
        
        chain = []
        
        # Weather assessment
        risk_assessment = weather_data.get('risk_assessment', {})
        if risk_assessment.get('has_storm_risk'):
            risk_window = risk_assessment.get('risk_window', 'soon')
            impact = risk_assessment.get('impact', 'Heavy rainfall expected')
            chain.append(f"Weather Alert: {impact} {risk_window}.")
        else:
            chain.append("Weather: No immediate storm threats detected in the next 48 hours.")
        
        # Crop readiness
        crop_ready = recommendation.get('crop_ready', False)
        ndvi = geospatial_data.get('ndvi')
        if ndvi is not None:
            chain.append(f"Crop Health: NDVI index is {ndvi:.2f}, indicating {'healthy vegetation ready for harvest' if crop_ready else 'crop needs more time'}.")
        else:
            chain.append("Crop Health: Satellite data unavailable, assessment based on typical growth patterns.")
        
        # Spoilage risk
        timeline = agronomist_data.get('spoilage_timeline', {})
        risk_level = timeline.get('risk_level', 'unknown')
        time_to_spoilage = timeline.get('time_to_spoilage_display', 'unknown')
        
        if risk_level != 'unknown':
            conditions = agronomist_data.get('conditions', {})
            temp = conditions.get('temperature', 0)
            humidity = conditions.get('humidity', 0)
            chain.append(f"Spoilage Risk: {risk_level.capitalize()} - current conditions (temp: {temp:.1f}°C, humidity: {humidity:.0f}%) may cause deterioration in {time_to_spoilage}.")
        else:
            chain.append("Spoilage Risk: Unable to assess due to missing biological rules data.")
        
        # Market analysis
        if economist_data.get('best_market'):
            best_market = economist_data['best_market']
            price_diff = economist_data.get('price_difference', 0)
            
            if price_diff > 0:
                chain.append(f"Market Opportunity: {best_market['name']} is paying ₹{best_market['price_per_kg']:.2f}/kg, which is ₹{price_diff:.2f} more than your local market.")
            else:
                chain.append(f"Market Prices: Your local market offers the best price at ₹{best_market['price_per_kg']:.2f}/kg.")
        else:
            chain.append("Market Prices: Market data unavailable at this time.")
        
        # Final recommendation
        action = recommendation['action']
        primary_factor = recommendation['primary_factor']
        
        factor_explanation = {
            'storm_risk': 'imminent weather threat',
            'spoilage_risk': 'high spoilage risk under current conditions',
            'market_opportunity': 'favorable market prices',
            'optimal_timing': 'no immediate threats or opportunities'
        }.get(primary_factor, 'overall assessment')
        
        action_text = {
            'harvest_now': 'harvest immediately',
            'sell_now': 'sell at the recommended market',
            'wait': 'wait and monitor conditions'
        }.get(action, action)
        
        chain.append(f"Recommendation: Based on {factor_explanation}, we advise you to {action_text}.")
        
        return chain
    
    def _generate_hindi_reasoning_chain(
        self, recommendation: Dict[str, Any], geospatial_data: Dict[str, Any],
        weather_data: Dict[str, Any], agronomist_data: Dict[str, Any], economist_data: Dict[str, Any]
    ) -> List[str]:
        """Generate reasoning chain in Hindi"""
        chain = []
        
        risk_assessment = weather_data.get('risk_assessment', {})
        if risk_assessment.get('has_storm_risk'):
            chain.append("मौसम चेतावनी: अगले 48 घंटों में भारी बारिश की संभावना।")
        else:
            chain.append("मौसम: अगले 48 घंटों में कोई तूफान का खतरा नहीं।")
        
        crop_ready = recommendation.get('crop_ready', False)
        if crop_ready:
            chain.append("फसल स्वास्थ्य: फसल कटाई के लिए तैयार है।")
        else:
            chain.append("फसल स्वास्थ्य: फसल को और समय चाहिए।")
        
        timeline = agronomist_data.get('spoilage_timeline', {})
        risk_level = timeline.get('risk_level', 'unknown')
        if risk_level != 'unknown':
            risk_hindi = {"critical": "गंभीर", "high": "उच्च", "medium": "मध्यम", "low": "कम"}.get(risk_level, risk_level)
            chain.append(f"खराब होने का जोखिम: {risk_hindi}।")
        
        if economist_data.get('best_market'):
            best_market = economist_data['best_market']
            price_diff = economist_data.get('price_difference', 0)
            
            if price_diff > 0:
                chain.append(f"बाजार अवसर: {best_market['name']} में ₹{best_market['price_per_kg']:.2f}/किलो मिल रहा है।")
            else:
                chain.append("बाजार मूल्य: आपके स्थानीय बाजार में सबसे अच्छी कीमत है।")
        
        action = recommendation['action']
        if action == 'harvest_now':
            chain.append("सिफारिश: तुरंत फसल काटें।")
        elif action == 'sell_now':
            chain.append("सिफारिश: अनुशंसित बाजार में बेचें।")
        else:
            chain.append("सिफारिश: प्रतीक्षा करें और स्थितियों की निगरानी करें।")
        
        return chain

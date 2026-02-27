"""Gemini AI service for natural language generation"""

from typing import Dict, Any, Optional
import logging
import google.generativeai as genai

from app.config.settings import settings

logger = logging.getLogger(__name__)


class GeminiService:
    """
    Service for using Google Gemini Pro for natural language generation.
    
    Features:
    - Enhanced conversational responses
    - Natural language explanations of technical data
    - Context-aware recommendations
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini service.
        
        Args:
            api_key: Gemini API key
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.has_api_key = bool(self.api_key and self.api_key != "your-gemini-api-key")
        
        if self.has_api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                logger.info("✅ Gemini Pro initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.has_api_key = False
                self.model = None
        else:
            logger.warning("No Gemini API key - natural language enhancement disabled")
            self.model = None
    
    async def enhance_recommendation_message(
        self,
        recommendation: Dict[str, Any],
        weather_data: Dict[str, Any],
        agronomist_data: Dict[str, Any],
        economist_data: Dict[str, Any],
        language: str = "en"
    ) -> str:
        """
        Use Gemini to generate a natural, conversational recommendation message.
        
        Args:
            recommendation: Base recommendation from supervisor
            weather_data: Weather forecast data
            agronomist_data: Neo4j biological rules data
            economist_data: Market price data
            language: Language code ('en' or 'hi')
            
        Returns:
            Enhanced natural language message
        """
        if not self.has_api_key or not self.model:
            # Fallback to basic message
            return recommendation.get('primary_message', 'Unable to generate recommendation')
        
        try:
            # Build comprehensive context for Gemini
            context = self._build_detailed_context(
                recommendation, weather_data, agronomist_data, economist_data
            )
            
            # Generate enhanced message with ALL the data
            prompt = f"""You are an expert agricultural advisor helping Indian farmers.

Based on this comprehensive analysis:

{context}

Generate a detailed, natural, and actionable recommendation in {'Hindi' if language == 'hi' else 'English'}.

Include:
1. Main recommendation (harvest now, wait, or sell)
2. Primary reason (weather, spoilage risk, or market opportunity)
3. Supporting data from Neo4j biological rules
4. Weather conditions and risks
5. Market prices and opportunities
6. Confidence level and data quality

Be conversational but include all the important data points. Explain how the Neo4j biological rules were matched to current conditions.

Do NOT use markdown formatting. Just natural text with line breaks."""

            response = self.model.generate_content(prompt)
            enhanced_message = response.text.strip()
            
            logger.info("✅ Gemini enhanced the recommendation message")
            return enhanced_message
            
        except Exception as e:
            logger.error(f"Gemini enhancement failed: {e}")
            return recommendation.get('primary_message', 'Unable to generate recommendation')
    
    async def generate_conversational_response(
        self,
        user_query: str,
        recommendation: Dict[str, Any],
        context: Dict[str, Any],
        language: str = "en"
    ) -> str:
        """
        Generate a conversational response to user's specific question.
        
        Args:
            user_query: User's question
            recommendation: Recommendation data
            context: Additional context (weather, neo4j, market data)
            language: Language code
            
        Returns:
            Natural conversational response
        """
        if not self.has_api_key or not self.model:
            return "I can help you with harvest timing and market recommendations. Please ensure Gemini API is configured."
        
        try:
            # Build comprehensive context
            full_context = f"""
User Question: {user_query}

Available Data:
- Action: {recommendation.get('action')}
- Urgency: {recommendation.get('urgency')}
- Confidence: {recommendation.get('confidence')}%
- Weather: {context.get('weather_summary', 'Not available')}
- Neo4j Rules: {context.get('neo4j_summary', 'Not available')}
- Market Prices: {context.get('market_summary', 'Not available')}
- Reasoning: {' | '.join(recommendation.get('reasoning_chain', []))}
"""

            prompt = f"""You are Sodhak AI, a friendly agricultural advisor for Indian farmers.

Context:
{full_context}

Respond to the user's question in {'Hindi' if language == 'hi' else 'English'}.

Guidelines:
- Answer their specific question directly
- Use data from the context to support your answer
- Be conversational and encouraging
- Explain technical terms in simple language
- If you mention Neo4j rules, explain what they mean
- Keep response focused and actionable
- Maximum 6-7 sentences

Response:"""

            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini conversation failed: {e}")
            return "I apologize, but I'm having trouble generating a response. Please try again."
    
    def _build_detailed_context(
        self,
        recommendation: Dict[str, Any],
        weather_data: Dict[str, Any],
        agronomist_data: Dict[str, Any],
        economist_data: Dict[str, Any]
    ) -> str:
        """Build comprehensive context string for Gemini"""
        context_parts = []
        
        # Recommendation
        context_parts.append(f"RECOMMENDATION:")
        context_parts.append(f"- Action: {recommendation.get('action')}")
        context_parts.append(f"- Urgency: {recommendation.get('urgency')}")
        context_parts.append(f"- Primary Factor: {recommendation.get('primary_factor')}")
        context_parts.append(f"- Confidence: {recommendation.get('confidence')}%")
        context_parts.append(f"- Data Quality: {recommendation.get('data_quality')}")
        context_parts.append("")
        
        # Weather
        context_parts.append("WEATHER DATA:")
        risk = weather_data.get('risk_assessment', {})
        if risk.get('has_storm_risk'):
            context_parts.append(f"- Storm Risk: YES - {risk.get('impact')}")
            context_parts.append(f"- Risk Window: {risk.get('risk_window')}")
        else:
            context_parts.append("- Storm Risk: NO - No immediate threats in next 48 hours")
        
        forecast = weather_data.get('forecast', [])
        if forecast:
            first_day = forecast[0]
            context_parts.append(f"- Current Temperature: {first_day.get('temperature', {}).get('max', 0)}°C")
            context_parts.append(f"- Current Humidity: {first_day.get('humidity', 0)}%")
        context_parts.append("")
        
        # Neo4j biological rules - DETAILED
        context_parts.append("NEO4J BIOLOGICAL RULES:")
        matched_rules = agronomist_data.get('matched_rules', [])
        if matched_rules:
            context_parts.append(f"- Matched {len(matched_rules)} biological rule(s) from ICAR/AGROVOC database")
            
            # Primary rule details
            rule = matched_rules[0]
            context_parts.append(f"- Primary Rule: \"{rule.get('condition')}\"")
            context_parts.append(f"- Source: {rule.get('source', {}).get('name')} ({rule.get('source', {}).get('type')})")
            context_parts.append(f"- Credibility: {rule.get('source', {}).get('credibility', 0)}")
            
            # Temperature and humidity ranges
            temp_range = rule.get('temp_range', {})
            humidity_range = rule.get('humidity_range', {})
            context_parts.append(f"- Rule applies when: Temperature {temp_range.get('min')}-{temp_range.get('max')}°C AND Humidity {humidity_range.get('min')}-{humidity_range.get('max')}%")
            
            # Spoilage timeline
            timeline = agronomist_data.get('spoilage_timeline', {})
            context_parts.append(f"- Spoilage Risk Level: {timeline.get('risk_level', 'unknown').upper()}")
            context_parts.append(f"- Time to Spoilage: {timeline.get('time_to_spoilage_display', 'unknown')}")
            context_parts.append(f"- Spoilage Time: {rule.get('spoilage_time_hours', 0)} hours")
            
            # Current conditions
            conditions = agronomist_data.get('conditions', {})
            context_parts.append(f"- Current Conditions: {conditions.get('temperature', 0)}°C, {conditions.get('humidity', 0)}% humidity")
            context_parts.append(f"- Conditions Match Rule: YES")
        else:
            context_parts.append("- No matching biological rules found")
        context_parts.append("")
        
        # Market
        context_parts.append("MARKET DATA:")
        if economist_data.get('best_market'):
            market = economist_data['best_market']
            price_diff = economist_data.get('price_difference', 0)
            context_parts.append(f"- Best Market: {market.get('name')}")
            context_parts.append(f"- Price: ₹{market.get('price_per_kg')}/kg")
            context_parts.append(f"- Distance: {market.get('distance')} km")
            if price_diff > 0:
                context_parts.append(f"- Price Advantage: ₹{price_diff:.2f} more than local market")
                context_parts.append(f"- Extra Income Potential: ₹{price_diff * 100:.0f} per quintal")
        else:
            context_parts.append("- Market data unavailable")
        
        return "\n".join(context_parts)
    
    def _build_context(
        self,
        recommendation: Dict[str, Any],
        weather_data: Dict[str, Any],
        agronomist_data: Dict[str, Any],
        economist_data: Dict[str, Any],
        language: str
    ) -> str:
        """Build context string for Gemini (legacy method)"""
        return self._build_detailed_context(recommendation, weather_data, agronomist_data, economist_data)

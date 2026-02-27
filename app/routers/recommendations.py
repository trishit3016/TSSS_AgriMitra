"""Recommendations API endpoints"""

import json
import logging
from typing import AsyncGenerator
from datetime import datetime, UTC

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.requests import RecommendationRequest
from app.models.responses import (
    ActionBannerData,
    WeatherCardData,
    WeatherForecast,
    RiskAssessment,
    MarketCardData,
    Market,
    MarketRecommendation,
    SpoilageCardData,
    CurrentConditions,
    SpoilageRisk,
    BiologicalRule,
    ReasoningData,
    DataSources,
    DataSource,
    StreamComponent,
)
from app.agents.supervisor_agent import SupervisorAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["recommendations"])


async def generate_recommendation_stream(
    request: RecommendationRequest,
) -> AsyncGenerator[str, None]:
    """
    Generate streaming recommendation response with Server-Sent Events.
    
    Streams UI components in order:
    1. ActionBanner - Primary recommendation
    2. WeatherCard - Weather forecast and risk assessment
    3. MarketCard - Market prices and recommendation
    4. SpoilageCard - Spoilage risk and biological rules
    5. ReasoningData - Detailed reasoning chain
    
    Requirements: 1.1, 1.4, 7.2, 7.3
    """
    supervisor = SupervisorAgent()
    
    try:
        # Generate comprehensive recommendation
        logger.info(
            f"Processing recommendation request: farmer={request.farmer_id}, "
            f"location=({request.location.latitude}, {request.location.longitude}), "
            f"crop={request.crop}"
        )
        
        recommendation = await supervisor.generate_recommendation(
            farmer_id=request.farmer_id,
            latitude=request.location.latitude,
            longitude=request.location.longitude,
            crop=request.crop,
            field_size=request.field_size,
            language=request.language,
        )
        
        # Stream 1: ActionBanner (Primary recommendation)
        action_banner = ActionBannerData(
            action=recommendation["action"],
            urgency=recommendation["urgency"],
            primary_message=recommendation["primary_message"],
            reasoning=recommendation["reasoning"],
            confidence=recommendation["confidence"],
            data_quality=recommendation["data_quality"],
        )
        
        component = StreamComponent(type="action", data=action_banner.model_dump())
        yield f"data: {json.dumps(component.model_dump())}\n\n"
        
        # Get agent data for remaining components
        geospatial_data = await supervisor._get_geospatial_data(
            request.location.latitude, request.location.longitude
        )
        weather_data = await supervisor._get_weather_data(
            request.location.latitude, request.location.longitude
        )
        agronomist_data = await supervisor._get_agronomist_data(
            request.crop, weather_data.get("current_conditions", {})
        )
        economist_data = await supervisor._get_economist_data(
            request.crop, (request.location.latitude, request.location.longitude)
        )
        
        # Stream 2: WeatherCard
        if weather_data and not weather_data.get("error"):
            forecast_list = []
            for day in weather_data.get("forecast", []):
                forecast_list.append(
                    WeatherForecast(
                        date=day["date"],
                        temp_max=day["temp_max"],
                        temp_min=day["temp_min"],
                        humidity=day["humidity"],
                        precip_probability=day["precip_probability"],
                        precip_amount=day["precip_amount"],
                        condition=day["condition"],
                    )
                )
            
            risk_assessment_data = weather_data.get("risk_assessment", {})
            risk_assessment = RiskAssessment(
                has_storm_risk=risk_assessment_data.get("has_storm_risk", False),
                risk_window=risk_assessment_data.get("risk_window", ""),
                impact=risk_assessment_data.get("impact", ""),
            )
            
            weather_card = WeatherCardData(
                forecast=forecast_list,
                risk_assessment=risk_assessment,
                last_updated=datetime.now(UTC).isoformat(),
            )
            
            component = StreamComponent(type="weather", data=weather_card.model_dump())
            yield f"data: {json.dumps(component.model_dump())}\n\n"
        
        # Stream 3: MarketCard
        if economist_data and not economist_data.get("error"):
            markets_list = []
            for market in economist_data.get("markets", []):
                markets_list.append(
                    Market(
                        name=market["name"],
                        location=market["location"],
                        price_per_kg=market["price_per_kg"],
                        distance=market["distance"],
                        last_updated=market.get("last_updated", datetime.now(UTC).isoformat()),
                    )
                )
            
            best_market_data = economist_data.get("best_market", {})
            market_recommendation = MarketRecommendation(
                best_market=best_market_data.get("name", ""),
                price_difference=economist_data.get("price_difference", 0.0),
                reasoning=economist_data.get("reasoning", ""),
            )
            
            market_card = MarketCardData(
                crop=request.crop,
                markets=markets_list,
                recommendation=market_recommendation,
            )
            
            component = StreamComponent(type="market", data=market_card.model_dump())
            yield f"data: {json.dumps(component.model_dump())}\n\n"
        
        # Stream 4: SpoilageCard
        if agronomist_data and not agronomist_data.get("error"):
            conditions = agronomist_data.get("conditions", {})
            current_conditions = CurrentConditions(
                temperature=conditions.get("temperature", 0.0),
                humidity=conditions.get("humidity", 0.0),
            )
            
            timeline = agronomist_data.get("spoilage_timeline", {})
            spoilage_risk = SpoilageRisk(
                level=timeline.get("risk_level", "low"),
                time_to_spoilage=timeline.get("time_to_spoilage_display", "unknown"),
                factors=agronomist_data.get("factors", []),
            )
            
            matched_rules = agronomist_data.get("matched_rules", [])
            if matched_rules:
                rule = matched_rules[0]
                biological_rule = BiologicalRule(
                    source=rule.get("source", "ICAR"),
                    rule=rule.get("condition", ""),
                )
            else:
                biological_rule = BiologicalRule(
                    source="ICAR",
                    rule="Standard post-harvest guidelines apply",
                )
            
            spoilage_card = SpoilageCardData(
                crop=request.crop,
                current_conditions=current_conditions,
                spoilage_risk=spoilage_risk,
                biological_rule=biological_rule,
            )
            
            component = StreamComponent(type="spoilage", data=spoilage_card.model_dump())
            yield f"data: {json.dumps(component.model_dump())}\n\n"
        
        # Stream 5: Reasoning Chain
        data_sources = DataSources(
            satellite=DataSource(
                source="Google Earth Engine (Sentinel-2, NASA SMAP, CHIRPS)",
                timestamp=geospatial_data.get("timestamp", datetime.now(UTC).isoformat())
                if not geospatial_data.get("error")
                else "",
            )
            if not geospatial_data.get("error")
            else None,
            weather=DataSource(
                source="OpenWeatherMap One Call API 3.0",
                timestamp=datetime.now(UTC).isoformat(),
            )
            if not weather_data.get("error")
            else None,
            market=DataSource(
                source="Agmarknet / AIKosh",
                timestamp=datetime.now(UTC).isoformat(),
            )
            if not economist_data.get("error")
            else None,
            biological={
                "source": "Neo4j (ICAR + AGROVOC)",
                "rules_matched": len(agronomist_data.get("matched_rules", [])),
            }
            if not agronomist_data.get("error")
            else None,
        )
        
        reasoning_data = ReasoningData(
            chain=recommendation.get("reasoning_chain", []),
            data_sources=data_sources,
        )
        
        component = StreamComponent(type="reasoning", data=reasoning_data.model_dump())
        yield f"data: {json.dumps(component.model_dump())}\n\n"
        
        logger.info(
            f"Recommendation stream completed: action={recommendation['action']}, "
            f"confidence={recommendation['confidence']:.1f}%"
        )
        
    except ValueError as e:
        # Validation errors (e.g., location bounds)
        logger.error(f"Validation error: {e}")
        error_data = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "recoverable": False,
            }
        }
        yield f"data: {json.dumps(error_data)}\n\n"
        
    except Exception as e:
        # Unexpected errors with graceful degradation
        logger.error(f"Error generating recommendation: {e}", exc_info=True)
        error_data = {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Unable to generate recommendation at this time",
                "details": str(e) if logger.level == logging.DEBUG else None,
                "recoverable": True,
            }
        }
        yield f"data: {json.dumps(error_data)}\n\n"


@router.post(
    "/recommendations",
    response_class=StreamingResponse,
    summary="Generate harvest and market recommendation",
    description="""
    Generate comprehensive harvest timing and market recommendation for a farmer.
    
    This endpoint:
    - Validates location is within India (8-37°N, 68-97°E)
    - Integrates satellite data, weather forecasts, biological rules, and market prices
    - Returns streaming response with Server-Sent Events
    - Implements graceful degradation when data sources are unavailable
    
    The response streams 5 components in order:
    1. ActionBanner - Primary recommendation with urgency level
    2. WeatherCard - 8-day forecast with storm risk assessment
    3. MarketCard - Market prices and best market recommendation
    4. SpoilageCard - Spoilage risk based on biological rules
    5. ReasoningData - Detailed reasoning chain with data sources
    
    Requirements: 1.1, 1.4, 7.2, 7.3
    """,
    responses={
        200: {
            "description": "Streaming recommendation response",
            "content": {
                "text/event-stream": {
                    "example": """data: {"type": "action", "data": {...}}

data: {"type": "weather", "data": {...}}

data: {"type": "market", "data": {...}}

data: {"type": "spoilage", "data": {...}}

data: {"type": "reasoning", "data": {...}}"""
                }
            },
        },
        400: {"description": "Invalid request (e.g., location outside India)"},
        500: {"description": "Internal server error"},
    },
)
async def create_recommendation(request: RecommendationRequest):
    """
    Create harvest and market recommendation with streaming response.
    
    Args:
        request: Recommendation request with farmer location, crop, and preferences
        
    Returns:
        StreamingResponse with Server-Sent Events containing UI components
        
    Raises:
        HTTPException: If request validation fails or internal error occurs
    """
    try:
        return StreamingResponse(
            generate_recommendation_stream(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )
    except Exception as e:
        logger.error(f"Failed to create recommendation stream: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendation",
        )


@router.post("/recommendations/simple")
async def get_recommendation_simple(request: RecommendationRequest):
    """
    Simple JSON endpoint for recommendations (no streaming).
    Uses only Neo4j biological rules - no external APIs needed.
    
    This endpoint works immediately without any API keys!
    """
    supervisor = SupervisorAgent()
    
    try:
        recommendation = await supervisor.generate_recommendation(
            farmer_id=request.farmer_id,
            latitude=request.location.latitude,
            longitude=request.location.longitude,
            crop=request.crop,
            field_size=request.field_size,
            language=request.language,
        )
        
        return {
            "success": True,
            "recommendation": recommendation
        }
        
    except Exception as e:
        logger.error(f"Error generating recommendation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating recommendation: {str(e)}"
        )

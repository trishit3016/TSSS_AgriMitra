"""Response models for API endpoints"""

from datetime import datetime
from typing import List, Literal, Dict, Any, Optional
from pydantic import BaseModel, Field


class ActionBannerData(BaseModel):
    """Data for ActionBanner UI component"""
    action: Literal["harvest_now", "wait", "sell_now"]
    urgency: Literal["critical", "high", "medium", "low"]
    primary_message: str
    reasoning: str
    confidence: float = Field(..., ge=0, le=100)
    data_quality: Literal["excellent", "good", "fair", "poor"]


class WeatherForecast(BaseModel):
    """Single day weather forecast"""
    date: str
    temp_max: float
    temp_min: float
    humidity: float
    precip_probability: float
    precip_amount: float
    condition: str


class RiskAssessment(BaseModel):
    """Weather risk assessment"""
    has_storm_risk: bool
    risk_window: str
    impact: str


class WeatherCardData(BaseModel):
    """Data for WeatherCard UI component"""
    forecast: List[WeatherForecast]
    risk_assessment: RiskAssessment
    last_updated: str


class Market(BaseModel):
    """Market information"""
    name: str
    location: str
    price_per_kg: float
    distance: float
    last_updated: str


class MarketRecommendation(BaseModel):
    """Market recommendation"""
    best_market: str
    price_difference: float
    reasoning: str


class MarketCardData(BaseModel):
    """Data for MarketCard UI component"""
    crop: Literal["tomato", "onion"]
    markets: List[Market]
    recommendation: MarketRecommendation


class CurrentConditions(BaseModel):
    """Current environmental conditions"""
    temperature: float
    humidity: float


class SpoilageRisk(BaseModel):
    """Spoilage risk assessment"""
    level: Literal["critical", "high", "medium", "low"]
    time_to_spoilage: str
    factors: List[str]


class BiologicalRule(BaseModel):
    """Biological rule citation"""
    source: Literal["ICAR", "AGROVOC"]
    rule: str


class SpoilageCardData(BaseModel):
    """Data for SpoilageCard UI component"""
    crop: Literal["tomato", "onion"]
    current_conditions: CurrentConditions
    spoilage_risk: SpoilageRisk
    biological_rule: BiologicalRule


class DataSource(BaseModel):
    """Data source information"""
    source: str
    timestamp: str


class DataSources(BaseModel):
    """All data sources used"""
    satellite: Optional[DataSource] = None
    weather: Optional[DataSource] = None
    market: Optional[DataSource] = None
    biological: Optional[Dict[str, str]] = None


class ReasoningData(BaseModel):
    """Detailed reasoning chain"""
    chain: List[str]
    data_sources: DataSources


class StreamComponent(BaseModel):
    """Streaming UI component"""
    type: Literal["action", "weather", "market", "spoilage", "reasoning"]
    data: Dict[str, Any]


class CacheStatusResponse(BaseModel):
    """Cache status response"""
    cached: bool
    last_updated: Optional[str] = None
    data_age: Optional[float] = None
    expires_in: Optional[float] = None
    
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "cached": True,
                "last_updated": "2024-01-15T10:30:00Z",
                "data_age": 12.5,
                "expires_in": 155.5
            }
        }
    }


class CachePrefetchResponse(BaseModel):
    """Cache prefetch response"""
    task_id: str
    status: Literal["queued", "processing"]
    estimated_time: int


class BiologicalRuleResponse(BaseModel):
    """Single biological rule response"""
    id: str
    condition: str
    spoilage_time: str
    source: Literal["ICAR", "AGROVOC", "FALLBACK"]
    confidence: float = Field(..., ge=0, le=1)
    temp_range: Optional[Dict[str, float]] = None
    humidity_range: Optional[Dict[str, float]] = None
    source_reference: Optional[str] = None


class BiologicalRulesResponse(BaseModel):
    """Biological rules response for a crop"""
    crop: str
    rules: List[BiologicalRuleResponse]
    conditions_applied: Optional[Dict[str, float]] = None
    
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "crop": "tomato",
                "rules": [
                    {
                        "id": "rule_tomato_high_temp",
                        "condition": "High temperature and humidity",
                        "spoilage_time": "2 days",
                        "source": "ICAR",
                        "confidence": 0.95,
                        "temp_range": {"min": 30.0, "max": 45.0},
                        "humidity_range": {"min": 80.0, "max": 100.0},
                        "source_reference": "ICAR Post-Harvest Manual 2020, Page 45"
                    }
                ],
                "conditions_applied": {
                    "temperature": 32.0,
                    "humidity": 85.0
                }
            }
        }
    }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    version: str

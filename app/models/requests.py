"""Request models for API endpoints"""

from typing import Literal
from pydantic import BaseModel, Field, field_validator


class Location(BaseModel):
    """Geographic location coordinates"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")


class RecommendationRequest(BaseModel):
    """Request for harvest and market recommendation"""
    farmer_id: str = Field(..., min_length=1, max_length=255, description="Unique farmer identifier")
    location: Location = Field(..., description="Farm location coordinates")
    crop: Literal["tomato", "onion"] = Field(..., description="Crop type")
    field_size: float = Field(..., gt=0, le=1000, description="Field size in hectares")
    language: Literal["en", "hi"] = Field(default="en", description="Preferred language for explanations")
    
    @field_validator("location")
    @classmethod
    def validate_india_bounds(cls, v: Location) -> Location:
        """Ensure location is within India"""
        if not (8.0 <= v.latitude <= 37.0):
            raise ValueError("Location must be within India (latitude: 8-37°N)")
        if not (68.0 <= v.longitude <= 97.0):
            raise ValueError("Location must be within India (longitude: 68-97°E)")
        return v


class CacheStatusRequest(BaseModel):
    """Request to check cache status for a location"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class CachePrefetchRequest(BaseModel):
    """Request to prefetch satellite data for a location"""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    priority: Literal["high", "normal", "low"] = Field(default="normal")

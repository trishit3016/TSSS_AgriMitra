"""Gemini API endpoints for raw AI responses"""

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gemini", tags=["gemini"])


class RawQueryRequest(BaseModel):
    """Request model for raw Gemini queries"""
    query: str


class RawQueryResponse(BaseModel):
    """Response model for raw Gemini queries"""
    response: str
    model: str = "gemini-pro"


@router.post("/raw", response_model=RawQueryResponse)
async def raw_gemini_query(request: RawQueryRequest):
    """
    Raw Gemini query - NO prompt engineering, just pass user's question directly.
    
    This endpoint sends the user's query directly to Gemini Pro without any
    additional context, system prompts, or data from Neo4j/LangGraph.
    
    Use this when you want pure Gemini responses without agricultural context.
    """
    gemini_service = GeminiService()
    
    if not gemini_service.has_api_key or not gemini_service.model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API is not configured. Please add GEMINI_API_KEY to .env"
        )
    
    try:
        logger.info(f"Raw Gemini query: {request.query[:100]}...")
        
        # Send query directly to Gemini with NO prompt engineering
        response = gemini_service.model.generate_content(request.query)
        response_text = response.text.strip()
        
        logger.info(f"✅ Gemini responded with {len(response_text)} characters")
        
        return RawQueryResponse(
            response=response_text,
            model="gemini-pro"
        )
        
    except Exception as e:
        logger.error(f"Gemini raw query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get response from Gemini: {str(e)}"
        )

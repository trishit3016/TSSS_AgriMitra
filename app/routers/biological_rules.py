"""Biological rules API endpoints"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Path, Query

from app.models.responses import BiologicalRulesResponse, BiologicalRuleResponse
from app.agents.agronomist_agent import AgronomistAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/biological-rules", tags=["biological-rules"])


@router.get(
    "/{crop}",
    response_model=BiologicalRulesResponse,
    summary="Retrieve biological rules for a specific crop",
    description="""
    Retrieve biological spoilage rules for a specific crop (tomato/onion) from the Neo4j graph database.
    
    This endpoint queries the Biological Rules Engine to retrieve crop-specific spoilage rules.
    Rules can be optionally filtered by environmental conditions (temperature and humidity).
    
    When conditions are provided:
    - Returns rules where the current conditions fall within the rule's ranges
    - Rules are ordered by severity (critical > high > medium > low)
    - Returns up to 5 most relevant rules
    
    When conditions are not provided:
    - Returns all rules for the crop (unfiltered)
    
    Each rule includes:
    - Condition description (plain language)
    - Spoilage timeline (human-readable format)
    - Source citation (ICAR/AGROVOC)
    - Confidence level based on source credibility
    - Temperature and humidity ranges
    
    Requirements: 5.4, 5.5
    """,
    responses={
        200: {
            "description": "Biological rules retrieved successfully",
            "content": {
                "application/json": {
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
            },
        },
        400: {"description": "Invalid crop type or conditions"},
        404: {"description": "No rules found for the specified crop"},
        500: {"description": "Internal server error"},
    },
)
async def get_biological_rules(
    crop: str = Path(
        ...,
        description="Crop type (tomato or onion)",
        pattern="^(tomato|onion)$"
    ),
    temperature: Optional[float] = Query(
        None,
        description="Current temperature in Celsius",
        ge=-50,
        le=60
    ),
    humidity: Optional[float] = Query(
        None,
        description="Current humidity percentage",
        ge=0,
        le=100
    ),
):
    """
    Get biological spoilage rules for a specific crop.
    
    Args:
        crop: Crop type ('tomato' or 'onion')
        temperature: Optional current temperature for filtering rules
        humidity: Optional current humidity for filtering rules
        
    Returns:
        BiologicalRulesResponse with matching rules and citations
        
    Raises:
        HTTPException: If crop is invalid or query fails
    """
    try:
        logger.info(
            f"Retrieving biological rules for crop: {crop}, "
            f"temperature: {temperature}, humidity: {humidity}"
        )
        
        # Validate crop type
        if crop.lower() not in ["tomato", "onion"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid crop type: {crop}. Must be 'tomato' or 'onion'."
            )
        
        # Validate that both temperature and humidity are provided together
        if (temperature is not None and humidity is None) or (temperature is None and humidity is not None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both temperature and humidity must be provided together for filtering."
            )
        
        # Initialize Agronomist Agent
        agent = AgronomistAgent()
        
        # Query rules based on whether conditions are provided
        if temperature is not None and humidity is not None:
            # Query with environmental conditions
            rules = agent.query_spoilage_rules(crop, temperature, humidity)
            conditions_applied = {
                "temperature": temperature,
                "humidity": humidity
            }
        else:
            # Query all rules for the crop (no filtering)
            # We'll use a very wide range to get all rules
            rules = agent.query_spoilage_rules(crop, temperature=25.0, humidity=50.0)
            # Actually, let's query without filtering by getting all rules
            # We need to modify the approach - query with extreme ranges
            with agent.driver.session() as session:
                query = """
                MATCH (c:Crop {name: $crop_name})
                -[:HAS_RULE]->(r:SpoilageRule)
                -[:CITES]->(s:Source)
                RETURN r.id as id,
                       r.condition as condition,
                       r.temp_min as temp_min,
                       r.temp_max as temp_max,
                       r.humidity_min as humidity_min,
                       r.humidity_max as humidity_max,
                       r.spoilage_time_hours as spoilage_time_hours,
                       r.severity as severity,
                       r.source_reference as source_reference,
                       s.name as source_name,
                       s.type as source_type,
                       s.credibility as credibility
                ORDER BY 
                    CASE r.severity
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'medium' THEN 3
                        WHEN 'low' THEN 4
                    END,
                    r.spoilage_time_hours ASC
                """
                
                result = session.run(query, crop_name=crop.capitalize())
                
                rules = []
                for record in result:
                    rules.append({
                        'id': record['id'],
                        'condition': record['condition'],
                        'temp_range': {
                            'min': float(record['temp_min']),
                            'max': float(record['temp_max'])
                        },
                        'humidity_range': {
                            'min': float(record['humidity_min']),
                            'max': float(record['humidity_max'])
                        },
                        'spoilage_time_hours': int(record['spoilage_time_hours']),
                        'severity': record['severity'],
                        'source': {
                            'name': record['source_name'],
                            'type': record['source_type'],
                            'reference': record['source_reference'],
                            'credibility': float(record['credibility'])
                        }
                    })
            
            conditions_applied = None
        
        # Check if any rules were found
        if not rules:
            logger.warning(f"No rules found for crop: {crop}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No biological rules found for crop: {crop}"
            )
        
        # Convert rules to response format
        rule_responses = []
        for rule in rules:
            # Convert spoilage time to human-readable format
            hours = rule['spoilage_time_hours']
            if hours < 24:
                spoilage_time = f"{hours} hours"
            elif hours < 168:  # Less than a week
                days = hours // 24
                spoilage_time = f"{days} day{'s' if days > 1 else ''}"
            else:
                weeks = hours // 168
                spoilage_time = f"{weeks} week{'s' if weeks > 1 else ''}"
            
            # Determine source type
            source_type = rule['source']['type']
            if source_type == 'ICAR_Manual':
                source = 'ICAR'
            elif source_type == 'AGROVOC':
                source = 'AGROVOC'
            else:
                source = 'FALLBACK'
            
            rule_responses.append(
                BiologicalRuleResponse(
                    id=rule['id'],
                    condition=rule['condition'],
                    spoilage_time=spoilage_time,
                    source=source,
                    confidence=rule['source']['credibility'],
                    temp_range=rule['temp_range'],
                    humidity_range=rule['humidity_range'],
                    source_reference=rule['source']['reference']
                )
            )
        
        response = BiologicalRulesResponse(
            crop=crop,
            rules=rule_responses,
            conditions_applied=conditions_applied
        )
        
        logger.info(
            f"Retrieved {len(rule_responses)} rules for {crop}"
            + (f" with conditions (temp={temperature}, humidity={humidity})" if conditions_applied else "")
        )
        
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving biological rules: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve biological rules"
        )

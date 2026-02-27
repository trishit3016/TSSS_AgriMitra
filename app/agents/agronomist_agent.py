"""Agronomist Agent for biological rules and spoilage assessment using GraphRAG"""

from typing import Optional, Dict, Any, List
from datetime import datetime, UTC
import logging

from app.db.neo4j_client import get_neo4j_driver
from neo4j.exceptions import ServiceUnavailable

logger = logging.getLogger(__name__)


class AgronomistAgent:
    """
    Agronomist Agent responsible for:
    - Querying Neo4j biological rules engine
    - Matching environmental conditions to spoilage rules
    - Calculating spoilage timelines
    - Providing ICAR/AGROVOC citations for explainability
    - Graph traversal for related agricultural concepts
    
    Requirements: 5.4, 5.5, 5.6
    """
    
    def __init__(self):
        self.driver = get_neo4j_driver()
    
    def query_spoilage_rules(
        self,
        crop: str,
        temperature: float,
        humidity: float
    ) -> List[Dict[str, Any]]:
        """
        Query Neo4j for spoilage rules matching environmental conditions.
        
        Uses GraphRAG pattern to find rules where current conditions fall
        within the rule's temperature and humidity ranges.
        
        Args:
            crop: Crop name ('tomato' or 'onion')
            temperature: Current temperature in Celsius
            humidity: Current humidity percentage (0-100)
            
        Returns:
            List of matching rules with citations, ordered by severity
            
        Validates: Requirements 5.4 (environmental condition rule matching)
        """
        try:
            with self.driver.session() as session:
                # Query for rules matching current conditions
                query = """
                MATCH (c:Crop {name: $crop_name})
                -[:HAS_RULE]->(r:SpoilageRule)
                -[:CITES]->(s:Source)
                WHERE r.temp_min <= $temperature <= r.temp_max
                  AND r.humidity_min <= $humidity <= r.humidity_max
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
                LIMIT 5
                """
                
                result = session.run(
                    query,
                    crop_name=crop.capitalize(),
                    temperature=temperature,
                    humidity=humidity
                )
                
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
                
                logger.info(
                    f"Found {len(rules)} matching rules for {crop} "
                    f"(temp: {temperature}°C, humidity: {humidity}%)"
                )
                
                return rules
                
        except ServiceUnavailable as e:
            logger.error(f"Neo4j unavailable: {e}")
            # Return default conservative rules as fallback
            return self._get_default_rules(crop)
        except Exception as e:
            logger.error(f"Error querying spoilage rules: {e}")
            return self._get_default_rules(crop)
    
    def calculate_spoilage_timeline(
        self,
        rules: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate spoilage timeline from matched rules.
        
        Uses the most severe (shortest time) rule to determine timeline.
        
        Args:
            rules: List of matched spoilage rules
            
        Returns:
            Dictionary with spoilage timeline and risk assessment
        """
        if not rules:
            return {
                'time_to_spoilage_hours': None,
                'time_to_spoilage_display': 'Unknown',
                'risk_level': 'unknown',
                'primary_rule': None
            }
        
        # Use the first rule (most severe due to ordering)
        primary_rule = rules[0]
        hours = primary_rule['spoilage_time_hours']
        
        # Convert hours to human-readable format
        if hours < 24:
            display = f"{hours} hours"
        elif hours < 168:  # Less than a week
            days = hours // 24
            display = f"{days} day{'s' if days > 1 else ''}"
        else:
            weeks = hours // 168
            display = f"{weeks} week{'s' if weeks > 1 else ''}"
        
        return {
            'time_to_spoilage_hours': hours,
            'time_to_spoilage_display': display,
            'risk_level': primary_rule['severity'],
            'primary_rule': primary_rule
        }
    
    def get_crop_related_concepts(
        self,
        crop: str,
        relationship_types: Optional[List[str]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Traverse graph to find related agricultural concepts.
        
        Supports graph traversal for:
        - Related conditions (REQUIRES relationship)
        - Related crops (RELATED_TO relationship)
        - All spoilage rules (HAS_RULE relationship)
        
        Args:
            crop: Crop name
            relationship_types: List of relationship types to traverse
                               (defaults to ['REQUIRES', 'HAS_RULE'])
            
        Returns:
            Dictionary mapping relationship types to related nodes
            
        Validates: Requirements 5.6 (graph traversal for related concepts)
        """
        if relationship_types is None:
            relationship_types = ['REQUIRES', 'HAS_RULE']
        
        try:
            with self.driver.session() as session:
                related_concepts = {}
                
                # Query for each relationship type
                for rel_type in relationship_types:
                    if rel_type == 'REQUIRES':
                        query = """
                        MATCH (c:Crop {name: $crop_name})
                        -[r:REQUIRES]->(cond:Condition)
                        RETURN cond.name as name,
                               cond.type as type,
                               cond.optimal_min as optimal_min,
                               cond.optimal_max as optimal_max,
                               cond.description as description,
                               r.importance as importance
                        """
                        result = session.run(query, crop_name=crop.capitalize())
                        
                        conditions = []
                        for record in result:
                            conditions.append({
                                'name': record['name'],
                                'type': record['type'],
                                'optimal_range': {
                                    'min': float(record['optimal_min']) if record['optimal_min'] else None,
                                    'max': float(record['optimal_max']) if record['optimal_max'] else None
                                },
                                'description': record['description'],
                                'importance': record['importance']
                            })
                        
                        related_concepts['conditions'] = conditions
                    
                    elif rel_type == 'HAS_RULE':
                        query = """
                        MATCH (c:Crop {name: $crop_name})
                        -[:HAS_RULE]->(r:SpoilageRule)
                        RETURN count(r) as rule_count,
                               collect(DISTINCT r.severity) as severities
                        """
                        result = session.run(query, crop_name=crop.capitalize())
                        record = result.single()
                        
                        if record:
                            related_concepts['rules_summary'] = {
                                'total_rules': record['rule_count'],
                                'severity_levels': record['severities']
                            }
                    
                    elif rel_type == 'RELATED_TO':
                        query = """
                        MATCH (c:Crop {name: $crop_name})
                        -[r:RELATED_TO]->(related:Crop)
                        RETURN related.name as name,
                               related.scientific_name as scientific_name,
                               r.relationship_type as relationship_type
                        """
                        result = session.run(query, crop_name=crop.capitalize())
                        
                        related_crops = []
                        for record in result:
                            related_crops.append({
                                'name': record['name'],
                                'scientific_name': record['scientific_name'],
                                'relationship_type': record['relationship_type']
                            })
                        
                        related_concepts['related_crops'] = related_crops
                
                logger.info(f"Retrieved related concepts for {crop}: {list(related_concepts.keys())}")
                return related_concepts
                
        except Exception as e:
            logger.error(f"Error traversing graph for related concepts: {e}")
            return {}
    
    def assess_spoilage_risk(
        self,
        crop: str,
        temperature: float,
        humidity: float
    ) -> Dict[str, Any]:
        """
        Comprehensive spoilage risk assessment.
        
        This is the main entry point for the Agronomist Agent.
        Combines rule matching, timeline calculation, and citations.
        
        Args:
            crop: Crop name ('tomato' or 'onion')
            temperature: Current temperature in Celsius
            humidity: Current humidity percentage (0-100)
            
        Returns:
            Complete spoilage assessment with rules, timeline, and citations
            
        Validates: Requirements 5.4, 5.5 (biological rule validation)
        """
        # Query matching rules
        rules = self.query_spoilage_rules(crop, temperature, humidity)
        
        # Calculate timeline
        timeline = self.calculate_spoilage_timeline(rules)
        
        # Get related concepts for additional context
        related = self.get_crop_related_concepts(crop)
        
        # Build assessment
        assessment = {
            'crop': crop,
            'conditions': {
                'temperature': temperature,
                'humidity': humidity
            },
            'matched_rules': rules,
            'spoilage_timeline': timeline,
            'risk_factors': self._extract_risk_factors(rules),
            'citations': self._generate_citations(rules),
            'related_concepts': related,
            'timestamp': datetime.now(UTC).isoformat()
        }
        
        logger.info(
            f"Spoilage assessment for {crop}: "
            f"risk={timeline['risk_level']}, "
            f"time={timeline['time_to_spoilage_display']}"
        )
        
        return assessment
    
    def _extract_risk_factors(self, rules: List[Dict[str, Any]]) -> List[str]:
        """
        Extract plain-language risk factors from rules.
        
        Args:
            rules: List of matched rules
            
        Returns:
            List of risk factor descriptions
        """
        if not rules:
            return []
        
        factors = []
        primary_rule = rules[0]
        
        # Analyze temperature
        temp_range = primary_rule['temp_range']
        if temp_range['max'] > 30:
            factors.append("High temperature accelerating spoilage")
        elif temp_range['min'] < 10:
            factors.append("Low temperature risk (chilling injury)")
        
        # Analyze humidity
        humidity_range = primary_rule['humidity_range']
        if humidity_range['min'] > 85:
            factors.append("High humidity promoting fungal growth")
        elif humidity_range['max'] < 70:
            factors.append("Low humidity causing dehydration")
        
        # Add condition description
        factors.append(primary_rule['condition'])
        
        return factors
    
    def _generate_citations(self, rules: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Generate ICAR/AGROVOC citations from rules.
        
        Args:
            rules: List of matched rules
            
        Returns:
            List of citation dictionaries
        """
        citations = []
        seen_sources = set()
        
        for rule in rules:
            source = rule['source']
            source_key = f"{source['type']}:{source['reference']}"
            
            if source_key not in seen_sources:
                citations.append({
                    'source': source['name'],
                    'type': source['type'],
                    'reference': source['reference'],
                    'credibility': source['credibility']
                })
                seen_sources.add(source_key)
        
        return citations
    
    def _get_default_rules(self, crop: str) -> List[Dict[str, Any]]:
        """
        Fallback default rules when Neo4j is unavailable.
        
        Conservative rules to ensure system continues functioning.
        
        Args:
            crop: Crop name
            
        Returns:
            List of default rules
        """
        logger.warning(f"Using default fallback rules for {crop}")
        
        if crop.lower() == 'tomato':
            return [{
                'id': 'default_tomato',
                'condition': 'Default conservative rule (database unavailable)',
                'temp_range': {'min': 0, 'max': 50},
                'humidity_range': {'min': 0, 'max': 100},
                'spoilage_time_hours': 72,
                'severity': 'high',
                'source': {
                    'name': 'Default Rules',
                    'type': 'FALLBACK',
                    'reference': 'Conservative estimate',
                    'credibility': 0.5
                }
            }]
        elif crop.lower() == 'onion':
            return [{
                'id': 'default_onion',
                'condition': 'Default conservative rule (database unavailable)',
                'temp_range': {'min': 0, 'max': 50},
                'humidity_range': {'min': 0, 'max': 100},
                'spoilage_time_hours': 168,
                'severity': 'medium',
                'source': {
                    'name': 'Default Rules',
                    'type': 'FALLBACK',
                    'reference': 'Conservative estimate',
                    'credibility': 0.5
                }
            }]
        else:
            return []

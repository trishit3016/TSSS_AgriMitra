"""
Integration tests for Agronomist Agent with Neo4j

These tests verify the Agronomist Agent works correctly with the actual Neo4j database.
They require Neo4j credentials to be configured in .env file.

Requirements: 5.4, 5.5, 5.6
"""

import pytest
import os
from dotenv import load_dotenv

from app.agents.agronomist_agent import AgronomistAgent

load_dotenv()


@pytest.fixture(scope="module")
def agronomist_agent():
    """Create AgronomistAgent instance"""
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    
    if not neo4j_uri or not neo4j_user or not neo4j_password:
        pytest.skip("Neo4j credentials not configured")
    
    return AgronomistAgent()


class TestAgronomistAgentIntegration:
    """Integration tests for Agronomist Agent"""
    
    def test_query_tomato_critical_conditions(self, agronomist_agent):
        """Test querying tomato rules for critical conditions"""
        # High temperature and high humidity - critical for tomatoes
        rules = agronomist_agent.query_spoilage_rules(
            crop='tomato',
            temperature=32.0,
            humidity=90.0
        )
        
        assert len(rules) > 0, "Should find matching rules"
        assert rules[0]['severity'] in ['critical', 'high'], "Should be critical/high severity"
        assert rules[0]['spoilage_time_hours'] <= 96, "Should have short spoilage time"
        assert 'ICAR' in rules[0]['source']['type'], "Should cite ICAR source"
    
    def test_query_tomato_optimal_conditions(self, agronomist_agent):
        """Test querying tomato rules for optimal storage"""
        # Optimal storage conditions for tomatoes
        rules = agronomist_agent.query_spoilage_rules(
            crop='tomato',
            temperature=13.0,
            humidity=90.0
        )
        
        assert len(rules) > 0, "Should find matching rules"
        assert rules[0]['severity'] in ['low', 'medium'], "Should be low/medium severity"
        assert rules[0]['spoilage_time_hours'] >= 168, "Should have long spoilage time"
    
    def test_query_onion_high_humidity(self, agronomist_agent):
        """Test querying onion rules for high humidity (sprouting risk)"""
        # High humidity - critical for onions (sprouting)
        rules = agronomist_agent.query_spoilage_rules(
            crop='onion',
            temperature=25.0,
            humidity=90.0
        )
        
        assert len(rules) > 0, "Should find matching rules"
        assert rules[0]['severity'] == 'critical', "Should be critical severity"
        assert 'sprout' in rules[0]['condition'].lower() or 'humidity' in rules[0]['condition'].lower()
    
    def test_query_onion_optimal_storage(self, agronomist_agent):
        """Test querying onion rules for optimal cold storage"""
        # Optimal cold storage for onions
        rules = agronomist_agent.query_spoilage_rules(
            crop='onion',
            temperature=2.0,
            humidity=68.0
        )
        
        assert len(rules) > 0, "Should find matching rules"
        assert rules[0]['severity'] == 'low', "Should be low severity"
        assert rules[0]['spoilage_time_hours'] >= 2160, "Should have very long spoilage time"
    
    def test_calculate_spoilage_timeline(self, agronomist_agent):
        """Test spoilage timeline calculation"""
        # Get rules for critical conditions
        rules = agronomist_agent.query_spoilage_rules(
            crop='tomato',
            temperature=32.0,
            humidity=90.0
        )
        
        timeline = agronomist_agent.calculate_spoilage_timeline(rules)
        
        assert timeline['time_to_spoilage_hours'] is not None
        assert timeline['time_to_spoilage_display'] != 'Unknown'
        assert timeline['risk_level'] in ['critical', 'high', 'medium', 'low']
        assert timeline['primary_rule'] is not None
    
    def test_assess_spoilage_risk_complete(self, agronomist_agent):
        """Test complete spoilage risk assessment"""
        assessment = agronomist_agent.assess_spoilage_risk(
            crop='tomato',
            temperature=30.0,
            humidity=85.0
        )
        
        # Verify assessment structure
        assert assessment['crop'] == 'tomato'
        assert assessment['conditions']['temperature'] == 30.0
        assert assessment['conditions']['humidity'] == 85.0
        assert len(assessment['matched_rules']) > 0
        assert 'spoilage_timeline' in assessment
        assert len(assessment['risk_factors']) > 0
        assert len(assessment['citations']) > 0
        assert 'timestamp' in assessment
    
    def test_get_crop_related_concepts(self, agronomist_agent):
        """Test graph traversal for related concepts"""
        concepts = agronomist_agent.get_crop_related_concepts(
            crop='tomato',
            relationship_types=['REQUIRES', 'HAS_RULE']
        )
        
        # Should have rules summary
        assert 'rules_summary' in concepts
        assert concepts['rules_summary']['total_rules'] >= 8
        assert 'critical' in concepts['rules_summary']['severity_levels']
    
    def test_crop_specific_differentiation(self, agronomist_agent):
        """Test that tomato and onion get different rules for same conditions"""
        # Same environmental conditions
        temp = 25.0
        humidity = 80.0
        
        tomato_rules = agronomist_agent.query_spoilage_rules('tomato', temp, humidity)
        onion_rules = agronomist_agent.query_spoilage_rules('onion', temp, humidity)
        
        assert len(tomato_rules) > 0, "Should find tomato rules"
        assert len(onion_rules) > 0, "Should find onion rules"
        
        # Tomatoes should spoil faster than onions
        tomato_time = tomato_rules[0]['spoilage_time_hours']
        onion_time = onion_rules[0]['spoilage_time_hours']
        
        assert tomato_time < onion_time, \
            f"Tomatoes should spoil faster ({tomato_time}h) than onions ({onion_time}h)"
    
    def test_citations_include_icar(self, agronomist_agent):
        """Test that citations include ICAR sources"""
        assessment = agronomist_agent.assess_spoilage_risk(
            crop='tomato',
            temperature=30.0,
            humidity=90.0
        )
        
        citations = assessment['citations']
        assert len(citations) > 0, "Should have citations"
        
        # At least one citation should be from ICAR
        icar_citations = [c for c in citations if 'ICAR' in c['type']]
        assert len(icar_citations) > 0, "Should have ICAR citations"
        assert icar_citations[0]['credibility'] >= 0.9, "ICAR should have high credibility"
    
    def test_risk_factors_extraction(self, agronomist_agent):
        """Test risk factor extraction"""
        assessment = agronomist_agent.assess_spoilage_risk(
            crop='tomato',
            temperature=32.0,
            humidity=90.0
        )
        
        risk_factors = assessment['risk_factors']
        assert len(risk_factors) > 0, "Should have risk factors"
        
        # Should mention temperature or humidity
        factors_text = ' '.join(risk_factors).lower()
        assert 'temperature' in factors_text or 'humidity' in factors_text, \
            "Risk factors should mention environmental conditions"

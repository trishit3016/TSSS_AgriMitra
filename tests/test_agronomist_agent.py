"""Unit tests for Agronomist Agent"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.agents.agronomist_agent import AgronomistAgent


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver"""
    with patch('app.agents.agronomist_agent.get_neo4j_driver') as mock:
        driver = Mock()
        session = Mock()
        driver.session.return_value.__enter__ = Mock(return_value=session)
        driver.session.return_value.__exit__ = Mock(return_value=None)
        mock.return_value = driver
        yield driver, session


@pytest.fixture
def agronomist_agent(mock_neo4j_driver):
    """Create AgronomistAgent instance with mocked driver"""
    return AgronomistAgent()


class TestQuerySpoilageRules:
    """Test spoilage rule querying"""
    
    def test_query_rules_with_matching_conditions(self, agronomist_agent, mock_neo4j_driver):
        """Test querying rules that match environmental conditions"""
        driver, session = mock_neo4j_driver
        
        # Mock query result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([
            {
                'id': 'icar_tomato_high_temp_high_humidity',
                'condition': 'High temperature with high humidity',
                'temp_min': 28.0,
                'temp_max': 35.0,
                'humidity_min': 85.0,
                'humidity_max': 100.0,
                'spoilage_time_hours': 48,
                'severity': 'critical',
                'source_reference': 'ICAR Post-Harvest Manual 2020, Section 3.2.2',
                'source_name': 'ICAR Post-Harvest Management Manual',
                'source_type': 'ICAR_Manual',
                'credibility': 0.95
            }
        ]))
        
        session.run.return_value = mock_result
        
        # Query rules
        rules = agronomist_agent.query_spoilage_rules(
            crop='tomato',
            temperature=30.0,
            humidity=90.0
        )
        
        # Verify
        assert len(rules) == 1
        assert rules[0]['id'] == 'icar_tomato_high_temp_high_humidity'
        assert rules[0]['severity'] == 'critical'
        assert rules[0]['spoilage_time_hours'] == 48
        assert rules[0]['source']['type'] == 'ICAR_Manual'
        assert rules[0]['source']['credibility'] == 0.95
        
        # Verify query was called with correct parameters
        session.run.assert_called_once()
        call_args = session.run.call_args
        assert call_args[1]['crop_name'] == 'Tomato'
        assert call_args[1]['temperature'] == 30.0
        assert call_args[1]['humidity'] == 90.0
    
    def test_query_rules_multiple_matches(self, agronomist_agent, mock_neo4j_driver):
        """Test querying when multiple rules match"""
        driver, session = mock_neo4j_driver
        
        # Mock multiple results
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([
            {
                'id': 'rule1',
                'condition': 'Critical condition',
                'temp_min': 25.0,
                'temp_max': 35.0,
                'humidity_min': 80.0,
                'humidity_max': 100.0,
                'spoilage_time_hours': 48,
                'severity': 'critical',
                'source_reference': 'ICAR Manual',
                'source_name': 'ICAR',
                'source_type': 'ICAR_Manual',
                'credibility': 0.95
            },
            {
                'id': 'rule2',
                'condition': 'High risk condition',
                'temp_min': 20.0,
                'temp_max': 30.0,
                'humidity_min': 70.0,
                'humidity_max': 90.0,
                'spoilage_time_hours': 72,
                'severity': 'high',
                'source_reference': 'ICAR Manual',
                'source_name': 'ICAR',
                'source_type': 'ICAR_Manual',
                'credibility': 0.95
            }
        ]))
        
        session.run.return_value = mock_result
        
        # Query rules
        rules = agronomist_agent.query_spoilage_rules(
            crop='tomato',
            temperature=28.0,
            humidity=85.0
        )
        
        # Verify multiple rules returned
        assert len(rules) == 2
        assert rules[0]['severity'] == 'critical'
        assert rules[1]['severity'] == 'high'
    
    def test_query_rules_no_matches(self, agronomist_agent, mock_neo4j_driver):
        """Test querying when no rules match"""
        driver, session = mock_neo4j_driver
        
        # Mock empty result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        session.run.return_value = mock_result
        
        # Query rules
        rules = agronomist_agent.query_spoilage_rules(
            crop='tomato',
            temperature=15.0,
            humidity=75.0
        )
        
        # Verify empty list
        assert len(rules) == 0
    
    def test_query_rules_neo4j_unavailable(self, agronomist_agent, mock_neo4j_driver):
        """Test fallback when Neo4j is unavailable"""
        from neo4j.exceptions import ServiceUnavailable
        
        driver, session = mock_neo4j_driver
        session.run.side_effect = ServiceUnavailable("Connection failed")
        
        # Query rules
        rules = agronomist_agent.query_spoilage_rules(
            crop='tomato',
            temperature=30.0,
            humidity=90.0
        )
        
        # Verify fallback rules returned
        assert len(rules) == 1
        assert rules[0]['id'] == 'default_tomato'
        assert rules[0]['source']['type'] == 'FALLBACK'
    
    def test_query_rules_onion(self, agronomist_agent, mock_neo4j_driver):
        """Test querying rules for onion crop"""
        driver, session = mock_neo4j_driver
        
        # Mock onion rule
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([
            {
                'id': 'icar_onion_high_humidity',
                'condition': 'High humidity causing sprouting',
                'temp_min': 20.0,
                'temp_max': 30.0,
                'humidity_min': 85.0,
                'humidity_max': 100.0,
                'spoilage_time_hours': 168,
                'severity': 'critical',
                'source_reference': 'ICAR Post-Harvest Manual 2020, Section 4.3.2',
                'source_name': 'ICAR Post-Harvest Management Manual',
                'source_type': 'ICAR_Manual',
                'credibility': 0.95
            }
        ]))
        
        session.run.return_value = mock_result
        
        # Query rules
        rules = agronomist_agent.query_spoilage_rules(
            crop='onion',
            temperature=25.0,
            humidity=90.0
        )
        
        # Verify onion-specific rule
        assert len(rules) == 1
        assert 'onion' in rules[0]['id']
        assert 'sprouting' in rules[0]['condition'].lower()


class TestCalculateSpoilageTimeline:
    """Test spoilage timeline calculation"""
    
    def test_calculate_timeline_critical_rule(self, agronomist_agent):
        """Test timeline calculation for critical severity rule"""
        rules = [{
            'id': 'test_rule',
            'condition': 'Critical condition',
            'spoilage_time_hours': 48,
            'severity': 'critical'
        }]
        
        timeline = agronomist_agent.calculate_spoilage_timeline(rules)
        
        assert timeline['time_to_spoilage_hours'] == 48
        assert timeline['time_to_spoilage_display'] == '2 days'
        assert timeline['risk_level'] == 'critical'
        assert timeline['primary_rule'] == rules[0]
    
    def test_calculate_timeline_hours(self, agronomist_agent):
        """Test timeline display for hours"""
        rules = [{
            'id': 'test_rule',
            'condition': 'Test',
            'spoilage_time_hours': 12,
            'severity': 'critical'
        }]
        
        timeline = agronomist_agent.calculate_spoilage_timeline(rules)
        
        assert timeline['time_to_spoilage_display'] == '12 hours'
    
    def test_calculate_timeline_days(self, agronomist_agent):
        """Test timeline display for days"""
        rules = [{
            'id': 'test_rule',
            'condition': 'Test',
            'spoilage_time_hours': 72,
            'severity': 'high'
        }]
        
        timeline = agronomist_agent.calculate_spoilage_timeline(rules)
        
        assert timeline['time_to_spoilage_display'] == '3 days'
    
    def test_calculate_timeline_weeks(self, agronomist_agent):
        """Test timeline display for weeks"""
        rules = [{
            'id': 'test_rule',
            'condition': 'Test',
            'spoilage_time_hours': 336,  # 2 weeks
            'severity': 'low'
        }]
        
        timeline = agronomist_agent.calculate_spoilage_timeline(rules)
        
        assert timeline['time_to_spoilage_display'] == '2 weeks'
    
    def test_calculate_timeline_no_rules(self, agronomist_agent):
        """Test timeline calculation with no rules"""
        timeline = agronomist_agent.calculate_spoilage_timeline([])
        
        assert timeline['time_to_spoilage_hours'] is None
        assert timeline['time_to_spoilage_display'] == 'Unknown'
        assert timeline['risk_level'] == 'unknown'
        assert timeline['primary_rule'] is None


class TestGetCropRelatedConcepts:
    """Test graph traversal for related concepts"""
    
    def test_get_related_conditions(self, agronomist_agent, mock_neo4j_driver):
        """Test retrieving related conditions"""
        driver, session = mock_neo4j_driver
        
        # Mock conditions result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([
            {
                'name': 'High Temperature and Humidity',
                'type': 'environmental',
                'optimal_min': 12.0,
                'optimal_max': 15.0,
                'description': 'Optimal storage conditions',
                'importance': 'high'
            }
        ]))
        
        session.run.return_value = mock_result
        
        # Get related concepts
        concepts = agronomist_agent.get_crop_related_concepts(
            crop='tomato',
            relationship_types=['REQUIRES']
        )
        
        # Verify
        assert 'conditions' in concepts
        assert len(concepts['conditions']) == 1
        assert concepts['conditions'][0]['name'] == 'High Temperature and Humidity'
        assert concepts['conditions'][0]['importance'] == 'high'
    
    def test_get_rules_summary(self, agronomist_agent, mock_neo4j_driver):
        """Test retrieving rules summary"""
        driver, session = mock_neo4j_driver
        
        # Mock rules summary result
        mock_result = Mock()
        mock_result.single.return_value = {
            'rule_count': 11,
            'severities': ['critical', 'high', 'medium', 'low']
        }
        
        session.run.return_value = mock_result
        
        # Get related concepts
        concepts = agronomist_agent.get_crop_related_concepts(
            crop='tomato',
            relationship_types=['HAS_RULE']
        )
        
        # Verify
        assert 'rules_summary' in concepts
        assert concepts['rules_summary']['total_rules'] == 11
        assert 'critical' in concepts['rules_summary']['severity_levels']
    
    def test_get_related_crops(self, agronomist_agent, mock_neo4j_driver):
        """Test retrieving related crops"""
        driver, session = mock_neo4j_driver
        
        # Mock related crops result
        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([
            {
                'name': 'Potato',
                'scientific_name': 'Solanum tuberosum',
                'relationship_type': 'same_family'
            }
        ]))
        
        session.run.return_value = mock_result
        
        # Get related concepts
        concepts = agronomist_agent.get_crop_related_concepts(
            crop='tomato',
            relationship_types=['RELATED_TO']
        )
        
        # Verify
        assert 'related_crops' in concepts
        assert len(concepts['related_crops']) == 1
        assert concepts['related_crops'][0]['name'] == 'Potato'
    
    def test_get_default_relationships(self, agronomist_agent, mock_neo4j_driver):
        """Test default relationship types"""
        driver, session = mock_neo4j_driver
        
        # Mock results for default relationships
        session.run.return_value = Mock(__iter__=Mock(return_value=iter([])))
        
        # Get related concepts without specifying types
        concepts = agronomist_agent.get_crop_related_concepts(crop='tomato')
        
        # Verify default relationships were queried
        assert session.run.call_count >= 2  # REQUIRES and HAS_RULE


class TestAssessSpoilageRisk:
    """Test comprehensive spoilage risk assessment"""
    
    def test_assess_risk_complete(self, agronomist_agent, mock_neo4j_driver):
        """Test complete spoilage risk assessment"""
        driver, session = mock_neo4j_driver
        
        # Mock rule query result
        mock_rule_result = Mock()
        mock_rule_result.__iter__ = Mock(return_value=iter([
            {
                'id': 'test_rule',
                'condition': 'High temperature with high humidity',
                'temp_min': 28.0,
                'temp_max': 35.0,
                'humidity_min': 85.0,
                'humidity_max': 100.0,
                'spoilage_time_hours': 48,
                'severity': 'critical',
                'source_reference': 'ICAR Manual',
                'source_name': 'ICAR',
                'source_type': 'ICAR_Manual',
                'credibility': 0.95
            }
        ]))
        
        # Mock related concepts result
        mock_concepts_result = Mock()
        mock_concepts_result.__iter__ = Mock(return_value=iter([]))
        
        session.run.side_effect = [mock_rule_result, mock_concepts_result, mock_concepts_result]
        
        # Assess risk
        assessment = agronomist_agent.assess_spoilage_risk(
            crop='tomato',
            temperature=30.0,
            humidity=90.0
        )
        
        # Verify assessment structure
        assert assessment['crop'] == 'tomato'
        assert assessment['conditions']['temperature'] == 30.0
        assert assessment['conditions']['humidity'] == 90.0
        assert len(assessment['matched_rules']) == 1
        assert assessment['spoilage_timeline']['risk_level'] == 'critical'
        assert len(assessment['risk_factors']) > 0
        assert len(assessment['citations']) > 0
        assert 'timestamp' in assessment
    
    def test_assess_risk_factors_high_temp(self, agronomist_agent):
        """Test risk factor extraction for high temperature"""
        rules = [{
            'id': 'test',
            'condition': 'High temperature condition',
            'temp_range': {'min': 30.0, 'max': 40.0},
            'humidity_range': {'min': 60.0, 'max': 80.0},
            'spoilage_time_hours': 48,
            'severity': 'critical',
            'source': {'name': 'ICAR', 'type': 'ICAR_Manual', 'reference': 'Test', 'credibility': 0.95}
        }]
        
        factors = agronomist_agent._extract_risk_factors(rules)
        
        assert any('High temperature' in f for f in factors)
    
    def test_assess_risk_factors_low_temp(self, agronomist_agent):
        """Test risk factor extraction for low temperature"""
        rules = [{
            'id': 'test',
            'condition': 'Chilling injury',
            'temp_range': {'min': 0.0, 'max': 8.0},
            'humidity_range': {'min': 60.0, 'max': 80.0},
            'spoilage_time_hours': 96,
            'severity': 'high',
            'source': {'name': 'ICAR', 'type': 'ICAR_Manual', 'reference': 'Test', 'credibility': 0.95}
        }]
        
        factors = agronomist_agent._extract_risk_factors(rules)
        
        assert any('Low temperature' in f or 'chilling' in f.lower() for f in factors)
    
    def test_assess_risk_factors_high_humidity(self, agronomist_agent):
        """Test risk factor extraction for high humidity"""
        rules = [{
            'id': 'test',
            'condition': 'Fungal growth risk',
            'temp_range': {'min': 20.0, 'max': 30.0},
            'humidity_range': {'min': 90.0, 'max': 100.0},
            'spoilage_time_hours': 72,
            'severity': 'high',
            'source': {'name': 'ICAR', 'type': 'ICAR_Manual', 'reference': 'Test', 'credibility': 0.95}
        }]
        
        factors = agronomist_agent._extract_risk_factors(rules)
        
        assert any('High humidity' in f for f in factors)
    
    def test_assess_risk_factors_low_humidity(self, agronomist_agent):
        """Test risk factor extraction for low humidity"""
        rules = [{
            'id': 'test',
            'condition': 'Dehydration risk',
            'temp_range': {'min': 20.0, 'max': 30.0},
            'humidity_range': {'min': 30.0, 'max': 60.0},
            'spoilage_time_hours': 120,
            'severity': 'medium',
            'source': {'name': 'ICAR', 'type': 'ICAR_Manual', 'reference': 'Test', 'credibility': 0.95}
        }]
        
        factors = agronomist_agent._extract_risk_factors(rules)
        
        assert any('Low humidity' in f or 'dehydration' in f.lower() for f in factors)


class TestGenerateCitations:
    """Test citation generation"""
    
    def test_generate_citations_single_source(self, agronomist_agent):
        """Test citation generation with single source"""
        rules = [{
            'id': 'rule1',
            'source': {
                'name': 'ICAR Post-Harvest Manual',
                'type': 'ICAR_Manual',
                'reference': 'Section 3.2.1',
                'credibility': 0.95
            }
        }]
        
        citations = agronomist_agent._generate_citations(rules)
        
        assert len(citations) == 1
        assert citations[0]['source'] == 'ICAR Post-Harvest Manual'
        assert citations[0]['type'] == 'ICAR_Manual'
        assert citations[0]['credibility'] == 0.95
    
    def test_generate_citations_multiple_sources(self, agronomist_agent):
        """Test citation generation with multiple sources"""
        rules = [
            {
                'id': 'rule1',
                'source': {
                    'name': 'ICAR Manual',
                    'type': 'ICAR_Manual',
                    'reference': 'Section 3.2.1',
                    'credibility': 0.95
                }
            },
            {
                'id': 'rule2',
                'source': {
                    'name': 'AGROVOC',
                    'type': 'AGROVOC',
                    'reference': 'Concept c_7760',
                    'credibility': 0.90
                }
            }
        ]
        
        citations = agronomist_agent._generate_citations(rules)
        
        assert len(citations) == 2
        assert citations[0]['type'] == 'ICAR_Manual'
        assert citations[1]['type'] == 'AGROVOC'
    
    def test_generate_citations_deduplicate(self, agronomist_agent):
        """Test citation deduplication"""
        rules = [
            {
                'id': 'rule1',
                'source': {
                    'name': 'ICAR Manual',
                    'type': 'ICAR_Manual',
                    'reference': 'Section 3.2.1',
                    'credibility': 0.95
                }
            },
            {
                'id': 'rule2',
                'source': {
                    'name': 'ICAR Manual',
                    'type': 'ICAR_Manual',
                    'reference': 'Section 3.2.1',
                    'credibility': 0.95
                }
            }
        ]
        
        citations = agronomist_agent._generate_citations(rules)
        
        # Should deduplicate same source
        assert len(citations) == 1


class TestDefaultRules:
    """Test fallback default rules"""
    
    def test_default_rules_tomato(self, agronomist_agent):
        """Test default rules for tomato"""
        rules = agronomist_agent._get_default_rules('tomato')
        
        assert len(rules) == 1
        assert rules[0]['id'] == 'default_tomato'
        assert rules[0]['severity'] == 'high'
        assert rules[0]['source']['type'] == 'FALLBACK'
    
    def test_default_rules_onion(self, agronomist_agent):
        """Test default rules for onion"""
        rules = agronomist_agent._get_default_rules('onion')
        
        assert len(rules) == 1
        assert rules[0]['id'] == 'default_onion'
        assert rules[0]['severity'] == 'medium'
        assert rules[0]['source']['type'] == 'FALLBACK'
    
    def test_default_rules_unknown_crop(self, agronomist_agent):
        """Test default rules for unknown crop"""
        rules = agronomist_agent._get_default_rules('unknown')
        
        assert len(rules) == 0

"""Unit tests for biological rules API endpoint"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_agronomist_agent():
    """Mock AgronomistAgent for testing"""
    with patch('app.routers.biological_rules.AgronomistAgent') as mock:
        agent_instance = Mock()
        mock.return_value = agent_instance
        yield agent_instance


@pytest.fixture
def sample_rules():
    """Sample biological rules for testing"""
    return [
        {
            'id': 'rule_tomato_high_temp',
            'condition': 'High temperature and humidity',
            'temp_range': {'min': 30.0, 'max': 45.0},
            'humidity_range': {'min': 80.0, 'max': 100.0},
            'spoilage_time_hours': 48,
            'severity': 'critical',
            'source': {
                'name': 'ICAR Post-Harvest Management Manual',
                'type': 'ICAR_Manual',
                'reference': 'ICAR Post-Harvest Manual 2020, Page 45',
                'credibility': 0.95
            }
        },
        {
            'id': 'rule_tomato_moderate',
            'condition': 'Moderate temperature and humidity',
            'temp_range': {'min': 20.0, 'max': 30.0},
            'humidity_range': {'min': 60.0, 'max': 80.0},
            'spoilage_time_hours': 120,
            'severity': 'medium',
            'source': {
                'name': 'AGROVOC',
                'type': 'AGROVOC',
                'reference': 'AGROVOC Ontology',
                'credibility': 0.85
            }
        }
    ]


def test_get_biological_rules_with_conditions(mock_agronomist_agent, sample_rules):
    """Test retrieving biological rules with temperature and humidity conditions"""
    # Setup mock
    mock_agronomist_agent.query_spoilage_rules.return_value = sample_rules
    
    # Make request
    response = client.get(
        "/api/biological-rules/tomato",
        params={"temperature": 32.0, "humidity": 85.0}
    )
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    
    assert data['crop'] == 'tomato'
    assert len(data['rules']) == 2
    assert data['conditions_applied'] == {'temperature': 32.0, 'humidity': 85.0}
    
    # Check first rule
    rule = data['rules'][0]
    assert rule['id'] == 'rule_tomato_high_temp'
    assert rule['condition'] == 'High temperature and humidity'
    assert rule['spoilage_time'] == '2 days'
    assert rule['source'] == 'ICAR'
    assert rule['confidence'] == 0.95
    assert rule['temp_range'] == {'min': 30.0, 'max': 45.0}
    assert rule['humidity_range'] == {'min': 80.0, 'max': 100.0}
    
    # Verify agent was called correctly
    mock_agronomist_agent.query_spoilage_rules.assert_called_once_with(
        'tomato', 32.0, 85.0
    )


def test_get_biological_rules_without_conditions(mock_agronomist_agent):
    """Test retrieving all biological rules without filtering"""
    # Setup mock for Neo4j session - need to properly mock the context manager
    mock_session = MagicMock()
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__ = MagicMock(return_value=mock_session)
    mock_context_manager.__exit__ = MagicMock(return_value=False)
    mock_agronomist_agent.driver.session.return_value = mock_context_manager
    
    mock_record = Mock()
    mock_record.__getitem__ = lambda self, key: {
        'id': 'rule_tomato_1',
        'condition': 'Test condition',
        'temp_min': 20.0,
        'temp_max': 30.0,
        'humidity_min': 60.0,
        'humidity_max': 80.0,
        'spoilage_time_hours': 72,
        'severity': 'medium',
        'source_reference': 'Test reference',
        'source_name': 'ICAR',
        'source_type': 'ICAR_Manual',
        'credibility': 0.9
    }[key]
    
    mock_session.run.return_value = [mock_record]
    
    # Make request
    response = client.get("/api/biological-rules/onion")
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    
    assert data['crop'] == 'onion'
    assert len(data['rules']) >= 1
    assert data['conditions_applied'] is None


def test_get_biological_rules_invalid_crop():
    """Test with invalid crop type"""
    response = client.get("/api/biological-rules/potato")
    
    assert response.status_code == 422  # Validation error from path pattern


def test_get_biological_rules_temperature_only():
    """Test with only temperature (should fail - both required)"""
    response = client.get(
        "/api/biological-rules/tomato",
        params={"temperature": 32.0}
    )
    
    assert response.status_code == 400
    assert "Both temperature and humidity must be provided" in response.json()['detail']


def test_get_biological_rules_humidity_only():
    """Test with only humidity (should fail - both required)"""
    response = client.get(
        "/api/biological-rules/tomato",
        params={"humidity": 85.0}
    )
    
    assert response.status_code == 400
    assert "Both temperature and humidity must be provided" in response.json()['detail']


def test_get_biological_rules_invalid_temperature():
    """Test with invalid temperature value"""
    response = client.get(
        "/api/biological-rules/tomato",
        params={"temperature": 100.0, "humidity": 85.0}
    )
    
    assert response.status_code == 422  # Validation error


def test_get_biological_rules_invalid_humidity():
    """Test with invalid humidity value"""
    response = client.get(
        "/api/biological-rules/tomato",
        params={"temperature": 32.0, "humidity": 150.0}
    )
    
    assert response.status_code == 422  # Validation error


def test_get_biological_rules_no_rules_found(mock_agronomist_agent):
    """Test when no rules are found for the crop"""
    # Setup mock to return empty list
    mock_agronomist_agent.query_spoilage_rules.return_value = []
    
    # Make request
    response = client.get(
        "/api/biological-rules/tomato",
        params={"temperature": 32.0, "humidity": 85.0}
    )
    
    # Assertions
    assert response.status_code == 404
    assert "No biological rules found" in response.json()['detail']


def test_get_biological_rules_spoilage_time_formatting(mock_agronomist_agent):
    """Test spoilage time formatting for different durations"""
    test_cases = [
        (12, '12 hours'),
        (24, '1 day'),
        (48, '2 days'),
        (168, '1 week'),
        (336, '2 weeks')
    ]
    
    for hours, expected_display in test_cases:
        # Setup mock
        mock_agronomist_agent.query_spoilage_rules.return_value = [{
            'id': 'test_rule',
            'condition': 'Test condition',
            'temp_range': {'min': 20.0, 'max': 30.0},
            'humidity_range': {'min': 60.0, 'max': 80.0},
            'spoilage_time_hours': hours,
            'severity': 'medium',
            'source': {
                'name': 'Test Source',
                'type': 'ICAR_Manual',
                'reference': 'Test reference',
                'credibility': 0.9
            }
        }]
        
        # Make request
        response = client.get(
            "/api/biological-rules/tomato",
            params={"temperature": 25.0, "humidity": 70.0}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data['rules'][0]['spoilage_time'] == expected_display


def test_get_biological_rules_source_type_mapping(mock_agronomist_agent):
    """Test source type mapping (ICAR_Manual -> ICAR, AGROVOC -> AGROVOC, etc.)"""
    test_cases = [
        ('ICAR_Manual', 'ICAR'),
        ('AGROVOC', 'AGROVOC'),
        ('FALLBACK', 'FALLBACK'),
        ('Unknown', 'FALLBACK')
    ]
    
    for source_type, expected_source in test_cases:
        # Setup mock
        mock_agronomist_agent.query_spoilage_rules.return_value = [{
            'id': 'test_rule',
            'condition': 'Test condition',
            'temp_range': {'min': 20.0, 'max': 30.0},
            'humidity_range': {'min': 60.0, 'max': 80.0},
            'spoilage_time_hours': 72,
            'severity': 'medium',
            'source': {
                'name': 'Test Source',
                'type': source_type,
                'reference': 'Test reference',
                'credibility': 0.9
            }
        }]
        
        # Make request
        response = client.get(
            "/api/biological-rules/tomato",
            params={"temperature": 25.0, "humidity": 70.0}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data['rules'][0]['source'] == expected_source


def test_get_biological_rules_error_handling(mock_agronomist_agent):
    """Test error handling when agent raises exception"""
    # Setup mock to raise exception
    mock_agronomist_agent.query_spoilage_rules.side_effect = Exception("Database error")
    
    # Make request
    response = client.get(
        "/api/biological-rules/tomato",
        params={"temperature": 32.0, "humidity": 85.0}
    )
    
    # Assertions
    assert response.status_code == 500
    assert "Failed to retrieve biological rules" in response.json()['detail']


def test_get_biological_rules_multiple_rules_ordering(mock_agronomist_agent, sample_rules):
    """Test that rules are returned in correct order (by severity)"""
    # Setup mock
    mock_agronomist_agent.query_spoilage_rules.return_value = sample_rules
    
    # Make request
    response = client.get(
        "/api/biological-rules/tomato",
        params={"temperature": 32.0, "humidity": 85.0}
    )
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    
    # First rule should be critical severity
    assert data['rules'][0]['id'] == 'rule_tomato_high_temp'
    # Second rule should be medium severity
    assert data['rules'][1]['id'] == 'rule_tomato_moderate'

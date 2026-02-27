"""Tests for Supervisor Agent recommendation synthesis logic"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.supervisor_agent import SupervisorAgent


@pytest.fixture
def supervisor():
    """Create supervisor agent instance with mocked dependencies"""
    with patch('app.agents.supervisor_agent.GeospatialAgent'), \
         patch('app.agents.supervisor_agent.AgronomistAgent'), \
         patch('app.agents.supervisor_agent.EconomistAgent'), \
         patch('app.agents.supervisor_agent.WeatherService'):
        return SupervisorAgent()


@pytest.fixture
def mock_geospatial_data():
    """Mock geospatial data"""
    return {
        'ndvi': 0.75,
        'soil_moisture': 65.0,
        'rainfall_mm': 12.5,
        'cached': True,
        'cache_age_days': 1
    }


@pytest.fixture
def mock_weather_data_with_storm():
    """Mock weather data with storm risk"""
    return {
        'forecast': [
            {
                'date': '2024-01-15',
                'temp_max': 32.0,
                'temp_min': 24.0,
                'humidity': 85.0,
                'precip_probability': 0.8,
                'precip_amount': 25.0,
                'condition': 'Heavy rain'
            }
        ],
        'risk_assessment': {
            'has_storm_risk': True,
            'risk_window': 'next 24 hours',
            'impact': 'Heavy rainfall expected'
        },
        'current_conditions': {
            'temperature': 28.0,
            'humidity': 85.0
        }
    }


@pytest.fixture
def mock_weather_data_no_storm():
    """Mock weather data without storm risk"""
    return {
        'forecast': [
            {
                'date': '2024-01-15',
                'temp_max': 30.0,
                'temp_min': 22.0,
                'humidity': 70.0,
                'precip_probability': 0.2,
                'precip_amount': 2.0,
                'condition': 'Partly cloudy'
            }
        ],
        'risk_assessment': {
            'has_storm_risk': False,
            'risk_window': None,
            'impact': None
        },
        'current_conditions': {
            'temperature': 26.0,
            'humidity': 70.0
        }
    }


@pytest.fixture
def mock_agronomist_data_critical():
    """Mock agronomist data with critical spoilage risk"""
    return {
        'crop': 'tomato',
        'conditions': {
            'temperature': 35.0,
            'humidity': 90.0
        },
        'matched_rules': [
            {
                'id': 'rule_tomato_high_temp',
                'condition': 'High temperature and humidity',
                'severity': 'critical',
                'spoilage_time_hours': 48,
                'source': {
                    'name': 'ICAR Post-Harvest Manual',
                    'type': 'ICAR',
                    'reference': 'Page 45',
                    'credibility': 0.95
                }
            }
        ],
        'spoilage_timeline': {
            'time_to_spoilage_hours': 48,
            'time_to_spoilage_display': '2 days',
            'risk_level': 'critical'
        },
        'risk_factors': ['High temperature accelerating spoilage'],
        'citations': []
    }


@pytest.fixture
def mock_agronomist_data_low():
    """Mock agronomist data with low spoilage risk"""
    return {
        'crop': 'tomato',
        'conditions': {
            'temperature': 25.0,
            'humidity': 65.0
        },
        'matched_rules': [
            {
                'id': 'rule_tomato_normal',
                'condition': 'Normal conditions',
                'severity': 'low',
                'spoilage_time_hours': 168,
                'source': {
                    'name': 'ICAR Post-Harvest Manual',
                    'type': 'ICAR',
                    'reference': 'Page 45',
                    'credibility': 0.95
                }
            }
        ],
        'spoilage_timeline': {
            'time_to_spoilage_hours': 168,
            'time_to_spoilage_display': '1 week',
            'risk_level': 'low'
        },
        'risk_factors': [],
        'citations': []
    }


@pytest.fixture
def mock_economist_data_good_opportunity():
    """Mock economist data with good market opportunity"""
    return {
        'crop': 'tomato',
        'best_market': {
            'name': 'Nagpur Mandi',
            'location': 'Nagpur',
            'price_per_kg': 35.0,
            'distance_km': 25.0,
            'last_updated': '2024-01-15T10:00:00Z'
        },
        'local_market': {
            'name': 'Local Mandi',
            'location': 'Local',
            'price_per_kg': 25.0,
            'distance_km': 5.0
        },
        'price_difference': 10.0,
        'market_opportunity': 'excellent',
        'fallback_used': False
    }


@pytest.fixture
def mock_economist_data_low_opportunity():
    """Mock economist data with low market opportunity"""
    return {
        'crop': 'tomato',
        'best_market': {
            'name': 'Local Mandi',
            'location': 'Local',
            'price_per_kg': 25.0,
            'distance_km': 5.0,
            'last_updated': '2024-01-15T10:00:00Z'
        },
        'local_market': {
            'name': 'Local Mandi',
            'location': 'Local',
            'price_per_kg': 25.0,
            'distance_km': 5.0
        },
        'price_difference': 0.0,
        'market_opportunity': 'low',
        'fallback_used': False
    }


class TestRecommendationSynthesis:
    """Test recommendation synthesis logic"""
    
    def test_storm_triggered_urgent_harvest(
        self,
        supervisor,
        mock_geospatial_data,
        mock_weather_data_with_storm,
        mock_agronomist_data_low,
        mock_economist_data_low_opportunity
    ):
        """
        Test that storm within 48h + crop ready triggers critical/high urgency harvest.
        
        Validates: Requirements 3.2 (storm-triggered urgent harvest)
        """
        recommendation = supervisor._synthesize_recommendation(
            geospatial_data=mock_geospatial_data,
            weather_data=mock_weather_data_with_storm,
            agronomist_data=mock_agronomist_data_low,
            economist_data=mock_economist_data_low_opportunity,
            crop='tomato',
            language='en'
        )
        
        assert recommendation['action'] == 'harvest_now'
        assert recommendation['urgency'] in ['critical', 'high']
        assert recommendation['primary_factor'] == 'storm_risk'
        assert 'rain' in recommendation['primary_message'].lower() or 'storm' in recommendation['primary_message'].lower()
    
    def test_critical_spoilage_risk_harvest(
        self,
        supervisor,
        mock_geospatial_data,
        mock_weather_data_no_storm,
        mock_agronomist_data_critical,
        mock_economist_data_low_opportunity
    ):
        """
        Test that critical spoilage risk triggers high urgency harvest.
        
        Validates: Requirements 10.2, 10.5 (spoilage-based decision)
        """
        recommendation = supervisor._synthesize_recommendation(
            geospatial_data=mock_geospatial_data,
            weather_data=mock_weather_data_no_storm,
            agronomist_data=mock_agronomist_data_critical,
            economist_data=mock_economist_data_low_opportunity,
            crop='tomato',
            language='en'
        )
        
        assert recommendation['action'] == 'harvest_now'
        assert recommendation['urgency'] == 'high'
        assert recommendation['primary_factor'] == 'spoilage_risk'
    
    def test_market_opportunity_sell_now(
        self,
        supervisor,
        mock_geospatial_data,
        mock_weather_data_no_storm,
        mock_agronomist_data_low,
        mock_economist_data_good_opportunity
    ):
        """
        Test that good market opportunity + crop ready triggers sell_now.
        
        Validates: Requirements 10.2, 10.5 (market-based decision)
        """
        recommendation = supervisor._synthesize_recommendation(
            geospatial_data=mock_geospatial_data,
            weather_data=mock_weather_data_no_storm,
            agronomist_data=mock_agronomist_data_low,
            economist_data=mock_economist_data_good_opportunity,
            crop='tomato',
            language='en'
        )
        
        assert recommendation['action'] == 'sell_now'
        assert recommendation['urgency'] in ['medium', 'low']
        assert recommendation['primary_factor'] == 'market_opportunity'
    
    def test_wait_recommendation_default(
        self,
        supervisor,
        mock_geospatial_data,
        mock_weather_data_no_storm,
        mock_agronomist_data_low,
        mock_economist_data_low_opportunity
    ):
        """
        Test that no threats/opportunities triggers wait recommendation.
        
        Validates: Requirements 10.2 (default decision logic)
        """
        # Make crop not ready
        mock_geospatial_data['ndvi'] = 0.5
        
        recommendation = supervisor._synthesize_recommendation(
            geospatial_data=mock_geospatial_data,
            weather_data=mock_weather_data_no_storm,
            agronomist_data=mock_agronomist_data_low,
            economist_data=mock_economist_data_low_opportunity,
            crop='tomato',
            language='en'
        )
        
        assert recommendation['action'] == 'wait'
        assert recommendation['urgency'] == 'low'
    
    def test_urgency_level_calculation(self, supervisor):
        """
        Test urgency level calculation for different scenarios.
        
        Validates: Requirements 10.5 (urgency levels)
        """
        # Critical urgency: storm + crop ready
        action, urgency, factor = supervisor._determine_action_and_urgency(
            crop_ready=True,
            storm_risk=True,
            spoilage_risk='low',
            market_opportunity='low',
            price_difference=0.0
        )
        assert urgency == 'critical'
        
        # High urgency: storm + crop not ready
        action, urgency, factor = supervisor._determine_action_and_urgency(
            crop_ready=False,
            storm_risk=True,
            spoilage_risk='low',
            market_opportunity='low',
            price_difference=0.0
        )
        assert urgency == 'high'
        
        # High urgency: critical spoilage
        action, urgency, factor = supervisor._determine_action_and_urgency(
            crop_ready=True,
            storm_risk=False,
            spoilage_risk='critical',
            market_opportunity='low',
            price_difference=0.0
        )
        assert urgency == 'high'
        
        # Medium urgency: high spoilage
        action, urgency, factor = supervisor._determine_action_and_urgency(
            crop_ready=True,
            storm_risk=False,
            spoilage_risk='high',
            market_opportunity='low',
            price_difference=0.0
        )
        assert urgency == 'medium'
    
    def test_confidence_calculation_excellent_data(
        self,
        supervisor,
        mock_geospatial_data,
        mock_weather_data_no_storm,
        mock_agronomist_data_low,
        mock_economist_data_low_opportunity
    ):
        """
        Test confidence calculation with excellent data quality.
        
        Validates: Requirements 10.6 (confidence scoring)
        """
        confidence, quality = supervisor._calculate_confidence_and_quality(
            geospatial_data=mock_geospatial_data,
            weather_data=mock_weather_data_no_storm,
            agronomist_data=mock_agronomist_data_low,
            economist_data=mock_economist_data_low_opportunity
        )
        
        assert confidence >= 90.0
        assert quality == 'excellent'
    
    def test_confidence_calculation_degraded_data(self, supervisor):
        """
        Test confidence calculation with degraded data quality.
        
        Validates: Requirements 10.6 (confidence with data quality correlation)
        """
        # Missing satellite data
        geospatial_data = {'error': 'Satellite unavailable', 'cached': False}
        weather_data = {'fallback_used': True, 'forecast': []}
        agronomist_data = {'matched_rules': []}
        economist_data = {'error': 'Market API down', 'best_market': None}
        
        confidence, quality = supervisor._calculate_confidence_and_quality(
            geospatial_data=geospatial_data,
            weather_data=weather_data,
            agronomist_data=agronomist_data,
            economist_data=economist_data
        )
        
        assert confidence < 50.0
        assert quality == 'poor'
    
    def test_confidence_calculation_old_cache(
        self,
        supervisor,
        mock_weather_data_no_storm,
        mock_agronomist_data_low,
        mock_economist_data_low_opportunity
    ):
        """
        Test that old cached data reduces confidence.
        
        Validates: Requirements 10.6 (data age affects confidence)
        """
        # Old cached data (5 days)
        geospatial_data = {
            'ndvi': 0.75,
            'cached': True,
            'cache_age_days': 5
        }
        
        confidence, quality = supervisor._calculate_confidence_and_quality(
            geospatial_data=geospatial_data,
            weather_data=mock_weather_data_no_storm,
            agronomist_data=mock_agronomist_data_low,
            economist_data=mock_economist_data_low_opportunity
        )
        
        assert confidence < 100.0
        assert quality in ['excellent', 'good', 'fair']  # Old cache reduces confidence by 10, so still good quality
    
    def test_reasoning_chain_structure(
        self,
        supervisor,
        mock_geospatial_data,
        mock_weather_data_with_storm,
        mock_agronomist_data_low,
        mock_economist_data_good_opportunity
    ):
        """
        Test reasoning chain includes all required elements.
        
        Validates: Requirements 10.2 (reasoning chain structure)
        """
        recommendation = supervisor._synthesize_recommendation(
            geospatial_data=mock_geospatial_data,
            weather_data=mock_weather_data_with_storm,
            agronomist_data=mock_agronomist_data_low,
            economist_data=mock_economist_data_good_opportunity,
            crop='tomato',
            language='en'
        )
        
        reasoning_chain = supervisor._generate_reasoning_chain(
            recommendation=recommendation,
            geospatial_data=mock_geospatial_data,
            weather_data=mock_weather_data_with_storm,
            agronomist_data=mock_agronomist_data_low,
            economist_data=mock_economist_data_good_opportunity,
            language='en'
        )
        
        # Should have at least 5 steps
        assert len(reasoning_chain) >= 5
        
        # Check for required elements
        chain_text = ' '.join(reasoning_chain).lower()
        assert 'weather' in chain_text
        assert 'crop' in chain_text or 'ndvi' in chain_text
        assert 'spoilage' in chain_text or 'risk' in chain_text
        assert 'market' in chain_text or 'price' in chain_text
        assert 'recommendation' in chain_text
    
    def test_primary_factor_highlighting(
        self,
        supervisor,
        mock_geospatial_data,
        mock_weather_data_with_storm,
        mock_agronomist_data_low,
        mock_economist_data_low_opportunity
    ):
        """
        Test that primary factor is identified and highlighted.
        
        Validates: Requirements 10.5 (primary factor highlighting)
        """
        recommendation = supervisor._synthesize_recommendation(
            geospatial_data=mock_geospatial_data,
            weather_data=mock_weather_data_with_storm,
            agronomist_data=mock_agronomist_data_low,
            economist_data=mock_economist_data_low_opportunity,
            crop='tomato',
            language='en'
        )
        
        assert 'primary_factor' in recommendation
        assert recommendation['primary_factor'] in [
            'storm_risk', 'spoilage_risk', 'market_opportunity', 'optimal_timing'
        ]
    
    def test_graceful_degradation_missing_data(self, supervisor):
        """
        Test graceful degradation when data is missing.
        
        Validates: Requirements 10.6 (graceful degradation)
        """
        # All data sources have errors
        geospatial_data = {'error': 'Service unavailable'}
        weather_data = {'error': 'API timeout', 'forecast': [], 'risk_assessment': {
            'has_storm_risk': False, 'risk_window': None, 'impact': None
        }, 'current_conditions': {'temperature': 25.0, 'humidity': 70.0}}
        agronomist_data = {'error': 'Neo4j down', 'matched_rules': [], 'spoilage_timeline': {
            'risk_level': 'unknown'
        }}
        economist_data = {'error': 'Market API down', 'best_market': None}
        
        # Should still generate a recommendation
        recommendation = supervisor._synthesize_recommendation(
            geospatial_data=geospatial_data,
            weather_data=weather_data,
            agronomist_data=agronomist_data,
            economist_data=economist_data,
            crop='tomato',
            language='en'
        )
        
        assert 'action' in recommendation
        assert 'urgency' in recommendation
        assert 'primary_message' in recommendation
        
        # Confidence should be low
        confidence, quality = supervisor._calculate_confidence_and_quality(
            geospatial_data=geospatial_data,
            weather_data=weather_data,
            agronomist_data=agronomist_data,
            economist_data=economist_data
        )
        
        assert confidence < 50.0
        assert quality == 'poor'
    
    def test_hindi_language_support(
        self,
        supervisor,
        mock_geospatial_data,
        mock_weather_data_with_storm,
        mock_agronomist_data_low,
        mock_economist_data_low_opportunity
    ):
        """
        Test Hindi language support for messages and reasoning.
        
        Validates: Requirements 10.1 (language-specific explanations)
        """
        recommendation = supervisor._synthesize_recommendation(
            geospatial_data=mock_geospatial_data,
            weather_data=mock_weather_data_with_storm,
            agronomist_data=mock_agronomist_data_low,
            economist_data=mock_economist_data_low_opportunity,
            crop='tomato',
            language='hi'
        )
        
        # Check for Hindi characters in message
        message = recommendation['primary_message']
        # Hindi Unicode range: \u0900-\u097F
        has_hindi = any('\u0900' <= char <= '\u097F' for char in message)
        assert has_hindi, "Message should contain Hindi characters"
        
        # Generate reasoning chain in Hindi
        reasoning_chain = supervisor._generate_reasoning_chain(
            recommendation=recommendation,
            geospatial_data=mock_geospatial_data,
            weather_data=mock_weather_data_with_storm,
            agronomist_data=mock_agronomist_data_low,
            economist_data=mock_economist_data_low_opportunity,
            language='hi'
        )
        
        # Check for Hindi in reasoning
        chain_text = ' '.join(reasoning_chain)
        has_hindi_reasoning = any('\u0900' <= char <= '\u097F' for char in chain_text)
        assert has_hindi_reasoning, "Reasoning should contain Hindi characters"


class TestCropReadinessAssessment:
    """Test crop readiness assessment logic"""
    
    def test_crop_ready_high_ndvi(self, supervisor):
        """Test crop is ready when NDVI > 0.6"""
        geospatial_data = {'ndvi': 0.75, 'soil_moisture': 65.0}
        
        crop_ready = supervisor._assess_crop_readiness(geospatial_data)
        
        assert crop_ready is True
    
    def test_crop_not_ready_low_ndvi(self, supervisor):
        """Test crop is not ready when NDVI <= 0.6"""
        geospatial_data = {'ndvi': 0.5, 'soil_moisture': 65.0}
        
        crop_ready = supervisor._assess_crop_readiness(geospatial_data)
        
        assert crop_ready is False
    
    def test_crop_ready_missing_ndvi(self, supervisor):
        """Test crop assumed ready when NDVI is missing (conservative)"""
        geospatial_data = {'ndvi': None, 'soil_moisture': 65.0}
        
        crop_ready = supervisor._assess_crop_readiness(geospatial_data)
        
        assert crop_ready is True


@pytest.mark.asyncio
class TestEndToEndRecommendation:
    """Test end-to-end recommendation generation"""
    
    async def test_generate_recommendation_success(self, supervisor):
        """Test successful recommendation generation with mocked agents"""
        # Mock all agent methods
        supervisor.geospatial_agent.get_geospatial_data = AsyncMock(return_value={
            'ndvi': 0.75,
            'soil_moisture': 65.0,
            'cached': True,
            'cache_age_days': 1
        })
        
        supervisor.weather_service.get_weather_forecast = AsyncMock(return_value={
            'forecast': [
                {
                    'date': '2024-01-15',
                    'temp_max': 32.0,
                    'temp_min': 24.0,
                    'humidity': 85.0,
                    'precip_probability': 0.8,
                    'precip_amount': 25.0,
                    'condition': 'Heavy rain'
                }
            ],
            'risk_assessment': {
                'has_storm_risk': True,
                'risk_window': 'next 24 hours',
                'impact': 'Heavy rainfall expected'
            }
        })
        
        supervisor.agronomist_agent.assess_spoilage_risk = MagicMock(return_value={
            'crop': 'tomato',
            'conditions': {'temperature': 28.0, 'humidity': 85.0},
            'matched_rules': [{'severity': 'medium'}],
            'spoilage_timeline': {
                'time_to_spoilage_hours': 72,
                'time_to_spoilage_display': '3 days',
                'risk_level': 'medium'
            }
        })
        
        supervisor.economist_agent.get_market_recommendation = MagicMock(return_value={
            'crop': 'tomato',
            'best_market': {
                'name': 'Nagpur Mandi',
                'price_per_kg': 30.0,
                'distance_km': 25.0
            },
            'price_difference': 5.0,
            'market_opportunity': 'good'
        })
        
        # Generate recommendation
        recommendation = await supervisor.generate_recommendation(
            farmer_id='test_farmer',
            latitude=21.1458,
            longitude=79.0882,
            crop='tomato',
            field_size=2.5,
            language='en'
        )
        
        # Verify structure
        assert 'action' in recommendation
        assert 'urgency' in recommendation
        assert 'primary_message' in recommendation
        assert 'reasoning' in recommendation
        assert 'confidence' in recommendation
        assert 'data_quality' in recommendation
        assert 'reasoning_chain' in recommendation
        assert 'timestamp' in recommendation
        
        # Verify values
        assert recommendation['action'] in ['harvest_now', 'wait', 'sell_now']
        assert recommendation['urgency'] in ['critical', 'high', 'medium', 'low']
        assert 0 <= recommendation['confidence'] <= 100
        assert recommendation['data_quality'] in ['excellent', 'good', 'fair', 'poor']
        assert len(recommendation['reasoning_chain']) > 0

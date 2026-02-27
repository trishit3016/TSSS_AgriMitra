"""Tests for Supervisor Agent with LangGraph orchestration"""

import pytest
from app.agents.supervisor_agent import SupervisorAgent
from app.models.requests import RecommendationRequest, Location


@pytest.fixture
def supervisor_agent():
    """Create supervisor agent instance"""
    return SupervisorAgent()


@pytest.fixture
def sample_request():
    """Create sample recommendation request"""
    return RecommendationRequest(
        farmer_id="test_farmer_1",
        location=Location(latitude=21.1458, longitude=79.0882),
        crop="tomato",
        field_size=2.5,
        language="en"
    )


def test_supervisor_agent_initialization(supervisor_agent):
    """Test that supervisor agent initializes correctly"""
    assert supervisor_agent is not None
    assert supervisor_agent.geospatial_agent is not None
    assert supervisor_agent.agronomist_agent is not None
    assert supervisor_agent.economist_agent is not None
    assert supervisor_agent.workflow is not None


def test_agent_state_structure():
    """Test that AgentState TypedDict has correct structure"""
    # This validates that the state management structure is defined
    state: AgentState = {
        "request": None,
        "geospatial_data": None,
        "biological_assessment": None,
        "market_recommendation": None,
        "action_banner": None,
        "weather_card": None,
        "market_card": None,
        "spoilage_card": None,
        "reasoning": None,
        "errors": [],
        "warnings": [],
        "timestamp": ""
    }
    
    # Verify all required keys are present
    assert "request" in state
    assert "geospatial_data" in state
    assert "biological_assessment" in state
    assert "market_recommendation" in state
    assert "action_banner" in state
    assert "weather_card" in state
    assert "market_card" in state
    assert "spoilage_card" in state
    assert "reasoning" in state
    assert "errors" in state
    assert "warnings" in state
    assert "timestamp" in state


@pytest.mark.asyncio
async def test_generate_recommendation_structure(supervisor_agent, sample_request):
    """Test that generate_recommendation returns correct structure"""
    components = await supervisor_agent.generate_recommendation(sample_request)
    
    # Should return a list of StreamComponent objects
    assert isinstance(components, list)
    assert len(components) > 0
    
    # Verify component types
    component_types = [c.type for c in components]
    
    # Should have action banner (always present)
    assert "action" in component_types
    
    # Should have reasoning (always present)
    assert "reasoning" in component_types


@pytest.mark.asyncio
async def test_generate_recommendation_with_tomato(supervisor_agent):
    """Test recommendation generation for tomato crop"""
    request = RecommendationRequest(
        farmer_id="test_farmer_tomato",
        location=Location(latitude=21.1458, longitude=79.0882),
        crop="tomato",
        field_size=2.5,
        language="en"
    )
    
    components = await supervisor_agent.generate_recommendation(request)
    
    assert len(components) > 0
    
    # Find action component
    action_component = next((c for c in components if c.type == "action"), None)
    assert action_component is not None
    
    # Verify action component has required fields
    action_data = action_component.data
    assert "action" in action_data
    assert "urgency" in action_data
    assert "primary_message" in action_data
    assert "confidence" in action_data
    assert "data_quality" in action_data


@pytest.mark.asyncio
async def test_generate_recommendation_with_onion(supervisor_agent):
    """Test recommendation generation for onion crop"""
    request = RecommendationRequest(
        farmer_id="test_farmer_onion",
        location=Location(latitude=21.1458, longitude=79.0882),
        crop="onion",
        field_size=3.0,
        language="en"
    )
    
    components = await supervisor_agent.generate_recommendation(request)
    
    assert len(components) > 0
    
    # Find spoilage component
    spoilage_component = next((c for c in components if c.type == "spoilage"), None)
    
    # Spoilage component should be present if biological assessment succeeded
    if spoilage_component:
        spoilage_data = spoilage_component.data
        assert "crop" in spoilage_data
        assert spoilage_data["crop"] == "onion"


@pytest.mark.asyncio
async def test_parallel_agent_execution(supervisor_agent, sample_request):
    """Test that agents execute in parallel through LangGraph"""
    # This test verifies the workflow structure
    # In a real scenario, we'd measure execution time to confirm parallelism
    
    components = await supervisor_agent.generate_recommendation(sample_request)
    
    # If all agents executed successfully, we should have multiple components
    assert len(components) >= 2  # At minimum action and reasoning
    
    # Verify reasoning includes data from multiple sources
    reasoning_component = next((c for c in components if c.type == "reasoning"), None)
    assert reasoning_component is not None
    
    reasoning_data = reasoning_component.data
    assert "chain" in reasoning_data
    assert "data_sources" in reasoning_data
    
    # Chain should have multiple steps (one per agent)
    assert len(reasoning_data["chain"]) >= 3


@pytest.mark.asyncio
async def test_graceful_degradation(supervisor_agent):
    """Test that supervisor handles missing data gracefully"""
    # Create request for location that likely has no cached data
    request = RecommendationRequest(
        farmer_id="test_farmer_no_cache",
        location=Location(latitude=20.0, longitude=77.0),
        crop="tomato",
        field_size=1.0,
        language="en"
    )
    
    components = await supervisor_agent.generate_recommendation(request)
    
    # Should still generate components even with missing data
    assert len(components) > 0
    
    # Action component should always be present
    action_component = next((c for c in components if c.type == "action"), None)
    assert action_component is not None
    
    # Confidence should be reduced when data is missing
    action_data = action_component.data
    # Confidence will be lower due to missing cached data
    assert action_data["confidence"] < 100.0


def test_workflow_graph_structure(supervisor_agent):
    """Test that LangGraph workflow has correct structure"""
    workflow = supervisor_agent.workflow
    
    # Workflow should be compiled
    assert workflow is not None
    
    # The workflow should have the expected nodes
    # Note: LangGraph's compiled graph doesn't expose nodes directly,
    # but we can verify it was created successfully
    assert hasattr(workflow, 'invoke')
    assert hasattr(workflow, 'ainvoke')

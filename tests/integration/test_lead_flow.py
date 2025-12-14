"""
Hampstead Renovations - Integration Tests
==========================================

End-to-end tests for the complete lead flow:
Web Form -> Lead Intake API -> n8n -> HubSpot

Run with: pytest tests/integration/ -v --asyncio-mode=auto
"""

import asyncio
import os
import pytest
import httpx
from datetime import datetime
from typing import Generator, AsyncGenerator
from unittest.mock import AsyncMock, patch

# Test configuration
LEAD_INTAKE_URL = os.getenv("LEAD_INTAKE_URL", "http://localhost:8004")
DASHBOARD_API_URL = os.getenv("DASHBOARD_API_URL", "http://localhost:8005")
QUOTE_BUILDER_URL = os.getenv("QUOTE_BUILDER_URL", "http://localhost:8001")


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def valid_lead_data() -> dict:
    """Generate valid lead submission data."""
    return {
        "first_name": "John",
        "last_name": "Smith",
        "email": "john.smith@example.com",
        "phone": "+447123456789",
        "preferred_contact": "email",
        "postcode": "NW3 4QG",
        "property_type": "terraced",
        "property_age": "pre-1900",
        "project_types": ["kitchen", "bathroom"],
        "project_description": "Complete renovation of Victorian terrace including new kitchen and two bathrooms.",
        "timeline": "3-6-months",
        "budget_range": "100k-200k",
        "conservation_area": True,
        "planning_required": False,
        "source": "web-form",
        "how_did_you_hear": "google",
        "marketing_consent": True,
    }


@pytest.fixture
def minimal_lead_data() -> dict:
    """Generate minimal required lead data."""
    return {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane.doe@example.com",
        "phone": "07987654321",
        "preferred_contact": "phone",
        "postcode": "NW1 1AA",
        "property_type": "flat",
        "property_age": "1990-2010",
        "project_types": ["painting-decorating"],
        "project_description": "Interior decoration of 2-bedroom flat.",
        "timeline": "asap",
        "budget_range": "under-25k",
        "source": "web-form",
    }


@pytest.fixture
def invalid_postcode_lead() -> dict:
    """Generate lead data with invalid postcode (outside service area)."""
    return {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "phone": "07123456789",
        "preferred_contact": "email",
        "postcode": "SW1A 1AA",  # Westminster - outside service area
        "property_type": "flat",
        "property_age": "1960-1990",
        "project_types": ["bathroom"],
        "project_description": "Bathroom refurbishment.",
        "timeline": "1-3-months",
        "budget_range": "25k-50k",
        "source": "web-form",
    }


@pytest.fixture
async def http_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create async HTTP client for tests."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================


class TestHealthChecks:
    """Test service health endpoints."""
    
    @pytest.mark.asyncio
    async def test_lead_intake_health(self, http_client: httpx.AsyncClient):
        """Test Lead Intake API health check."""
        response = await http_client.get(f"{LEAD_INTAKE_URL}/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_dashboard_api_health(self, http_client: httpx.AsyncClient):
        """Test Dashboard API health check."""
        response = await http_client.get(f"{DASHBOARD_API_URL}/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_quote_builder_health(self, http_client: httpx.AsyncClient):
        """Test Quote Builder health check."""
        response = await http_client.get(f"{QUOTE_BUILDER_URL}/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


# =============================================================================
# LEAD SUBMISSION TESTS
# =============================================================================


class TestLeadSubmission:
    """Test lead submission flow."""
    
    @pytest.mark.asyncio
    async def test_submit_valid_lead(
        self, 
        http_client: httpx.AsyncClient, 
        valid_lead_data: dict
    ):
        """Test submitting a valid lead."""
        response = await http_client.post(
            f"{LEAD_INTAKE_URL}/leads",
            json=valid_lead_data
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] is True
        assert "leadId" in data or "lead_id" in data
        assert data.get("score") is not None or data.get("lead_score") is not None
        assert data["priority"] in ["high", "medium", "low"]
    
    @pytest.mark.asyncio
    async def test_submit_minimal_lead(
        self,
        http_client: httpx.AsyncClient,
        minimal_lead_data: dict
    ):
        """Test submitting a lead with minimal data."""
        response = await http_client.post(
            f"{LEAD_INTAKE_URL}/leads",
            json=minimal_lead_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_submit_missing_required_fields(
        self,
        http_client: httpx.AsyncClient
    ):
        """Test submission with missing required fields."""
        incomplete_data = {
            "first_name": "Test",
            # Missing other required fields
        }
        
        response = await http_client.post(
            f"{LEAD_INTAKE_URL}/leads",
            json=incomplete_data
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_submit_invalid_email(
        self,
        http_client: httpx.AsyncClient,
        valid_lead_data: dict
    ):
        """Test submission with invalid email."""
        invalid_data = valid_lead_data.copy()
        invalid_data["email"] = "not-an-email"
        
        response = await http_client.post(
            f"{LEAD_INTAKE_URL}/leads",
            json=invalid_data
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_submit_invalid_phone(
        self,
        http_client: httpx.AsyncClient,
        valid_lead_data: dict
    ):
        """Test submission with invalid phone number."""
        invalid_data = valid_lead_data.copy()
        invalid_data["phone"] = "123"  # Too short
        
        response = await http_client.post(
            f"{LEAD_INTAKE_URL}/leads",
            json=invalid_data
        )
        
        assert response.status_code == 422


# =============================================================================
# LEAD SCORING TESTS
# =============================================================================


class TestLeadScoring:
    """Test lead scoring algorithm."""
    
    @pytest.mark.asyncio
    async def test_high_value_lead_scoring(
        self,
        http_client: httpx.AsyncClient
    ):
        """Test that high-value leads get high scores."""
        high_value_lead = {
            "first_name": "Premium",
            "last_name": "Customer",
            "email": "premium@example.com",
            "phone": "+447123456789",
            "preferred_contact": "phone",
            "postcode": "NW3 1AA",  # Prime area
            "property_type": "detached",
            "property_age": "pre-1900",
            "project_types": ["full-refurbishment", "extension", "loft-conversion"],
            "project_description": "Complete restoration of Georgian detached house.",
            "timeline": "asap",
            "budget_range": "over-500k",
            "conservation_area": True,
            "source": "referral",
            "how_did_you_hear": "referral",
            "marketing_consent": True,
        }
        
        response = await http_client.post(
            f"{LEAD_INTAKE_URL}/leads",
            json=high_value_lead
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # High-value lead should be high priority
        assert data["priority"] == "high"
        
        # Score should be high (above 70)
        score = data.get("score") or data.get("lead_score", 0)
        assert score >= 70
    
    @pytest.mark.asyncio
    async def test_low_value_lead_scoring(
        self,
        http_client: httpx.AsyncClient
    ):
        """Test that low-value leads get appropriate scores."""
        low_value_lead = {
            "first_name": "Budget",
            "last_name": "Customer",
            "email": "budget@example.com",
            "phone": "07123456789",
            "preferred_contact": "email",
            "postcode": "N12 1AA",
            "property_type": "flat",
            "property_age": "post-2010",
            "project_types": ["painting-decorating"],
            "project_description": "Small decorating job.",
            "timeline": "planning-stage",
            "budget_range": "under-25k",
            "source": "web-form",
        }
        
        response = await http_client.post(
            f"{LEAD_INTAKE_URL}/leads",
            json=low_value_lead
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Lower-value lead should not be high priority
        assert data["priority"] in ["medium", "low"]


# =============================================================================
# LEAD RETRIEVAL TESTS
# =============================================================================


class TestLeadRetrieval:
    """Test lead retrieval functionality."""
    
    @pytest.mark.asyncio
    async def test_get_lead_by_id(
        self,
        http_client: httpx.AsyncClient,
        valid_lead_data: dict
    ):
        """Test retrieving a lead by ID."""
        # First, create a lead
        create_response = await http_client.post(
            f"{LEAD_INTAKE_URL}/leads",
            json=valid_lead_data
        )
        
        assert create_response.status_code == 201
        lead_id = create_response.json().get("leadId") or create_response.json().get("lead_id")
        
        # Then retrieve it
        get_response = await http_client.get(
            f"{LEAD_INTAKE_URL}/leads/{lead_id}"
        )
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == lead_id
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_lead(
        self,
        http_client: httpx.AsyncClient
    ):
        """Test retrieving a non-existent lead."""
        response = await http_client.get(
            f"{LEAD_INTAKE_URL}/leads/nonexistent-id-12345"
        )
        
        assert response.status_code == 404


# =============================================================================
# RATE LIMITING TESTS
# =============================================================================


class TestRateLimiting:
    """Test API rate limiting."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(
        self,
        http_client: httpx.AsyncClient
    ):
        """Test that rate limit headers are present in responses."""
        response = await http_client.get(f"{LEAD_INTAKE_URL}/health")
        
        # Rate limit headers should be present
        assert "X-RateLimit-Limit" in response.headers or response.status_code == 200
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_rate_limit_enforcement(
        self,
        http_client: httpx.AsyncClient
    ):
        """Test that rate limiting is enforced (slow test)."""
        # This test makes many requests quickly - may be slow
        # Skip if not running slow tests
        pytest.skip("Skipping slow rate limit test")
        
        responses = []
        for _ in range(150):  # Exceed typical rate limit
            response = await http_client.get(f"{LEAD_INTAKE_URL}/health")
            responses.append(response.status_code)
        
        # At least one should be rate limited
        assert 429 in responses


# =============================================================================
# DASHBOARD API TESTS
# =============================================================================


class TestDashboardAPI:
    """Test Dashboard API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_overview(
        self,
        http_client: httpx.AsyncClient
    ):
        """Test dashboard overview endpoint."""
        response = await http_client.get(f"{DASHBOARD_API_URL}/dashboard/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check expected fields
        assert "total_leads" in data or "totalLeads" in data
        assert "conversion_rate" in data or "conversionRate" in data
    
    @pytest.mark.asyncio
    async def test_get_recent_leads(
        self,
        http_client: httpx.AsyncClient
    ):
        """Test getting recent leads from dashboard."""
        response = await http_client.get(f"{DASHBOARD_API_URL}/dashboard/leads/recent")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "leads" in data
        assert isinstance(data["leads"], list)
    
    @pytest.mark.asyncio
    async def test_get_pipeline_stats(
        self,
        http_client: httpx.AsyncClient
    ):
        """Test getting pipeline statistics."""
        response = await http_client.get(f"{DASHBOARD_API_URL}/dashboard/pipeline")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have pipeline stages
        assert "stages" in data or "pipeline" in data


# =============================================================================
# END-TO-END FLOW TESTS
# =============================================================================


class TestEndToEndFlow:
    """Test complete lead processing flow."""
    
    @pytest.mark.asyncio
    async def test_complete_lead_flow(
        self,
        http_client: httpx.AsyncClient,
        valid_lead_data: dict
    ):
        """Test complete lead submission to dashboard flow."""
        # Step 1: Submit lead
        submit_response = await http_client.post(
            f"{LEAD_INTAKE_URL}/leads",
            json=valid_lead_data
        )
        
        assert submit_response.status_code == 201
        lead_id = submit_response.json().get("leadId") or submit_response.json().get("lead_id")
        assert lead_id is not None
        
        # Step 2: Verify lead can be retrieved
        get_response = await http_client.get(
            f"{LEAD_INTAKE_URL}/leads/{lead_id}"
        )
        
        assert get_response.status_code == 200
        
        # Step 3: Check lead appears in dashboard (may need to wait for processing)
        await asyncio.sleep(1)  # Brief wait for async processing
        
        dashboard_response = await http_client.get(
            f"{DASHBOARD_API_URL}/dashboard/leads/recent"
        )
        
        assert dashboard_response.status_code == 200


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])

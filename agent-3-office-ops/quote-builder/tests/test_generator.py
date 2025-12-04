"""
Hampstead Renovations - Quote Builder Tests
============================================

Unit tests for the quote generation service.
"""

import os
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# Import the modules we're testing
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from generator import (
    Settings,
    CustomerDetails,
    ProjectDetails,
    QuoteRequest,
    PricingEngine,
    QuotePDFGenerator,
    QuoteService,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def settings():
    """Create test settings using environment variables."""
    return Settings(
        database_url=os.environ.get("TEST_DATABASE_URL", "postgresql://test:test@localhost:5432/test"),
        aws_access_key_id=os.environ.get("TEST_AWS_ACCESS_KEY_ID", ""),
        aws_secret_access_key=os.environ.get("TEST_AWS_SECRET_ACCESS_KEY", ""),
        s3_bucket_name=os.environ.get("TEST_S3_BUCKET", "test-bucket"),
        hubspot_api_key=os.environ.get("TEST_HUBSPOT_API_KEY", ""),
    )


@pytest.fixture
def sample_customer():
    """Create a sample customer for testing."""
    return CustomerDetails(
        name="John Smith",
        email="john.smith@example.com",
        phone="+44 7700 900123",
        address_line1="42 Hampstead High Street",
        city="London",
        postcode="NW3 1QE",
    )


@pytest.fixture
def sample_project():
    """Create a sample project for testing."""
    return ProjectDetails(
        project_type="kitchen",
        tier="premium",
        estimated_sqm=Decimal("25"),
        requirements=["Modern handleless design", "Quartz worktops"],
        special_requests="Would like underfloor heating",
    )


@pytest.fixture
def sample_quote_request(sample_customer, sample_project):
    """Create a sample quote request."""
    return QuoteRequest(
        customer=sample_customer,
        project=sample_project,
    )


# =============================================================================
# CUSTOMER DETAILS TESTS
# =============================================================================


class TestCustomerDetails:
    """Tests for CustomerDetails model."""

    def test_valid_customer_creation(self):
        """Test creating a valid customer."""
        customer = CustomerDetails(
            name="Jane Doe",
            email="jane@example.com",
            phone="+44 7700 900456",
            address_line1="123 Test Street",
            city="London",
            postcode="NW1 1AA",
        )
        assert customer.name == "Jane Doe"
        assert customer.email == "jane@example.com"

    def test_invalid_email_rejected(self):
        """Test that invalid email is rejected."""
        with pytest.raises(ValueError):
            CustomerDetails(
                name="Test",
                email="not-an-email",
                phone="+44 7700 900123",
                address_line1="123 Test St",
                city="London",
                postcode="NW1 1AA",
            )

    def test_optional_fields(self):
        """Test that optional fields are handled correctly."""
        customer = CustomerDetails(
            name="Test User",
            email="test@example.com",
            phone="+44 7700 900123",
            address_line1="123 Main St",
            city="London",
            postcode="NW3 1QE",
        )
        assert customer.address_line2 is None
        assert customer.county is None


# =============================================================================
# PROJECT DETAILS TESTS
# =============================================================================


class TestProjectDetails:
    """Tests for ProjectDetails model."""

    def test_valid_project_creation(self):
        """Test creating a valid project."""
        project = ProjectDetails(
            project_type="bathroom",
            tier="luxury",
            estimated_sqm=Decimal("12"),
        )
        assert project.project_type == "bathroom"
        assert project.tier == "luxury"

    def test_project_type_validation(self):
        """Test that invalid project types are rejected."""
        with pytest.raises(ValueError):
            ProjectDetails(
                project_type="invalid_type",
                tier="premium",
                estimated_sqm=Decimal("20"),
            )

    def test_tier_validation(self):
        """Test that invalid tiers are rejected."""
        with pytest.raises(ValueError):
            ProjectDetails(
                project_type="kitchen",
                tier="super_luxury",
                estimated_sqm=Decimal("20"),
            )

    def test_sqm_must_be_positive(self):
        """Test that negative sqm is rejected."""
        with pytest.raises(ValueError):
            ProjectDetails(
                project_type="kitchen",
                tier="premium",
                estimated_sqm=Decimal("-5"),
            )


# =============================================================================
# PRICING ENGINE TESTS
# =============================================================================


class TestPricingEngine:
    """Tests for PricingEngine."""

    @pytest.fixture
    def pricing_engine(self):
        """Create a pricing engine for testing."""
        return PricingEngine()

    def test_load_pricing_matrix(self, pricing_engine):
        """Test that pricing matrix is loaded."""
        assert pricing_engine.pricing_matrix is not None
        assert "kitchen" in pricing_engine.pricing_matrix

    def test_calculate_base_price_kitchen_essential(self, pricing_engine):
        """Test base price calculation for essential kitchen."""
        price = pricing_engine.calculate_base_price("kitchen", "essential", Decimal("20"))
        assert price > 0
        assert isinstance(price, Decimal)

    def test_calculate_base_price_kitchen_premium(self, pricing_engine):
        """Test base price calculation for premium kitchen."""
        essential_price = pricing_engine.calculate_base_price("kitchen", "essential", Decimal("20"))
        premium_price = pricing_engine.calculate_base_price("kitchen", "premium", Decimal("20"))
        
        # Premium should be more expensive than essential
        assert premium_price > essential_price

    def test_calculate_base_price_kitchen_luxury(self, pricing_engine):
        """Test base price calculation for luxury kitchen."""
        premium_price = pricing_engine.calculate_base_price("kitchen", "premium", Decimal("20"))
        luxury_price = pricing_engine.calculate_base_price("kitchen", "luxury", Decimal("20"))
        
        # Luxury should be more expensive than premium
        assert luxury_price > premium_price

    def test_location_multiplier_hampstead(self, pricing_engine):
        """Test location multiplier for Hampstead (NW3)."""
        multiplier = pricing_engine.get_location_multiplier("NW3 1QE")
        
        # Hampstead should have a premium multiplier
        assert multiplier >= 1.0

    def test_location_multiplier_default(self, pricing_engine):
        """Test default location multiplier for unknown postcodes."""
        multiplier = pricing_engine.get_location_multiplier("XX1 1XX")
        
        # Default should be 1.0
        assert multiplier == Decimal("1.0")

    def test_vat_calculation(self, pricing_engine):
        """Test VAT calculation at 20%."""
        subtotal = Decimal("10000")
        vat = pricing_engine.calculate_vat(subtotal)
        
        assert vat == Decimal("2000")

    def test_discount_calculation(self, pricing_engine):
        """Test discount calculation."""
        subtotal = Decimal("10000")
        discount = pricing_engine.calculate_discount(subtotal, Decimal("10"))
        
        assert discount == Decimal("1000")


# =============================================================================
# QUOTE SERVICE TESTS
# =============================================================================


class TestQuoteService:
    """Tests for QuoteService."""

    @pytest.fixture
    def quote_service(self):
        """Create a quote service for testing."""
        return QuoteService()

    def test_generate_quote_number(self, quote_service):
        """Test quote number generation."""
        quote_number = quote_service._generate_quote_number()
        
        assert quote_number.startswith("QTE-")
        assert len(quote_number) == 18  # QTE-YYYY-NNNNNN format

    def test_quote_number_uniqueness(self, quote_service):
        """Test that quote numbers are unique."""
        numbers = [quote_service._generate_quote_number() for _ in range(100)]
        
        # All numbers should be unique
        assert len(numbers) == len(set(numbers))

    @pytest.mark.asyncio
    async def test_generate_quote_success(self, quote_service, sample_quote_request):
        """Test successful quote generation."""
        with patch.object(quote_service, "_save_to_s3", new_callable=AsyncMock) as mock_s3:
            mock_s3.return_value = "s3://bucket/quote.pdf"
            
            with patch.object(quote_service, "_update_hubspot", new_callable=AsyncMock):
                result = await quote_service.generate(sample_quote_request)
        
        assert result is not None
        assert result.quote_number.startswith("QTE-")
        assert result.total > 0
        assert result.subtotal > 0

    @pytest.mark.asyncio
    async def test_generate_quote_calculates_vat(self, quote_service, sample_quote_request):
        """Test that VAT is correctly calculated."""
        with patch.object(quote_service, "_save_to_s3", new_callable=AsyncMock) as mock_s3:
            mock_s3.return_value = None
            
            with patch.object(quote_service, "_update_hubspot", new_callable=AsyncMock):
                result = await quote_service.generate(sample_quote_request)
        
        # VAT should be 20% of subtotal (after discount)
        expected_vat = (result.subtotal - result.discount) * Decimal("0.20")
        assert abs(result.vat - expected_vat) < Decimal("0.01")


# =============================================================================
# QUOTE PDF GENERATOR TESTS
# =============================================================================


class TestQuotePDFGenerator:
    """Tests for QuotePDFGenerator."""

    @pytest.fixture
    def pdf_generator(self):
        """Create a PDF generator for testing."""
        return QuotePDFGenerator()

    def test_pdf_generation(self, pdf_generator, sample_customer, sample_project):
        """Test that PDF can be generated."""
        quote_data = {
            "quote_number": "QTE-2024-000001",
            "customer": sample_customer,
            "project": sample_project,
            "line_items": [
                {"description": "Kitchen Cabinets", "quantity": 1, "unit_price": Decimal("5000"), "total": Decimal("5000")},
            ],
            "subtotal": Decimal("5000"),
            "discount": Decimal("250"),
            "vat": Decimal("950"),
            "total": Decimal("5700"),
            "valid_until": datetime.now(),
        }
        
        pdf_bytes = pdf_generator.generate(quote_data)
        
        assert pdf_bytes is not None
        assert len(pdf_bytes) > 0
        # Check PDF magic bytes
        assert pdf_bytes[:4] == b"%PDF"


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================


class TestAPIEndpoints:
    """Tests for FastAPI endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        from fastapi.testclient import TestClient
        from generator import app
        
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "quote-builder"

    def test_project_types_endpoint(self, client):
        """Test project types endpoint."""
        response = client.get("/project-types")
        
        assert response.status_code == 200
        data = response.json()
        assert "project_types" in data
        assert "kitchen" in data["project_types"]
        assert "tiers" in data
        assert "essential" in data["tiers"]

    def test_pricing_matrix_endpoint(self, client):
        """Test pricing matrix endpoint."""
        response = client.get("/pricing-matrix")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "pricing_matrix" in data

    def test_generate_quote_endpoint(self, client, sample_quote_request):
        """Test quote generation endpoint."""
        with patch("generator.quote_service.generate", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = MagicMock(
                quote_number="QTE-2024-000001",
                total=Decimal("10000"),
                subtotal=Decimal("8500"),
                vat=Decimal("1700"),
                discount=Decimal("200"),
                s3_url="s3://bucket/quote.pdf",
                pdf_path="/tmp/quote.pdf",
            )
            
            response = client.post(
                "/generate",
                json={
                    "customer": {
                        "name": "John Smith",
                        "email": "john@example.com",
                        "phone": "+44 7700 900123",
                        "address_line1": "123 Test St",
                        "city": "London",
                        "postcode": "NW3 1QE",
                    },
                    "project": {
                        "project_type": "kitchen",
                        "tier": "premium",
                        "estimated_sqm": 25,
                    },
                },
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "quote_number" in data
        assert "total" in data


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests for the quote system."""

    @pytest.mark.asyncio
    async def test_full_quote_workflow(self, sample_quote_request):
        """Test the complete quote generation workflow."""
        service = QuoteService()
        
        with patch.object(service, "_save_to_s3", new_callable=AsyncMock) as mock_s3:
            mock_s3.return_value = None
            
            with patch.object(service, "_update_hubspot", new_callable=AsyncMock):
                result = await service.generate(sample_quote_request)
        
        # Verify all components worked together
        assert result.quote_number is not None
        assert result.total > 0
        assert result.pdf_path is not None

    @pytest.mark.asyncio
    async def test_large_project_pricing(self):
        """Test pricing for a large project."""
        service = QuoteService()
        
        request = QuoteRequest(
            customer=CustomerDetails(
                name="Test Client",
                email="test@example.com",
                phone="+44 7700 900123",
                address_line1="1 Big House",
                city="London",
                postcode="NW3 1QE",
            ),
            project=ProjectDetails(
                project_type="full_renovation",
                tier="luxury",
                estimated_sqm=Decimal("200"),
            ),
        )
        
        with patch.object(service, "_save_to_s3", new_callable=AsyncMock):
            with patch.object(service, "_update_hubspot", new_callable=AsyncMock):
                result = await service.generate(request)
        
        # Large luxury project should be expensive
        assert result.total > Decimal("100000")

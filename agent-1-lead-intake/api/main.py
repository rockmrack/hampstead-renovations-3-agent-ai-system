"""
Hampstead Renovations - Lead Intake API
=======================================

API service for receiving and processing leads from the web form.
Validates, scores, and routes leads to the CRM system.
"""

import os
import uuid
import httpx
import structlog
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic_settings import BaseSettings
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


# =============================================================================
# CONFIGURATION
# =============================================================================


class Settings(BaseSettings):
    """Application configuration."""
    
    # App settings
    app_name: str = "Lead Intake API"
    version: str = "1.0.0"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    
    # API Security
    api_key: str = Field(default="")
    allowed_origins: str = Field(default="http://localhost:3000,http://localhost:5173")
    
    # HubSpot Integration
    hubspot_api_key: str = Field(default="")
    hubspot_portal_id: str = Field(default="")
    
    # n8n Webhook
    n8n_webhook_url: str = Field(default="http://n8n:5678/webhook/lead-intake")
    
    # Database
    database_url: str = Field(default="postgresql://hampstead:password@localhost:5432/hampstead_renovations")
    
    # Redis for rate limiting
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger(__name__)


# =============================================================================
# RATE LIMITING
# =============================================================================

limiter = Limiter(key_func=get_remote_address)


# =============================================================================
# MODELS
# =============================================================================


class ContactDetails(BaseModel):
    """Customer contact information."""
    
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Remove spaces and validate
        cleaned = v.replace(" ", "").replace("-", "")
        if not cleaned.replace("+", "").isdigit():
            raise ValueError("Phone must contain only digits")
        return v


class AddressDetails(BaseModel):
    """Project address information."""
    
    address_line1: str = Field(..., min_length=1, max_length=200)
    address_line2: Optional[str] = Field(None, max_length=200)
    city: str = Field(..., min_length=1, max_length=100)
    postcode: str = Field(..., min_length=5, max_length=10)
    
    @field_validator("postcode")
    @classmethod
    def validate_postcode(cls, v: str) -> str:
        # Basic UK postcode validation
        cleaned = v.upper().replace(" ", "")
        if len(cleaned) < 5 or len(cleaned) > 8:
            raise ValueError("Invalid UK postcode format")
        return v.upper()


class ProjectDetails(BaseModel):
    """Project requirements."""
    
    project_type: str = Field(..., description="Type of renovation project")
    budget_range: str = Field(..., description="Budget range")
    timeline: str = Field(..., description="Desired timeline")
    property_type: Optional[str] = Field(None, description="Type of property")
    description: Optional[str] = Field(None, max_length=2000)
    
    @field_validator("project_type")
    @classmethod
    def validate_project_type(cls, v: str) -> str:
        valid_types = [
            "kitchen", "bathroom", "extension", "loft_conversion",
            "full_renovation", "flooring", "electrical", "plumbing",
            "painting", "landscaping", "other"
        ]
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid project type. Must be one of: {valid_types}")
        return v.lower()
    
    @field_validator("budget_range")
    @classmethod
    def validate_budget(cls, v: str) -> str:
        valid_ranges = [
            "under_10000", "10000-25000", "25000-50000",
            "50000-100000", "100000-200000", "200000_plus", "not_sure"
        ]
        if v.lower() not in valid_ranges:
            raise ValueError(f"Invalid budget range")
        return v.lower()
    
    @field_validator("timeline")
    @classmethod
    def validate_timeline(cls, v: str) -> str:
        valid_timelines = [
            "asap", "1-3_months", "3-6_months", "6-12_months", "flexible"
        ]
        if v.lower() not in valid_timelines:
            raise ValueError(f"Invalid timeline")
        return v.lower()


class LeadSubmission(BaseModel):
    """Complete lead submission from web form."""
    
    contact: ContactDetails
    address: AddressDetails
    project: ProjectDetails
    marketing_consent: bool = Field(default=False)
    source: str = Field(default="web_form")
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


class LeadResponse(BaseModel):
    """Response after lead submission."""
    
    success: bool
    lead_id: str
    message: str
    estimated_response_time: str


class LeadScore(BaseModel):
    """Lead scoring breakdown."""
    
    total_score: int
    budget_score: int
    timeline_score: int
    location_score: int
    project_score: int
    qualification: str  # hot, warm, cold


# =============================================================================
# LEAD SCORING ENGINE
# =============================================================================


class LeadScoringEngine:
    """Calculates lead quality scores."""
    
    # Premium postcodes (Hampstead area)
    PREMIUM_POSTCODES = ["NW3", "NW6", "NW8", "NW11", "N6", "N2", "N10"]
    
    def calculate_score(self, lead: LeadSubmission) -> LeadScore:
        """Calculate comprehensive lead score."""
        
        budget_score = self._score_budget(lead.project.budget_range)
        timeline_score = self._score_timeline(lead.project.timeline)
        location_score = self._score_location(lead.address.postcode)
        project_score = self._score_project_type(lead.project.project_type)
        
        total_score = budget_score + timeline_score + location_score + project_score
        
        # Determine qualification level
        if total_score >= 80:
            qualification = "hot"
        elif total_score >= 50:
            qualification = "warm"
        else:
            qualification = "cold"
        
        return LeadScore(
            total_score=total_score,
            budget_score=budget_score,
            timeline_score=timeline_score,
            location_score=location_score,
            project_score=project_score,
            qualification=qualification,
        )
    
    def _score_budget(self, budget_range: str) -> int:
        """Score based on budget (max 30 points)."""
        scores = {
            "200000_plus": 30,
            "100000-200000": 27,
            "50000-100000": 23,
            "25000-50000": 18,
            "10000-25000": 12,
            "under_10000": 6,
            "not_sure": 15,
        }
        return scores.get(budget_range, 10)
    
    def _score_timeline(self, timeline: str) -> int:
        """Score based on timeline (max 25 points)."""
        scores = {
            "asap": 25,
            "1-3_months": 22,
            "3-6_months": 16,
            "6-12_months": 10,
            "flexible": 14,
        }
        return scores.get(timeline, 10)
    
    def _score_location(self, postcode: str) -> int:
        """Score based on location (max 25 points)."""
        prefix = postcode.upper().split()[0] if " " in postcode else postcode[:3].upper()
        
        if any(prefix.startswith(p) for p in self.PREMIUM_POSTCODES):
            return 25
        elif prefix.startswith("N") or prefix.startswith("NW"):
            return 20
        elif prefix.startswith("W") or prefix.startswith("SW"):
            return 18
        else:
            return 12
    
    def _score_project_type(self, project_type: str) -> int:
        """Score based on project type (max 20 points)."""
        scores = {
            "full_renovation": 20,
            "extension": 19,
            "loft_conversion": 18,
            "kitchen": 16,
            "bathroom": 14,
            "flooring": 10,
            "painting": 8,
            "electrical": 12,
            "plumbing": 12,
            "landscaping": 10,
            "other": 10,
        }
        return scores.get(project_type, 10)


# =============================================================================
# API AUTHENTICATION
# =============================================================================


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """Verify API key for protected endpoints."""
    if not settings.api_key:
        return True  # No API key configured, allow all
    
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return True


# =============================================================================
# BACKGROUND TASKS
# =============================================================================


async def send_to_n8n(lead_id: str, lead_data: dict, score: LeadScore):
    """Send lead to n8n workflow for processing."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "lead_id": lead_id,
                "lead_data": lead_data,
                "score": score.model_dump(),
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            response = await client.post(
                settings.n8n_webhook_url,
                json=payload,
            )
            
            if response.status_code == 200:
                logger.info("lead_sent_to_n8n", lead_id=lead_id, status="success")
            else:
                logger.warning("n8n_webhook_failed", lead_id=lead_id, status_code=response.status_code)
                
    except Exception as e:
        logger.error("n8n_webhook_error", lead_id=lead_id, error=str(e))


async def send_to_hubspot(lead_id: str, lead: LeadSubmission, score: LeadScore):
    """Create or update contact in HubSpot."""
    if not settings.hubspot_api_key:
        logger.warning("hubspot_not_configured", lead_id=lead_id)
        return
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create contact
            contact_data = {
                "properties": {
                    "firstname": lead.contact.first_name,
                    "lastname": lead.contact.last_name,
                    "email": lead.contact.email,
                    "phone": lead.contact.phone,
                    "address": lead.address.address_line1,
                    "city": lead.address.city,
                    "zip": lead.address.postcode,
                    "lead_score": str(score.total_score),
                    "lead_qualification": score.qualification,
                    "project_type": lead.project.project_type,
                    "budget_range": lead.project.budget_range,
                    "timeline": lead.project.timeline,
                    "lead_source": lead.source,
                }
            }
            
            response = await client.post(
                "https://api.hubapi.com/crm/v3/objects/contacts",
                json=contact_data,
                headers={
                    "Authorization": f"Bearer {settings.hubspot_api_key}",
                    "Content-Type": "application/json",
                },
            )
            
            if response.status_code in [200, 201]:
                logger.info("hubspot_contact_created", lead_id=lead_id)
            else:
                logger.warning("hubspot_create_failed", lead_id=lead_id, response=response.text)
                
    except Exception as e:
        logger.error("hubspot_error", lead_id=lead_id, error=str(e))


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("application_starting", version=settings.version)
    yield
    logger.info("application_shutting_down")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Lead intake API for Hampstead Renovations",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted host middleware
if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["hampsteadrenovations.co.uk", "*.hampsteadrenovations.co.uk"],
    )

# Initialize scoring engine
scoring_engine = LeadScoringEngine()


# =============================================================================
# API ENDPOINTS
# =============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "lead-intake-api",
        "version": settings.version,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes/Docker."""
    return {
        "status": "ready",
        "hubspot_configured": bool(settings.hubspot_api_key),
        "n8n_configured": bool(settings.n8n_webhook_url),
    }


@app.post("/api/v1/leads", response_model=LeadResponse)
@limiter.limit("10/minute")
async def submit_lead(
    lead: LeadSubmission,
    background_tasks: BackgroundTasks,
    request = None,
):
    """
    Submit a new lead from the web form.
    
    Rate limited to 10 requests per minute per IP.
    """
    try:
        # Generate lead ID
        lead_id = f"LEAD-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        logger.info(
            "lead_received",
            lead_id=lead_id,
            email=lead.contact.email,
            project_type=lead.project.project_type,
        )
        
        # Score the lead
        score = scoring_engine.calculate_score(lead)
        
        logger.info(
            "lead_scored",
            lead_id=lead_id,
            total_score=score.total_score,
            qualification=score.qualification,
        )
        
        # Queue background tasks
        lead_data = lead.model_dump()
        background_tasks.add_task(send_to_n8n, lead_id, lead_data, score)
        background_tasks.add_task(send_to_hubspot, lead_id, lead, score)
        
        # Determine response time based on score
        if score.qualification == "hot":
            response_time = "within 1 hour"
        elif score.qualification == "warm":
            response_time = "within 4 hours"
        else:
            response_time = "within 24 hours"
        
        return LeadResponse(
            success=True,
            lead_id=lead_id,
            message="Thank you for your inquiry! We've received your request and will be in touch soon.",
            estimated_response_time=response_time,
        )
        
    except Exception as e:
        logger.error("lead_submission_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to process lead submission")


@app.post("/api/v1/leads/score", response_model=LeadScore)
@limiter.limit("20/minute")
async def score_lead(
    lead: LeadSubmission,
    request = None,
    authenticated: bool = Depends(verify_api_key),
):
    """
    Score a lead without submitting it.
    
    Useful for testing and validation.
    """
    return scoring_engine.calculate_score(lead)


@app.get("/api/v1/config/project-types")
async def get_project_types():
    """Get available project types for the form."""
    return {
        "project_types": [
            {"value": "kitchen", "label": "Kitchen Renovation", "icon": "🍳"},
            {"value": "bathroom", "label": "Bathroom Renovation", "icon": "🚿"},
            {"value": "extension", "label": "House Extension", "icon": "🏗️"},
            {"value": "loft_conversion", "label": "Loft Conversion", "icon": "🏠"},
            {"value": "full_renovation", "label": "Full House Renovation", "icon": "🔨"},
            {"value": "flooring", "label": "Flooring", "icon": "🪵"},
            {"value": "electrical", "label": "Electrical Work", "icon": "⚡"},
            {"value": "plumbing", "label": "Plumbing", "icon": "🔧"},
            {"value": "painting", "label": "Painting & Decorating", "icon": "🎨"},
            {"value": "landscaping", "label": "Garden & Landscaping", "icon": "🌳"},
            {"value": "other", "label": "Other", "icon": "📋"},
        ]
    }


@app.get("/api/v1/config/budget-ranges")
async def get_budget_ranges():
    """Get available budget ranges for the form."""
    return {
        "budget_ranges": [
            {"value": "under_10000", "label": "Under £10,000"},
            {"value": "10000-25000", "label": "£10,000 - £25,000"},
            {"value": "25000-50000", "label": "£25,000 - £50,000"},
            {"value": "50000-100000", "label": "£50,000 - £100,000"},
            {"value": "100000-200000", "label": "£100,000 - £200,000"},
            {"value": "200000_plus", "label": "£200,000+"},
            {"value": "not_sure", "label": "Not sure yet"},
        ]
    }


@app.get("/api/v1/config/timelines")
async def get_timelines():
    """Get available timeline options for the form."""
    return {
        "timelines": [
            {"value": "asap", "label": "As soon as possible"},
            {"value": "1-3_months", "label": "Within 1-3 months"},
            {"value": "3-6_months", "label": "Within 3-6 months"},
            {"value": "6-12_months", "label": "Within 6-12 months"},
            {"value": "flexible", "label": "I'm flexible"},
        ]
    }


# =============================================================================
# MAIN
# =============================================================================


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )

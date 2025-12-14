"""
Hampstead Renovations - Admin Dashboard API
============================================

Backend API for the admin dashboard providing:
- Lead statistics and analytics
- Pipeline overview
- Revenue metrics
- Real-time monitoring
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List
from decimal import Decimal

import uvicorn
import structlog
from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


# =============================================================================
# CONFIGURATION
# =============================================================================


class Settings(BaseSettings):
    """Application configuration."""
    
    app_name: str = "Admin Dashboard API"
    version: str = "1.0.0"
    environment: str = Field(default="development")
    debug: bool = Field(default=True)
    
    # API Security
    api_key: str = Field(default="")
    admin_api_key: str = Field(default="")
    
    # Database
    database_url: str = Field(default="postgresql://hampstead:password@localhost:5432/hampstead_renovations")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger(__name__)


# =============================================================================
# MODELS
# =============================================================================


class LeadStats(BaseModel):
    """Lead statistics."""
    total_leads: int
    new_leads_today: int
    new_leads_this_week: int
    new_leads_this_month: int
    hot_leads: int
    warm_leads: int
    cold_leads: int
    conversion_rate: float
    average_score: float


class PipelineStage(BaseModel):
    """Pipeline stage summary."""
    stage: str
    count: int
    total_value: float
    average_value: float
    average_days_in_stage: float


class PipelineOverview(BaseModel):
    """Complete pipeline overview."""
    stages: List[PipelineStage]
    total_deals: int
    total_pipeline_value: float
    weighted_pipeline_value: float
    average_deal_size: float
    win_rate: float


class RevenueMetrics(BaseModel):
    """Revenue metrics."""
    revenue_today: float
    revenue_this_week: float
    revenue_this_month: float
    revenue_this_year: float
    outstanding_invoices: float
    overdue_invoices: float
    average_invoice_value: float
    invoices_paid_this_month: int


class MonthlyRevenue(BaseModel):
    """Monthly revenue data point."""
    month: str
    revenue: float
    invoice_count: int


class LeadSourcePerformance(BaseModel):
    """Lead source performance."""
    source: str
    lead_count: int
    conversion_rate: float
    total_revenue: float
    average_deal_value: float


class DashboardSummary(BaseModel):
    """Complete dashboard summary."""
    leads: LeadStats
    pipeline: PipelineOverview
    revenue: RevenueMetrics
    top_sources: List[LeadSourcePerformance]
    revenue_trend: List[MonthlyRevenue]
    updated_at: str


class RecentLead(BaseModel):
    """Recent lead entry."""
    id: str
    name: str
    email: str
    project_type: str
    budget_range: str
    score: int
    qualification: str
    created_at: str
    source: str


class ActiveDeal(BaseModel):
    """Active deal in pipeline."""
    id: str
    customer_name: str
    project_type: str
    value: float
    stage: str
    probability: int
    expected_close_date: Optional[str]
    days_in_stage: int
    last_activity: str


# =============================================================================
# MOCK DATA SERVICE (Replace with database queries)
# =============================================================================


class DashboardService:
    """Service for dashboard data retrieval."""
    
    def get_lead_stats(self) -> LeadStats:
        """Get lead statistics."""
        # Mock data - replace with actual database queries
        return LeadStats(
            total_leads=247,
            new_leads_today=8,
            new_leads_this_week=34,
            new_leads_this_month=89,
            hot_leads=23,
            warm_leads=67,
            cold_leads=157,
            conversion_rate=28.5,
            average_score=62.3,
        )
    
    def get_pipeline_overview(self) -> PipelineOverview:
        """Get pipeline overview."""
        stages = [
            PipelineStage(stage="New Lead", count=34, total_value=680000, average_value=20000, average_days_in_stage=2.3),
            PipelineStage(stage="Qualified", count=28, total_value=840000, average_value=30000, average_days_in_stage=5.1),
            PipelineStage(stage="Quote Sent", count=19, total_value=760000, average_value=40000, average_days_in_stage=7.2),
            PipelineStage(stage="Negotiation", count=12, total_value=600000, average_value=50000, average_days_in_stage=10.5),
            PipelineStage(stage="Verbal Accept", count=8, total_value=480000, average_value=60000, average_days_in_stage=3.8),
            PipelineStage(stage="Contract Sent", count=5, total_value=350000, average_value=70000, average_days_in_stage=4.2),
        ]
        
        return PipelineOverview(
            stages=stages,
            total_deals=106,
            total_pipeline_value=3710000,
            weighted_pipeline_value=1855000,
            average_deal_size=35000,
            win_rate=32.5,
        )
    
    def get_revenue_metrics(self) -> RevenueMetrics:
        """Get revenue metrics."""
        return RevenueMetrics(
            revenue_today=12500,
            revenue_this_week=87500,
            revenue_this_month=342000,
            revenue_this_year=2850000,
            outstanding_invoices=425000,
            overdue_invoices=67500,
            average_invoice_value=28500,
            invoices_paid_this_month=12,
        )
    
    def get_revenue_trend(self, months: int = 12) -> List[MonthlyRevenue]:
        """Get monthly revenue trend."""
        # Mock data - generate last N months
        trend = []
        base_revenue = 250000
        
        for i in range(months - 1, -1, -1):
            date = datetime.now() - timedelta(days=30 * i)
            month_str = date.strftime("%Y-%m")
            
            # Add some variance
            variance = (hash(month_str) % 40000) - 20000
            revenue = base_revenue + variance + (i * 5000)  # Growth trend
            
            trend.append(MonthlyRevenue(
                month=month_str,
                revenue=revenue,
                invoice_count=8 + (hash(month_str) % 6),
            ))
        
        return trend
    
    def get_top_sources(self, limit: int = 5) -> List[LeadSourcePerformance]:
        """Get top performing lead sources."""
        return [
            LeadSourcePerformance(source="Google Ads", lead_count=67, conversion_rate=35.2, total_revenue=845000, average_deal_value=36000),
            LeadSourcePerformance(source="Word of Mouth", lead_count=45, conversion_rate=48.9, total_revenue=720000, average_deal_value=32700),
            LeadSourcePerformance(source="Houzz", lead_count=38, conversion_rate=31.6, total_revenue=456000, average_deal_value=38000),
            LeadSourcePerformance(source="Website Form", lead_count=52, conversion_rate=26.9, total_revenue=378000, average_deal_value=27000),
            LeadSourcePerformance(source="Checkatrade", lead_count=29, conversion_rate=24.1, total_revenue=203000, average_deal_value=29000),
        ][:limit]
    
    def get_recent_leads(self, limit: int = 10) -> List[RecentLead]:
        """Get recent leads."""
        # Mock data
        return [
            RecentLead(id="LEAD-20251215-A1B2C3D4", name="James Wilson", email="james.w@example.com", project_type="kitchen", budget_range="50000-100000", score=85, qualification="hot", created_at="2025-12-15T10:30:00Z", source="Google Ads"),
            RecentLead(id="LEAD-20251215-E5F6G7H8", name="Sarah Thompson", email="sarah.t@example.com", project_type="extension", budget_range="100000-200000", score=92, qualification="hot", created_at="2025-12-15T09:15:00Z", source="Word of Mouth"),
            RecentLead(id="LEAD-20251214-I9J0K1L2", name="Michael Chen", email="m.chen@example.com", project_type="bathroom", budget_range="25000-50000", score=68, qualification="warm", created_at="2025-12-14T16:45:00Z", source="Houzz"),
            RecentLead(id="LEAD-20251214-M3N4O5P6", name="Emma Davies", email="emma.d@example.com", project_type="loft_conversion", budget_range="50000-100000", score=78, qualification="warm", created_at="2025-12-14T14:20:00Z", source="Website Form"),
            RecentLead(id="LEAD-20251214-Q7R8S9T0", name="David Brown", email="d.brown@example.com", project_type="full_renovation", budget_range="200000_plus", score=95, qualification="hot", created_at="2025-12-14T11:00:00Z", source="Previous Client"),
        ][:limit]
    
    def get_active_deals(self, limit: int = 10) -> List[ActiveDeal]:
        """Get active deals in pipeline."""
        return [
            ActiveDeal(id="DEAL-001", customer_name="Robert & Jane Miller", project_type="Full House Renovation", value=185000, stage="Contract Sent", probability=90, expected_close_date="2025-12-20", days_in_stage=3, last_activity="Contract reviewed by client"),
            ActiveDeal(id="DEAL-002", customer_name="Thomas Anderson", project_type="Kitchen Renovation", value=65000, stage="Negotiation", probability=70, expected_close_date="2025-12-28", days_in_stage=8, last_activity="Revised quote sent"),
            ActiveDeal(id="DEAL-003", customer_name="Catherine Wright", project_type="Loft Conversion", value=95000, stage="Quote Sent", probability=50, expected_close_date="2026-01-15", days_in_stage=5, last_activity="Quote viewed by client"),
            ActiveDeal(id="DEAL-004", customer_name="Peter & Susan Hall", project_type="Extension", value=145000, stage="Qualified", probability=30, expected_close_date="2026-02-01", days_in_stage=4, last_activity="Site visit scheduled"),
            ActiveDeal(id="DEAL-005", customer_name="Jennifer Lewis", project_type="Bathroom Renovation", value=38000, stage="Verbal Accept", probability=85, expected_close_date="2025-12-18", days_in_stage=2, last_activity="Contract being prepared"),
        ][:limit]


# =============================================================================
# API AUTHENTICATION
# =============================================================================


async def verify_admin_key(x_admin_key: Optional[str] = Header(None)) -> bool:
    """Verify admin API key."""
    if not settings.admin_api_key:
        return True  # No key configured
    
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin API key")
    
    return True


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Admin dashboard API for Hampstead Renovations",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
dashboard_service = DashboardService()


# =============================================================================
# ENDPOINTS
# =============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "admin-dashboard-api",
        "version": settings.version,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/api/v1/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(authenticated: bool = Depends(verify_admin_key)):
    """Get complete dashboard summary."""
    return DashboardSummary(
        leads=dashboard_service.get_lead_stats(),
        pipeline=dashboard_service.get_pipeline_overview(),
        revenue=dashboard_service.get_revenue_metrics(),
        top_sources=dashboard_service.get_top_sources(),
        revenue_trend=dashboard_service.get_revenue_trend(),
        updated_at=datetime.utcnow().isoformat(),
    )


@app.get("/api/v1/dashboard/leads", response_model=LeadStats)
async def get_lead_stats(authenticated: bool = Depends(verify_admin_key)):
    """Get lead statistics."""
    return dashboard_service.get_lead_stats()


@app.get("/api/v1/dashboard/pipeline", response_model=PipelineOverview)
async def get_pipeline(authenticated: bool = Depends(verify_admin_key)):
    """Get pipeline overview."""
    return dashboard_service.get_pipeline_overview()


@app.get("/api/v1/dashboard/revenue", response_model=RevenueMetrics)
async def get_revenue(authenticated: bool = Depends(verify_admin_key)):
    """Get revenue metrics."""
    return dashboard_service.get_revenue_metrics()


@app.get("/api/v1/dashboard/revenue/trend", response_model=List[MonthlyRevenue])
async def get_revenue_trend(
    months: int = Query(default=12, ge=1, le=24),
    authenticated: bool = Depends(verify_admin_key),
):
    """Get monthly revenue trend."""
    return dashboard_service.get_revenue_trend(months)


@app.get("/api/v1/dashboard/sources", response_model=List[LeadSourcePerformance])
async def get_source_performance(
    limit: int = Query(default=5, ge=1, le=20),
    authenticated: bool = Depends(verify_admin_key),
):
    """Get lead source performance."""
    return dashboard_service.get_top_sources(limit)


@app.get("/api/v1/leads/recent", response_model=List[RecentLead])
async def get_recent_leads(
    limit: int = Query(default=10, ge=1, le=50),
    authenticated: bool = Depends(verify_admin_key),
):
    """Get recent leads."""
    return dashboard_service.get_recent_leads(limit)


@app.get("/api/v1/deals/active", response_model=List[ActiveDeal])
async def get_active_deals(
    limit: int = Query(default=10, ge=1, le=50),
    authenticated: bool = Depends(verify_admin_key),
):
    """Get active deals in pipeline."""
    return dashboard_service.get_active_deals(limit)


# =============================================================================
# MAIN
# =============================================================================


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)

#!/bin/bash
# =============================================================================
# Hampstead Renovations - Production Deployment Script
# =============================================================================
# This script handles full deployment of the 3-Agent AI System
# Usage: ./deploy.sh [environment] [--skip-build] [--skip-migrations]
#
# Environments: development, staging, production
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="${1:-development}"
SKIP_BUILD=false
SKIP_MIGRATIONS=false
COMPOSE_FILE="docker-compose.yml"

# Parse additional arguments
shift || true
for arg in "$@"; do
    case $arg in
        --skip-build)
            SKIP_BUILD=true
            ;;
        --skip-migrations)
            SKIP_MIGRATIONS=true
            ;;
        --help)
            echo "Usage: ./deploy.sh [environment] [--skip-build] [--skip-migrations]"
            echo ""
            echo "Environments:"
            echo "  development  - Local development (default)"
            echo "  staging      - Staging environment"
            echo "  production   - Production environment"
            echo ""
            echo "Options:"
            echo "  --skip-build      Skip Docker image build"
            echo "  --skip-migrations Skip database migrations"
            exit 0
            ;;
    esac
done

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check .env file
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.template" ]]; then
            log_warning ".env file not found. Creating from template..."
            cp .env.template .env
            log_warning "Please edit .env with your actual configuration"
        else
            log_error ".env file not found and no template available"
            exit 1
        fi
    fi
    
    log_success "Prerequisites check passed"
}

validate_environment() {
    log_info "Validating environment configuration..."
    
    # Source environment file
    set -a
    source .env
    set +a
    
    # Check critical variables
    local required_vars=(
        "POSTGRES_PASSWORD"
        "N8N_ENCRYPTION_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Warn about default passwords in production
    if [[ "$ENVIRONMENT" == "production" ]]; then
        if [[ "${POSTGRES_PASSWORD:-}" == "hampstead_secure_password_change_me" ]]; then
            log_error "Default password detected in production. Please change POSTGRES_PASSWORD"
            exit 1
        fi
    fi
    
    log_success "Environment validation passed"
}

create_directories() {
    log_info "Creating required directories..."
    
    mkdir -p data/postgres
    mkdir -p data/redis
    mkdir -p data/n8n
    mkdir -p data/prometheus
    mkdir -p data/grafana
    mkdir -p logs
    
    # Set permissions for mounted volumes
    chmod -R 755 data
    
    log_success "Directories created"
}

pull_images() {
    log_info "Pulling latest Docker images..."
    
    docker compose -f "$COMPOSE_FILE" pull
    
    log_success "Images pulled"
}

build_services() {
    if [[ "$SKIP_BUILD" == true ]]; then
        log_info "Skipping build (--skip-build flag set)"
        return
    fi
    
    log_info "Building custom services..."
    
    # Build all custom services
    docker compose -f "$COMPOSE_FILE" build \
        --parallel \
        quote-builder \
        contract-generator \
        invoice-generator \
        web-form
    
    log_success "Services built"
}

run_migrations() {
    if [[ "$SKIP_MIGRATIONS" == true ]]; then
        log_info "Skipping migrations (--skip-migrations flag set)"
        return
    fi
    
    log_info "Running database migrations..."
    
    # Start only the database
    docker compose -f "$COMPOSE_FILE" up -d postgres
    
    # Wait for database to be ready
    log_info "Waiting for database to be ready..."
    local retries=30
    until docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U hampstead -d hampstead_renovations || [[ $retries -eq 0 ]]; do
        log_info "Waiting for PostgreSQL... ($retries attempts remaining)"
        retries=$((retries - 1))
        sleep 2
    done
    
    if [[ $retries -eq 0 ]]; then
        log_error "Database failed to become ready"
        exit 1
    fi
    
    log_success "Database migrations completed"
}

start_services() {
    log_info "Starting services for $ENVIRONMENT environment..."
    
    # Define services based on environment
    local services="postgres redis n8n quote-builder contract-generator invoice-generator web-form nginx"
    
    if [[ "$ENVIRONMENT" != "development" ]]; then
        services="$services prometheus grafana alertmanager"
    fi
    
    docker compose -f "$COMPOSE_FILE" up -d $services
    
    log_success "Services started"
}

wait_for_health() {
    log_info "Waiting for services to become healthy..."
    
    local services=(
        "postgres:5432"
        "redis:6379"
        "n8n:5678"
        "quote-builder:8001"
        "contract-generator:8002"
        "invoice-generator:8003"
    )
    
    for service in "${services[@]}"; do
        local name="${service%%:*}"
        local port="${service##*:}"
        
        log_info "Checking $name..."
        
        local retries=30
        until docker compose -f "$COMPOSE_FILE" exec -T "$name" nc -z localhost "$port" 2>/dev/null || [[ $retries -eq 0 ]]; do
            retries=$((retries - 1))
            sleep 2
        done
        
        if [[ $retries -eq 0 ]]; then
            log_warning "$name may not be healthy"
        else
            log_success "$name is healthy"
        fi
    done
}

run_health_checks() {
    log_info "Running health checks..."
    
    # Check API endpoints
    local endpoints=(
        "http://localhost:8001/health|Quote Builder"
        "http://localhost:8002/health|Contract Generator"
        "http://localhost:8003/health|Invoice Generator"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local url="${endpoint%%|*}"
        local name="${endpoint##*|}"
        
        if curl -sf "$url" > /dev/null 2>&1; then
            log_success "$name health check passed"
        else
            log_warning "$name health check failed (may still be starting)"
        fi
    done
}

display_summary() {
    echo ""
    echo "=============================================="
    echo -e "${GREEN}Deployment Complete!${NC}"
    echo "=============================================="
    echo ""
    echo "Services available at:"
    echo "  - n8n Workflow Engine:  http://localhost:5678"
    echo "  - Web Form:             http://localhost:3000"
    echo "  - Quote Builder API:    http://localhost:8001"
    echo "  - Contract Generator:   http://localhost:8002"
    echo "  - Invoice Generator:    http://localhost:8003"
    echo ""
    
    if [[ "$ENVIRONMENT" != "development" ]]; then
        echo "Monitoring:"
        echo "  - Prometheus:           http://localhost:9090"
        echo "  - Grafana:              http://localhost:3001"
        echo "  - Alertmanager:         http://localhost:9093"
        echo ""
    fi
    
    echo "API Documentation:"
    echo "  - Quote Builder:        http://localhost:8001/docs"
    echo "  - Contract Generator:   http://localhost:8002/docs"
    echo "  - Invoice Generator:    http://localhost:8003/docs"
    echo ""
    echo "Useful commands:"
    echo "  - View logs:            docker compose logs -f"
    echo "  - Stop services:        docker compose down"
    echo "  - View status:          docker compose ps"
    echo ""
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo ""
    echo "=============================================="
    echo "Hampstead Renovations - Deployment Script"
    echo "Environment: $ENVIRONMENT"
    echo "=============================================="
    echo ""
    
    check_prerequisites
    validate_environment
    create_directories
    
    if [[ "$SKIP_BUILD" == false ]]; then
        build_services
    fi
    
    run_migrations
    start_services
    wait_for_health
    run_health_checks
    display_summary
}

# Run main function
main

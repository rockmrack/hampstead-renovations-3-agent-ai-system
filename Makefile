# ═══════════════════════════════════════════════════════════════════════════════
# HAMPSTEAD RENOVATIONS - 3-AGENT AI SYSTEM
# Makefile for common operations
# ═══════════════════════════════════════════════════════════════════════════════

.PHONY: help dev prod up down restart logs clean test lint build deploy backup

# Default target
.DEFAULT_GOAL := help

# Colors for output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# ─────────────────────────────────────────────────────────────────────────────────
# HELP
# ─────────────────────────────────────────────────────────────────────────────────
help: ## Show this help message
	@echo ""
	@echo "$(CYAN)╔═══════════════════════════════════════════════════════════════════╗$(RESET)"
	@echo "$(CYAN)║     HAMPSTEAD RENOVATIONS - 3-AGENT AI SYSTEM                     ║$(RESET)"
	@echo "$(CYAN)╚═══════════════════════════════════════════════════════════════════╝$(RESET)"
	@echo ""
	@echo "$(GREEN)Available commands:$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_-]+:.*?##/ { printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────────
# DEVELOPMENT
# ─────────────────────────────────────────────────────────────────────────────────
dev: ## Start development environment with hot reload
	@echo "$(GREEN)Starting development environment...$(RESET)"
	docker-compose --profile development up -d
	@echo "$(GREEN)Development environment started!$(RESET)"
	@echo "  n8n:          http://localhost:5678"
	@echo "  Quote Builder: http://localhost:8000"
	@echo "  Web Form:      http://localhost:3000"
	@echo "  Traefik:       http://localhost:8080"

dev-logs: ## Follow development logs
	docker-compose --profile development logs -f

# ─────────────────────────────────────────────────────────────────────────────────
# PRODUCTION
# ─────────────────────────────────────────────────────────────────────────────────
prod: ## Start production environment
	@echo "$(GREEN)Starting production environment...$(RESET)"
	docker-compose --profile production up -d
	@echo "$(GREEN)Production environment started!$(RESET)"

prod-logs: ## Follow production logs
	docker-compose --profile production logs -f

# ─────────────────────────────────────────────────────────────────────────────────
# DOCKER OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────────
up: ## Start all services
	@echo "$(GREEN)Starting all services...$(RESET)"
	docker-compose up -d

down: ## Stop all services
	@echo "$(YELLOW)Stopping all services...$(RESET)"
	docker-compose down

restart: ## Restart all services
	@echo "$(YELLOW)Restarting all services...$(RESET)"
	docker-compose restart

logs: ## Follow logs for all services
	docker-compose logs -f

logs-n8n: ## Follow n8n logs
	docker-compose logs -f n8n n8n-worker

logs-quote: ## Follow quote builder logs
	docker-compose logs -f quote-builder

status: ## Show status of all services
	@echo "$(CYAN)Service Status:$(RESET)"
	docker-compose ps

# ─────────────────────────────────────────────────────────────────────────────────
# BUILD
# ─────────────────────────────────────────────────────────────────────────────────
build: ## Build all Docker images
	@echo "$(GREEN)Building all Docker images...$(RESET)"
	docker-compose build --no-cache

build-quote: ## Build quote builder image
	@echo "$(GREEN)Building quote builder...$(RESET)"
	docker-compose build quote-builder

build-web: ## Build web form image
	@echo "$(GREEN)Building web form...$(RESET)"
	docker-compose build web-form

# ─────────────────────────────────────────────────────────────────────────────────
# TESTING
# ─────────────────────────────────────────────────────────────────────────────────
test: ## Run all tests
	@echo "$(GREEN)Running all tests...$(RESET)"
	cd agent-3-office-ops/quote-builder && python -m pytest tests/ -v
	cd web-form && npm test

test-quote: ## Run quote builder tests
	@echo "$(GREEN)Running quote builder tests...$(RESET)"
	cd agent-3-office-ops/quote-builder && python -m pytest tests/ -v --cov=. --cov-report=html

test-web: ## Run web form tests
	@echo "$(GREEN)Running web form tests...$(RESET)"
	cd web-form && npm test

# ─────────────────────────────────────────────────────────────────────────────────
# LINTING & FORMATTING
# ─────────────────────────────────────────────────────────────────────────────────
lint: ## Run linters on all code
	@echo "$(GREEN)Running linters...$(RESET)"
	cd agent-3-office-ops/quote-builder && python -m ruff check .
	cd web-form && npm run lint

lint-fix: ## Fix linting issues
	@echo "$(GREEN)Fixing linting issues...$(RESET)"
	cd agent-3-office-ops/quote-builder && python -m ruff check . --fix
	cd web-form && npm run lint:fix

format: ## Format all code
	@echo "$(GREEN)Formatting code...$(RESET)"
	cd agent-3-office-ops/quote-builder && python -m black .
	cd web-form && npm run format

# ─────────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────────
db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U hampstead -d hampstead

db-migrate: ## Run database migrations
	@echo "$(GREEN)Running database migrations...$(RESET)"
	docker-compose exec postgres psql -U hampstead -d hampstead -f /docker-entrypoint-initdb.d/001_schema.sql

db-seed: ## Seed database with test data
	@echo "$(GREEN)Seeding database...$(RESET)"
	docker-compose exec postgres psql -U hampstead -d hampstead -f /docker-entrypoint-initdb.d/002_seed.sql

db-backup: ## Create database backup
	@echo "$(GREEN)Creating database backup...$(RESET)"
	docker-compose exec postgres pg_dump -U hampstead hampstead > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Backup created!$(RESET)"

db-restore: ## Restore database from backup (BACKUP_FILE required)
	@if [ -z "$(BACKUP_FILE)" ]; then echo "$(RED)Error: BACKUP_FILE not specified$(RESET)"; exit 1; fi
	@echo "$(YELLOW)Restoring database from $(BACKUP_FILE)...$(RESET)"
	docker-compose exec -T postgres psql -U hampstead hampstead < $(BACKUP_FILE)
	@echo "$(GREEN)Database restored!$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────────
# REDIS
# ─────────────────────────────────────────────────────────────────────────────────
redis-cli: ## Open Redis CLI
	docker-compose exec redis redis-cli

redis-flush: ## Flush Redis cache
	@echo "$(YELLOW)Flushing Redis cache...$(RESET)"
	docker-compose exec redis redis-cli FLUSHALL
	@echo "$(GREEN)Redis cache flushed!$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────────
# N8N WORKFLOWS
# ─────────────────────────────────────────────────────────────────────────────────
n8n-export: ## Export all n8n workflows
	@echo "$(GREEN)Exporting n8n workflows...$(RESET)"
	./infrastructure/scripts/export-workflows.sh

n8n-import: ## Import all n8n workflows
	@echo "$(GREEN)Importing n8n workflows...$(RESET)"
	./infrastructure/scripts/import-workflows.sh

# ─────────────────────────────────────────────────────────────────────────────────
# MONITORING
# ─────────────────────────────────────────────────────────────────────────────────
monitoring-up: ## Start monitoring stack (Prometheus + Grafana)
	@echo "$(GREEN)Starting monitoring stack...$(RESET)"
	docker-compose --profile monitoring up -d prometheus grafana
	@echo "$(GREEN)Monitoring started!$(RESET)"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana:    http://localhost:3001 (admin/admin)"

monitoring-down: ## Stop monitoring stack
	docker-compose --profile monitoring down

# ─────────────────────────────────────────────────────────────────────────────────
# CLEANUP
# ─────────────────────────────────────────────────────────────────────────────────
clean: ## Remove all containers, volumes, and images
	@echo "$(RED)WARNING: This will remove all data!$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	docker-compose down -v --rmi all --remove-orphans
	@echo "$(GREEN)Cleanup complete!$(RESET)"

clean-volumes: ## Remove all Docker volumes
	@echo "$(RED)WARNING: This will remove all persistent data!$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	docker-compose down -v
	@echo "$(GREEN)Volumes removed!$(RESET)"

prune: ## Clean up unused Docker resources
	@echo "$(YELLOW)Pruning unused Docker resources...$(RESET)"
	docker system prune -af
	@echo "$(GREEN)Prune complete!$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────────
# DEPLOYMENT
# ─────────────────────────────────────────────────────────────────────────────────
deploy-staging: ## Deploy to staging environment
	@echo "$(GREEN)Deploying to staging...$(RESET)"
	./infrastructure/scripts/deploy.sh staging

deploy-prod: ## Deploy to production environment
	@echo "$(GREEN)Deploying to production...$(RESET)"
	./infrastructure/scripts/deploy.sh production

# ─────────────────────────────────────────────────────────────────────────────────
# HUBSPOT SETUP
# ─────────────────────────────────────────────────────────────────────────────────
hubspot-setup: ## Set up HubSpot custom properties and pipelines
	@echo "$(GREEN)Setting up HubSpot...$(RESET)"
	./infrastructure/scripts/setup-hubspot.sh

# ─────────────────────────────────────────────────────────────────────────────────
# SECURITY
# ─────────────────────────────────────────────────────────────────────────────────
security-scan: ## Run security scan with Snyk
	@echo "$(GREEN)Running security scan...$(RESET)"
	snyk test --all-projects

security-scan-docker: ## Scan Docker images for vulnerabilities
	@echo "$(GREEN)Scanning Docker images...$(RESET)"
	snyk container test hampstead-quote-builder:latest

# ─────────────────────────────────────────────────────────────────────────────────
# HEALTH CHECKS
# ─────────────────────────────────────────────────────────────────────────────────
health: ## Check health of all services
	@echo "$(CYAN)Checking service health...$(RESET)"
	@echo ""
	@echo "n8n:            $$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5678/healthz || echo 'DOWN')"
	@echo "Quote Builder:  $$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health || echo 'DOWN')"
	@echo "PostgreSQL:     $$(docker-compose exec -T postgres pg_isready -U hampstead > /dev/null 2>&1 && echo 'UP' || echo 'DOWN')"
	@echo "Redis:          $$(docker-compose exec -T redis redis-cli ping 2>/dev/null || echo 'DOWN')"
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────────
# SHELL ACCESS
# ─────────────────────────────────────────────────────────────────────────────────
shell-n8n: ## Open shell in n8n container
	docker-compose exec n8n /bin/sh

shell-quote: ## Open shell in quote builder container
	docker-compose exec quote-builder /bin/bash

shell-postgres: ## Open shell in postgres container
	docker-compose exec postgres /bin/sh

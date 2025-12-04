#!/bin/bash
# =============================================================================
# Hampstead Renovations - Backup Script
# =============================================================================
# Creates backups of database, n8n data, and configuration
# Usage: ./backup.sh [backup-dir]
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="${1:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$TIMESTAMP"

# Docker Compose file
COMPOSE_FILE="docker-compose.yml"

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

create_backup_directory() {
    log_info "Creating backup directory: $BACKUP_PATH"
    mkdir -p "$BACKUP_PATH"
    mkdir -p "$BACKUP_PATH/database"
    mkdir -p "$BACKUP_PATH/n8n"
    mkdir -p "$BACKUP_PATH/config"
    log_success "Backup directories created"
}

backup_database() {
    log_info "Backing up PostgreSQL database..."
    
    # Check if postgres container is running
    if ! docker compose -f "$COMPOSE_FILE" ps postgres | grep -q "running"; then
        log_warning "PostgreSQL container is not running. Skipping database backup."
        return
    fi
    
    # Create database dump
    docker compose -f "$COMPOSE_FILE" exec -T postgres \
        pg_dump -U hampstead -d hampstead_renovations \
        --format=custom \
        --file=/tmp/backup.dump
    
    # Copy dump from container
    docker compose -f "$COMPOSE_FILE" cp postgres:/tmp/backup.dump "$BACKUP_PATH/database/hampstead_renovations.dump"
    
    # Also create SQL format for readability
    docker compose -f "$COMPOSE_FILE" exec -T postgres \
        pg_dump -U hampstead -d hampstead_renovations \
        --format=plain > "$BACKUP_PATH/database/hampstead_renovations.sql"
    
    # Create schema-only backup
    docker compose -f "$COMPOSE_FILE" exec -T postgres \
        pg_dump -U hampstead -d hampstead_renovations \
        --schema-only > "$BACKUP_PATH/database/schema.sql"
    
    log_success "Database backup completed"
}

backup_n8n_data() {
    log_info "Backing up n8n data..."
    
    # Check if n8n container is running
    if ! docker compose -f "$COMPOSE_FILE" ps n8n | grep -q "running"; then
        log_warning "n8n container is not running. Attempting to backup from volume..."
    fi
    
    # Backup n8n SQLite database if it exists
    if docker compose -f "$COMPOSE_FILE" exec -T n8n test -f /home/node/.n8n/database.sqlite 2>/dev/null; then
        docker compose -f "$COMPOSE_FILE" cp n8n:/home/node/.n8n/database.sqlite "$BACKUP_PATH/n8n/"
        log_success "n8n database backed up"
    fi
    
    # Export workflows using the export script
    if [[ -x "./infrastructure/scripts/export-workflows.sh" ]]; then
        ./infrastructure/scripts/export-workflows.sh "$BACKUP_PATH/n8n/workflows"
    else
        log_warning "export-workflows.sh not found. Skipping workflow export."
    fi
    
    log_success "n8n backup completed"
}

backup_redis_data() {
    log_info "Backing up Redis data..."
    
    # Check if redis container is running
    if ! docker compose -f "$COMPOSE_FILE" ps redis | grep -q "running"; then
        log_warning "Redis container is not running. Skipping Redis backup."
        return
    fi
    
    # Trigger RDB save
    docker compose -f "$COMPOSE_FILE" exec -T redis redis-cli BGSAVE
    
    # Wait for save to complete
    sleep 2
    
    # Copy RDB file
    if docker compose -f "$COMPOSE_FILE" exec -T redis test -f /data/dump.rdb 2>/dev/null; then
        docker compose -f "$COMPOSE_FILE" cp redis:/data/dump.rdb "$BACKUP_PATH/redis/"
        log_success "Redis backup completed"
    else
        log_warning "Redis RDB file not found"
    fi
}

backup_configuration() {
    log_info "Backing up configuration files..."
    
    # Backup docker-compose and env
    cp docker-compose.yml "$BACKUP_PATH/config/" 2>/dev/null || true
    cp .env "$BACKUP_PATH/config/env.backup" 2>/dev/null || true
    cp .env.template "$BACKUP_PATH/config/" 2>/dev/null || true
    
    # Backup infrastructure configs
    if [[ -d "infrastructure" ]]; then
        cp -r infrastructure "$BACKUP_PATH/config/"
    fi
    
    # Backup pricing and templates
    if [[ -d "agent-3-office-ops/pricing" ]]; then
        cp -r agent-3-office-ops/pricing "$BACKUP_PATH/config/"
    fi
    
    log_success "Configuration backup completed"
}

create_backup_manifest() {
    log_info "Creating backup manifest..."
    
    cat > "$BACKUP_PATH/manifest.json" << EOF
{
    "backup_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "backup_version": "1.0.0",
    "system": "Hampstead Renovations 3-Agent AI System",
    "contents": {
        "database": $(test -f "$BACKUP_PATH/database/hampstead_renovations.dump" && echo "true" || echo "false"),
        "n8n": $(test -d "$BACKUP_PATH/n8n" && echo "true" || echo "false"),
        "redis": $(test -f "$BACKUP_PATH/redis/dump.rdb" 2>/dev/null && echo "true" || echo "false"),
        "configuration": true
    },
    "files": $(find "$BACKUP_PATH" -type f -exec basename {} \; | jq -R -s 'split("\n") | map(select(length > 0))')
}
EOF
    
    log_success "Manifest created"
}

compress_backup() {
    log_info "Compressing backup..."
    
    local archive_name="hampstead-backup-$TIMESTAMP.tar.gz"
    
    cd "$BACKUP_DIR"
    tar -czf "$archive_name" "$TIMESTAMP"
    
    # Calculate size
    local size
    size=$(du -h "$archive_name" | cut -f1)
    
    log_success "Backup compressed: $archive_name ($size)"
    
    # Optionally remove uncompressed directory
    # rm -rf "$TIMESTAMP"
    
    cd - > /dev/null
}

cleanup_old_backups() {
    log_info "Cleaning up old backups (keeping last 7)..."
    
    cd "$BACKUP_DIR"
    
    # Keep only the last 7 backup archives
    ls -t hampstead-backup-*.tar.gz 2>/dev/null | tail -n +8 | xargs -r rm -f
    
    log_success "Cleanup completed"
    
    cd - > /dev/null
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo ""
    echo "=============================================="
    echo "Hampstead Renovations - Backup Script"
    echo "=============================================="
    echo ""
    
    create_backup_directory
    backup_database
    backup_n8n_data
    backup_redis_data
    backup_configuration
    create_backup_manifest
    compress_backup
    cleanup_old_backups
    
    echo ""
    echo "=============================================="
    echo -e "${GREEN}Backup Complete!${NC}"
    echo "=============================================="
    echo ""
    echo "Backup location: $BACKUP_DIR/hampstead-backup-$TIMESTAMP.tar.gz"
    echo ""
    echo "To restore from this backup:"
    echo "  ./restore.sh $BACKUP_DIR/hampstead-backup-$TIMESTAMP.tar.gz"
    echo ""
}

# Run main function
main

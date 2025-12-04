#!/bin/bash
# =============================================================================
# Hampstead Renovations - n8n Workflow Export Script
# =============================================================================
# Exports all n8n workflows to JSON files for version control
# Usage: ./export-workflows.sh [output-dir]
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
N8N_HOST="${N8N_HOST:-http://localhost:5678}"
N8N_API_KEY="${N8N_API_KEY:-}"
OUTPUT_DIR="${1:-./exported-workflows}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

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
    
    # Check jq
    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed. Please install it with: brew install jq (Mac) or apt-get install jq (Linux)"
        exit 1
    fi
    
    # Check curl
    if ! command -v curl &> /dev/null; then
        log_error "curl is not installed"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

check_n8n_connection() {
    log_info "Checking n8n connection at $N8N_HOST..."
    
    local health_check
    if [[ -n "$N8N_API_KEY" ]]; then
        health_check=$(curl -sf -H "X-N8N-API-KEY: $N8N_API_KEY" "$N8N_HOST/healthz" 2>/dev/null || echo "failed")
    else
        health_check=$(curl -sf "$N8N_HOST/healthz" 2>/dev/null || echo "failed")
    fi
    
    if [[ "$health_check" == "failed" ]]; then
        log_error "Cannot connect to n8n at $N8N_HOST"
        log_info "Make sure n8n is running and accessible"
        exit 1
    fi
    
    log_success "n8n connection successful"
}

create_output_directory() {
    local dir="$OUTPUT_DIR/$TIMESTAMP"
    mkdir -p "$dir"
    echo "$dir"
}

export_workflows() {
    local output_dir="$1"
    
    log_info "Fetching workflow list..."
    
    local auth_header=""
    if [[ -n "$N8N_API_KEY" ]]; then
        auth_header="-H X-N8N-API-KEY: $N8N_API_KEY"
    fi
    
    # Get all workflows
    local workflows
    workflows=$(curl -sf $auth_header "$N8N_HOST/api/v1/workflows" 2>/dev/null || echo '{"data":[]}')
    
    local count
    count=$(echo "$workflows" | jq '.data | length')
    
    if [[ "$count" -eq 0 ]]; then
        log_warning "No workflows found to export"
        return
    fi
    
    log_info "Found $count workflows to export"
    
    # Export each workflow
    local exported=0
    while IFS= read -r workflow; do
        local id=$(echo "$workflow" | jq -r '.id')
        local name=$(echo "$workflow" | jq -r '.name')
        local active=$(echo "$workflow" | jq -r '.active')
        
        # Sanitize filename
        local filename=$(echo "$name" | sed 's/[^a-zA-Z0-9._-]/-/g' | tr '[:upper:]' '[:lower:]')
        filename="${filename}.json"
        
        log_info "Exporting: $name (ID: $id, Active: $active)"
        
        # Get full workflow details
        local workflow_data
        workflow_data=$(curl -sf $auth_header "$N8N_HOST/api/v1/workflows/$id" 2>/dev/null)
        
        if [[ -n "$workflow_data" ]]; then
            echo "$workflow_data" | jq '.' > "$output_dir/$filename"
            exported=$((exported + 1))
            log_success "  Saved to: $filename"
        else
            log_warning "  Failed to export workflow $id"
        fi
        
    done < <(echo "$workflows" | jq -c '.data[]')
    
    log_success "Exported $exported workflows to $output_dir"
}

export_credentials() {
    local output_dir="$1"
    
    log_info "Exporting credentials (encrypted)..."
    
    local auth_header=""
    if [[ -n "$N8N_API_KEY" ]]; then
        auth_header="-H X-N8N-API-KEY: $N8N_API_KEY"
    fi
    
    # Get all credentials
    local credentials
    credentials=$(curl -sf $auth_header "$N8N_HOST/api/v1/credentials" 2>/dev/null || echo '{"data":[]}')
    
    local count
    count=$(echo "$credentials" | jq '.data | length')
    
    if [[ "$count" -eq 0 ]]; then
        log_warning "No credentials found"
        return
    fi
    
    log_info "Found $count credentials"
    
    # Save credential metadata (not the actual secrets)
    echo "$credentials" | jq '{
        credentials: [.data[] | {
            id: .id,
            name: .name,
            type: .type,
            createdAt: .createdAt,
            updatedAt: .updatedAt
        }],
        exported_at: now | todate,
        note: "This file contains credential metadata only. Actual secrets are not exported for security."
    }' > "$output_dir/credentials-metadata.json"
    
    log_success "Credential metadata saved to credentials-metadata.json"
    log_warning "Note: Actual credential secrets are NOT exported for security reasons"
}

create_manifest() {
    local output_dir="$1"
    
    log_info "Creating export manifest..."
    
    local workflow_count
    workflow_count=$(find "$output_dir" -name "*.json" -not -name "credentials-*" -not -name "manifest.json" | wc -l | tr -d ' ')
    
    cat > "$output_dir/manifest.json" << EOF
{
    "export_timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "n8n_host": "$N8N_HOST",
    "workflow_count": $workflow_count,
    "export_version": "1.0.0",
    "system": "Hampstead Renovations 3-Agent AI System",
    "files": $(find "$output_dir" -name "*.json" -exec basename {} \; | jq -R -s 'split("\n") | map(select(length > 0))')
}
EOF
    
    log_success "Manifest created"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo ""
    echo "=============================================="
    echo "n8n Workflow Export"
    echo "=============================================="
    echo ""
    
    check_prerequisites
    check_n8n_connection
    
    local export_dir
    export_dir=$(create_output_directory)
    
    log_info "Export directory: $export_dir"
    
    export_workflows "$export_dir"
    export_credentials "$export_dir"
    create_manifest "$export_dir"
    
    echo ""
    echo "=============================================="
    echo -e "${GREEN}Export Complete!${NC}"
    echo "=============================================="
    echo ""
    echo "Exported to: $export_dir"
    echo ""
    echo "To import these workflows on another n8n instance:"
    echo "  ./import-workflows.sh $export_dir"
    echo ""
}

# Run main function
main

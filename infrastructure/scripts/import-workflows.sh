#!/bin/bash
# =============================================================================
# Hampstead Renovations - n8n Workflow Import Script
# =============================================================================
# Imports n8n workflows from JSON files
# Usage: ./import-workflows.sh [input-dir] [--activate]
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
INPUT_DIR="${1:-./agent-1-lead-intake/n8n-workflows}"
ACTIVATE_WORKFLOWS=false

# Parse additional arguments
shift || true
for arg in "$@"; do
    case $arg in
        --activate)
            ACTIVATE_WORKFLOWS=true
            ;;
        --help)
            echo "Usage: ./import-workflows.sh [input-dir] [--activate]"
            echo ""
            echo "Arguments:"
            echo "  input-dir   Directory containing workflow JSON files"
            echo ""
            echo "Options:"
            echo "  --activate  Activate workflows after import"
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
    
    # Check input directory
    if [[ ! -d "$INPUT_DIR" ]]; then
        log_error "Input directory not found: $INPUT_DIR"
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

import_workflow() {
    local file="$1"
    local filename=$(basename "$file")
    
    log_info "Importing: $filename"
    
    # Read workflow data
    local workflow_data
    workflow_data=$(cat "$file")
    
    # Extract workflow name
    local workflow_name
    workflow_name=$(echo "$workflow_data" | jq -r '.name // "Unknown"')
    
    # Check if workflow already exists
    local auth_header=""
    if [[ -n "$N8N_API_KEY" ]]; then
        auth_header="X-N8N-API-KEY: $N8N_API_KEY"
    fi
    
    local existing_workflows
    existing_workflows=$(curl -sf -H "$auth_header" "$N8N_HOST/api/v1/workflows" 2>/dev/null || echo '{"data":[]}')
    
    local existing_id
    existing_id=$(echo "$existing_workflows" | jq -r --arg name "$workflow_name" '.data[] | select(.name == $name) | .id // empty')
    
    if [[ -n "$existing_id" ]]; then
        log_warning "  Workflow '$workflow_name' already exists (ID: $existing_id)"
        log_info "  Updating existing workflow..."
        
        # Update existing workflow
        local update_data
        update_data=$(echo "$workflow_data" | jq 'del(.id) | del(.createdAt) | del(.updatedAt)')
        
        local response
        response=$(curl -sf -X PUT \
            -H "Content-Type: application/json" \
            -H "$auth_header" \
            -d "$update_data" \
            "$N8N_HOST/api/v1/workflows/$existing_id" 2>/dev/null)
        
        if [[ -n "$response" ]]; then
            log_success "  Updated workflow: $workflow_name"
        else
            log_error "  Failed to update workflow: $workflow_name"
            return 1
        fi
    else
        # Create new workflow
        local import_data
        import_data=$(echo "$workflow_data" | jq 'del(.id) | del(.createdAt) | del(.updatedAt)')
        
        local response
        response=$(curl -sf -X POST \
            -H "Content-Type: application/json" \
            -H "$auth_header" \
            -d "$import_data" \
            "$N8N_HOST/api/v1/workflows" 2>/dev/null)
        
        if [[ -n "$response" ]]; then
            local new_id
            new_id=$(echo "$response" | jq -r '.id')
            log_success "  Created workflow: $workflow_name (ID: $new_id)"
            
            # Activate if requested
            if [[ "$ACTIVATE_WORKFLOWS" == true ]]; then
                curl -sf -X PATCH \
                    -H "Content-Type: application/json" \
                    -H "$auth_header" \
                    -d '{"active": true}' \
                    "$N8N_HOST/api/v1/workflows/$new_id" > /dev/null 2>&1
                log_info "  Workflow activated"
            fi
        else
            log_error "  Failed to create workflow: $workflow_name"
            return 1
        fi
    fi
}

import_all_workflows() {
    log_info "Searching for workflow files in $INPUT_DIR..."
    
    local workflow_files
    workflow_files=$(find "$INPUT_DIR" -name "*.json" -type f | sort)
    
    local count=0
    local success=0
    local failed=0
    
    while IFS= read -r file; do
        # Skip manifest and credential files
        if [[ $(basename "$file") == "manifest.json" ]] || [[ $(basename "$file") == credentials-* ]]; then
            continue
        fi
        
        count=$((count + 1))
        
        if import_workflow "$file"; then
            success=$((success + 1))
        else
            failed=$((failed + 1))
        fi
        
        # Small delay between imports
        sleep 0.5
        
    done <<< "$workflow_files"
    
    echo ""
    log_info "Import Summary:"
    log_info "  Total files processed: $count"
    log_success "  Successfully imported: $success"
    
    if [[ $failed -gt 0 ]]; then
        log_error "  Failed imports: $failed"
    fi
}

import_project_workflows() {
    log_info "Importing all project workflows..."
    
    local workflow_dirs=(
        "agent-1-lead-intake/n8n-workflows"
        "agent-2-sales-crm/n8n-workflows"
        "agent-3-office-ops/n8n-workflows"
    )
    
    local base_dir
    base_dir=$(dirname "$(dirname "$(realpath "$0")")")
    
    for dir in "${workflow_dirs[@]}"; do
        local full_path="$base_dir/../$dir"
        
        if [[ -d "$full_path" ]]; then
            log_info "Processing: $dir"
            INPUT_DIR="$full_path"
            import_all_workflows
        else
            log_warning "Directory not found: $dir"
        fi
    done
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo ""
    echo "=============================================="
    echo "n8n Workflow Import"
    echo "=============================================="
    echo ""
    
    check_prerequisites
    check_n8n_connection
    
    log_info "Input directory: $INPUT_DIR"
    log_info "Activate workflows: $ACTIVATE_WORKFLOWS"
    echo ""
    
    # Check if importing from specific directory or all project workflows
    if [[ -d "$INPUT_DIR" ]]; then
        import_all_workflows
    else
        log_error "Directory not found: $INPUT_DIR"
        exit 1
    fi
    
    echo ""
    echo "=============================================="
    echo -e "${GREEN}Import Complete!${NC}"
    echo "=============================================="
    echo ""
    echo "View imported workflows at: $N8N_HOST"
    echo ""
    echo "Note: You may need to configure credentials for each workflow"
    echo ""
}

# Run main function
main

#!/bin/bash
# =============================================================================
# PreciAgro Emergency Rollback Script
# =============================================================================
# Usage: ./rollback.sh <environment> <engine> [version]
#
# Examples:
#   ./rollback.sh staging crop-intelligence           # Rollback to previous
#   ./rollback.sh production all                      # Rollback all engines
#   ./rollback.sh production geo-context v2.0.5      # Rollback to specific version
# =============================================================================

set -euo pipefail

# Configuration
REGISTRY="${REGISTRY:-ghcr.io/preciagro}"
NAMESPACE_PREFIX="preciagro"

# Parse arguments
ENVIRONMENT="${1:-}"
ENGINE="${2:-}"
VERSION="${3:-previous}"

if [[ -z "$ENVIRONMENT" ]] || [[ -z "$ENGINE" ]]; then
    echo "Usage: $0 <environment> <engine> [version]"
    echo ""
    echo "Environments: staging, production"
    echo "Engines: crop-intelligence, data-integration, geo-context, image-analysis, all"
    echo "Version: previous (default), or specific version tag"
    exit 1
fi

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    echo "Error: Invalid environment. Must be 'staging' or 'production'"
    exit 1
fi

NAMESPACE="${NAMESPACE_PREFIX}-${ENVIRONMENT}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to rollback a single engine
rollback_engine() {
    local engine_name="$1"
    local target_version="$2"
    
    log_info "Rolling back $engine_name in $NAMESPACE..."
    
    if [[ "$target_version" == "previous" ]]; then
        # Use kubectl rollout undo
        log_info "Rolling back to previous revision..."
        kubectl rollout undo deployment/"$engine_name" -n "$NAMESPACE" || {
            log_error "Failed to rollback $engine_name"
            return 1
        }
    else
        # Set specific image version
        local image="${REGISTRY}/preciagro-${engine_name}:${target_version}"
        log_info "Rolling back to version: $target_version"
        kubectl set image deployment/"$engine_name" \
            "$engine_name=$image" \
            -n "$NAMESPACE" || {
            log_error "Failed to set image for $engine_name"
            return 1
        }
    fi
    
    # Wait for rollout
    log_info "Waiting for rollout to complete..."
    kubectl rollout status deployment/"$engine_name" -n "$NAMESPACE" --timeout=300s || {
        log_error "Rollout failed for $engine_name"
        return 1
    }
    
    log_info "Rollback of $engine_name completed successfully"
}

# Function to verify rollback
verify_rollback() {
    local engine_name="$1"
    
    log_info "Verifying $engine_name health..."
    
    # Wait for pods to be ready
    kubectl wait --for=condition=Ready pods \
        -l app="$engine_name" \
        -n "$NAMESPACE" \
        --timeout=120s || {
        log_warn "Some pods may not be ready"
    }
    
    # Check deployment status
    local ready=$(kubectl get deployment "$engine_name" -n "$NAMESPACE" \
        -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
    local desired=$(kubectl get deployment "$engine_name" -n "$NAMESPACE" \
        -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "1")
    
    if [[ "$ready" == "$desired" ]]; then
        log_info "$engine_name: $ready/$desired replicas ready"
        return 0
    else
        log_error "$engine_name: Only $ready/$desired replicas ready"
        return 1
    fi
}

# Create rollback record for audit
create_audit_record() {
    local engine_name="$1"
    local version="$2"
    
    cat << EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "action": "rollback",
    "environment": "$ENVIRONMENT",
    "engine": "$engine_name",
    "target_version": "$version",
    "actor": "$(whoami)",
    "hostname": "$(hostname)"
}
EOF
}

# Main execution
main() {
    log_info "=== PreciAgro Rollback ==="
    log_info "Environment: $ENVIRONMENT"
    log_info "Engine: $ENGINE"
    log_info "Version: $VERSION"
    echo ""
    
    # Confirmation for production
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log_warn "⚠️  You are about to rollback PRODUCTION!"
        read -p "Type 'ROLLBACK' to confirm: " confirmation
        if [[ "$confirmation" != "ROLLBACK" ]]; then
            log_error "Rollback cancelled"
            exit 1
        fi
    fi
    
    # Determine engines to rollback
    local engines=()
    if [[ "$ENGINE" == "all" ]]; then
        engines=("crop-intelligence" "data-integration" "geo-context" "temporal-logic" "image-analysis")
    else
        engines=("$ENGINE")
    fi
    
    # Execute rollbacks
    local failed_engines=()
    for eng in "${engines[@]}"; do
        if rollback_engine "$eng" "$VERSION"; then
            if verify_rollback "$eng"; then
                log_info "✅ $eng rollback verified"
            else
                log_warn "⚠️ $eng rollback completed but verification failed"
            fi
        else
            failed_engines+=("$eng")
            log_error "❌ $eng rollback failed"
        fi
        
        # Create audit record
        create_audit_record "$eng" "$VERSION" >> rollback-audit.log
    done
    
    echo ""
    log_info "=== Rollback Summary ==="
    log_info "Total engines: ${#engines[@]}"
    log_info "Failed engines: ${#failed_engines[@]}"
    
    if [[ ${#failed_engines[@]} -gt 0 ]]; then
        log_error "Failed: ${failed_engines[*]}"
        exit 1
    fi
    
    log_info "✅ All rollbacks completed successfully"
}

main

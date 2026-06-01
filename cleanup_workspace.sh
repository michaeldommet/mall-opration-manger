#!/bin/bash
# ==============================================================================
# Mall Operations Manager — Local Workspace Cleanup Engine
# ==============================================================================
# Cleans Python cache, temp files, OS metadata, and optional deep build items.
# ==============================================================================

set -euo pipefail

# ANSI color codes for premium terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

DEEP_CLEAN=false

show_help() {
    cat << EOF
Usage: ./cleanup_workspace.sh [OPTIONS]

Options:
  -d, --deep     Deep clean (removes .venv, node_modules, and compiled .next builds)
  -h, --help     Show this help message and exit
EOF
}

# Parse command line options
while [[ $# -gt 0 ]]; do
    case "$1" in
        -d|--deep)
            DEEP_CLEAN=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

log_info() {
    echo -e "${BLUE}${BOLD}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}${BOLD}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}${BOLD}[WARNING]${NC} $1"
}

echo -e "${BLUE}${BOLD}"
echo "=========================================================================="
echo "          LOCAL WORKSPACE CLEANUP ENGINE — MALL OPERATIONS BRAIN          "
echo "=========================================================================="
echo -e "${NC}"

# 1. Clear Python Caches
log_info "Removing Python compiled bytecode and pycache folders..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type f -name "*.pyd" -delete 2>/dev/null || true

# 2. Clear Testing Caches
log_info "Removing test caches and reports..."
rm -rf .pytest_cache .coverage htmlcov .pytest_cache/ tests/.pytest_cache/ 2>/dev/null || true

# 3. Clear OS Metadata Files
log_info "Removing OS metadata files (.DS_Store)..."
find . -type f -name ".DS_Store" -delete 2>/dev/null || true

# 4. Clear Stray Temp Files in root
log_info "Removing local temporary development scripts..."
rm -f list_re.py 2>/dev/null || true

# 5. Deep Clean (optional)
if [ "$DEEP_CLEAN" = true ]; then
    log_warn "DEEP CLEAN triggered! Deleting virtual environments, node modules, and builds..."
    
    log_info "Removing Next.js compilation cache (.next) in frontend..."
    rm -rf frontend/.next 2>/dev/null || true
    
    log_info "Removing local virtual environment (.venv)..."
    rm -rf .venv 2>/dev/null || true
    
    log_info "Removing frontend dependencies (node_modules)..."
    rm -rf frontend/node_modules 2>/dev/null || true
    
    log_success "Deep cleanup completed successfully!"
else
    log_success "Standard workspace cleanup completed successfully!"
    echo -e "Run ${BOLD}./cleanup_workspace.sh --deep${NC} if you wish to wipe dependencies and build caches."
fi
echo ""

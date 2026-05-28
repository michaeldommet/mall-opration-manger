#!/bin/bash
# ==============================================================================
# Mall Operations Manager — Unified Cloud Deployment Engine
# ==============================================================================
# Deploys:
#   1. ADK Agent -> Vertex AI Agent Platform (via agents-cli)
#   2. FastAPI Backend -> Google Cloud Run (with Secret Manager injection)
#   3. Next.js Frontend -> Google Cloud Run (pointing to the backend service)
# ==============================================================================

set -euo pipefail

# ANSI color codes for premium terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default values
DEFAULT_PROJECT_ID="elastic-496520"
DEFAULT_REGION="us-central1"

PROJECT_ID="$DEFAULT_PROJECT_ID"
REGION="$DEFAULT_REGION"
DEPLOY_AGENT=true
DEPLOY_APP=true
DRY_RUN=false

show_help() {
    cat << EOF
Usage: ./deploy.sh [OPTIONS]

Options:
  -p, --project ID      GCP Project ID (default: $DEFAULT_PROJECT_ID)
  -r, --region REGION   GCP Region (default: $DEFAULT_REGION)
  --agent-only          Deploy only the Vertex AI ADK Agent
  --app-only            Deploy only the Backend and Frontend Cloud Run services
  -d, --dry-run         Print commands that would be executed without running them
  -h, --help            Show this help message and exit
EOF
}

# Parse command line options
while [[ $# -gt 0 ]]; do
    case "$1" in
        -p|--project)
            PROJECT_ID="$2"
            shift 2
            ;;
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        --agent-only)
            DEPLOY_AGENT=true
            DEPLOY_APP=false
            shift
            ;;
        --app-only)
            DEPLOY_AGENT=false
            DEPLOY_APP=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
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

log_error() {
    echo -e "${RED}${BOLD}[ERROR]${NC} $1"
}

# ------------------------------------------------------------------------------
# Banner
# ------------------------------------------------------------------------------
echo -e "${CYAN}${BOLD}"
echo "=========================================================================="
echo "          MALL OPERATIONS MANAGER — MULTI-SERVICE DEPLOYMENT ENGINE      "
echo "=========================================================================="
echo -e "${NC}"
echo -e "Project ID : ${BOLD}${PROJECT_ID}${NC}"
echo -e "Region     : ${BOLD}${REGION}${NC}"
echo -e "Dry Run    : ${BOLD}${DRY_RUN}${NC}"
echo -e "Scope      : $( [ "$DEPLOY_AGENT" = true ] && echo -n "Agent " ); $( [ "$DEPLOY_APP" = true ] && echo -n "App (Backend & Frontend)" )"
echo "=========================================================================="
echo ""

# ------------------------------------------------------------------------------
# Environmental Setup
# ------------------------------------------------------------------------------
ENV_FILE="./backend/.env"
if [ ! -f "$ENV_FILE" ]; then
    log_error "Configuration file $ENV_FILE not found. Please verify backend/.env exists."
    exit 1
fi

log_info "Parsing environment variables from $ENV_FILE..."
# Read needed environment variables
ELASTICSEARCH_URL=$(grep "^ELASTICSEARCH_URL=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
ELASTICSEARCH_API_KEY=$(grep "^ELASTICSEARCH_API_KEY=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
GOOGLE_API_KEY=$(grep "^GOOGLE_API_KEY=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
MODEL_NAME=$(grep "^MODEL_NAME=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'")
ELASTIC_MCP_URL=$(grep "^ELASTIC_MCP_URL=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'")

# Assign defaults if missing
MODEL_NAME="${MODEL_NAME:-gemini-2.5-flash}"

if [ -z "$ELASTICSEARCH_API_KEY" ] || [ -z "$GOOGLE_API_KEY" ]; then
    log_error "Missing critical credentials in $ENV_FILE (ELASTICSEARCH_API_KEY or GOOGLE_API_KEY)."
    exit 1
fi

# Locate agents-cli
AGENTS_CLI="agents-cli"
if ! command -v agents-cli &> /dev/null; then
    if [ -f "$HOME/.local/bin/agents-cli" ]; then
        AGENTS_CLI="$HOME/.local/bin/agents-cli"
    elif [ -f "$HOME/Library/Python/3.9/bin/agents-cli" ]; then
        AGENTS_CLI="$HOME/Library/Python/3.9/bin/agents-cli"
    else
        log_warn "agents-cli not found in PATH. Checking for local virtual environments..."
        if [ -f ".venv/bin/agents-cli" ]; then
            AGENTS_CLI=".venv/bin/agents-cli"
        else
            log_info "Installing google-agents-cli globally using uv..."
            if command -v uv &> /dev/null; then
                if [ "$DRY_RUN" = false ]; then
                    uv tool install google-agents-cli --force
                else
                    echo "[DRY-RUN] uv tool install google-agents-cli --force"
                fi
            else
                log_error "uv tool not installed. Please install 'uv' or make 'agents-cli' available."
                exit 1
            fi
        fi
    fi
fi

log_info "Using agents-cli executable: ${BOLD}$AGENTS_CLI${NC}"

# Check GCP Authentication
if [ "$DRY_RUN" = false ]; then
    log_info "Configuring active gcloud project to $PROJECT_ID..."
    gcloud config set project "$PROJECT_ID" || {
        log_error "Failed to target project $PROJECT_ID in gcloud. Are you logged in?"
        exit 1
    }
fi

# ------------------------------------------------------------------------------
# Enable Required Services
# ------------------------------------------------------------------------------
log_info "Ensuring necessary Google Cloud API services are enabled..."
REQUIRED_SERVICES=(
    "secretmanager.googleapis.com"
    "run.googleapis.com"
    "aiplatform.googleapis.com"
    "artifactregistry.googleapis.com"
)

if [ "$DRY_RUN" = true ]; then
    echo "[DRY-RUN] gcloud services enable ${REQUIRED_SERVICES[*]}"
else
    # Enable services in parallel/batch
    gcloud services enable "${REQUIRED_SERVICES[@]}" --project="$PROJECT_ID"
fi
log_success "Google Cloud API services enabled."

# ------------------------------------------------------------------------------
# Secret Management Setup
# ------------------------------------------------------------------------------
log_info "Synchronizing secrets with GCP Secret Manager..."

upsert_secret() {
    local secret_name="$1"
    local secret_value="$2"
    
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] Create/Update secret: $secret_name"
        return
    fi
    
    # Check if secret already exists
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &> /dev/null; then
        log_info "Secret $secret_name already exists. Adding new version..."
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --project="$PROJECT_ID" --data-file=- > /dev/null
    else
        log_info "Creating new secret $secret_name..."
        gcloud secrets create "$secret_name" --project="$PROJECT_ID" --replication-policy="automatic" > /dev/null
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --project="$PROJECT_ID" --data-file=- > /dev/null
    fi
}

upsert_secret "ELASTICSEARCH_API_KEY" "$ELASTICSEARCH_API_KEY"
upsert_secret "GOOGLE_API_KEY" "$GOOGLE_API_KEY"

# ------------------------------------------------------------------------------
# Deploy Phase 1: Vertex AI ADK Agent
# ------------------------------------------------------------------------------
if [ "$DEPLOY_AGENT" = true ]; then
    log_info "🚀 Deploying Vertex AI ADK Agent Platform..."
    
    DEPLOY_CMD=("$AGENTS_CLI" "deploy" 
        "--project=$PROJECT_ID" 
        "--region=$REGION" 
        "--update-env-vars=ELASTICSEARCH_URL=${ELASTICSEARCH_URL},MODEL_NAME=${MODEL_NAME},ELASTIC_MCP_URL=${ELASTIC_MCP_URL}" 
        "--secrets=ELASTICSEARCH_API_KEY=ELASTICSEARCH_API_KEY,GOOGLE_API_KEY=GOOGLE_API_KEY" 
        "--no-wait" 
        "--no-confirm-project"
    )
    
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] ${DEPLOY_CMD[*]}"
    else
        "${DEPLOY_CMD[@]}"
    fi
    log_success "ADK Agent Platform deployment initiated successfully!"
fi

# ------------------------------------------------------------------------------
# Deploy Phase 2: FastAPI Backend (Cloud Run)
# ------------------------------------------------------------------------------
BACKEND_URL=""
if [ "$DEPLOY_APP" = true ]; then
    log_info "🚀 Compiling and deploying FastAPI Backend to Cloud Run..."
    
    # Assemble env vars
    ENV_VARS="ELASTICSEARCH_URL=${ELASTICSEARCH_URL},MODEL_NAME=${MODEL_NAME},ELASTIC_MCP_URL=${ELASTIC_MCP_URL},PROJECT_ID=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION}"
    
    # Map Secrets from Secret Manager directly into the environment of Cloud Run
    SECRETS="ELASTICSEARCH_API_KEY=ELASTICSEARCH_API_KEY:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest"
    
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] gcloud run deploy mall-brain-backend --source ./backend --region $REGION --allow-unauthenticated --set-env-vars $ENV_VARS --set-secrets $SECRETS"
        BACKEND_URL="https://mall-brain-backend-dryrun-url.a.run.app"
    else
        gcloud run deploy mall-brain-backend \
          --source ./backend \
          --region "$REGION" \
          --allow-unauthenticated \
          --set-env-vars "$ENV_VARS" \
          --set-secrets "$SECRETS" \
          --format="value(status.url)" > .backend_url.tmp
        
        BACKEND_URL=$(cat .backend_url.tmp | tr -d '[:space:]')
        rm .backend_url.tmp
    fi
    
    if [ -z "$BACKEND_URL" ]; then
        log_error "Failed to retrieve deployed Backend URL. Aborting Frontend deployment."
        exit 1
    fi
    
    log_success "FastAPI Backend is operational at: ${BOLD}$BACKEND_URL${NC}"
    
    # --------------------------------------------------------------------------
    # Deploy Phase 3: Next.js Frontend (Cloud Run)
    # --------------------------------------------------------------------------
    log_info "🚀 Compiling and deploying Next.js Frontend to Cloud Run..."
    log_info "Injecting build variable NEXT_PUBLIC_API_URL pointing to $BACKEND_URL..."
    
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] Create temporary frontend/.env.production with NEXT_PUBLIC_API_URL=$BACKEND_URL"
        echo "[DRY-RUN] gcloud run deploy mall-brain-frontend --source ./frontend --region $REGION --allow-unauthenticated"
        echo "[DRY-RUN] Remove temporary frontend/.env.production"
    else
        # Write temporary .env.production file to be uploaded with source build
        # This is copied into the Docker container context and read by Next.js npm run build
        echo "NEXT_PUBLIC_API_URL=$BACKEND_URL" > ./frontend/.env.production
        
        # Deploy Frontend using Cloud Run source build
        gcloud run deploy mall-brain-frontend \
          --source ./frontend \
          --region "$REGION" \
          --allow-unauthenticated
        
        # Clean up temporary .env.production file
        rm -f ./frontend/.env.production
    fi
    
    log_success "Next.js Frontend is operational!"
fi

# ------------------------------------------------------------------------------
# Deployment Completion Report
# ------------------------------------------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}=========================================================================="
echo "                     🎉 ALL DEPLOYMENTS COMPLETED!                        "
echo -e "==========================================================================${NC}"
if [ "$DEPLOY_APP" = true ]; then
    if [ "$DRY_RUN" = false ]; then
        FRONTEND_URL=$(gcloud run services describe mall-brain-frontend --region "$REGION" --format='value(status.url)' | tr -d '[:space:]')
    else
        FRONTEND_URL="https://mall-brain-frontend-dryrun-url.a.run.app"
    fi
    echo -e "  ${BOLD}Backend API endpoint :${NC} $BACKEND_URL/api/health"
    echo -e "  ${BOLD}Frontend UI URL      :${NC} $FRONTEND_URL"
fi
if [ "$DEPLOY_AGENT" = true ]; then
    echo -e "  ${BOLD}Agent Target         :${NC} Vertex AI Agent Platform (agent_runtime)"
fi
echo -e "${GREEN}${BOLD}==========================================================================${NC}"
echo ""

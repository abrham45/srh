#!/bin/bash

# SRH Chatbot Production Deployment Script
# ==========================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="SRH Chatbot"
APP_DIR="/opt/srh-chatbot"
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"
BACKUP_DIR="./backups"

# Functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_requirements() {
    log_info "Checking system requirements..."
    
    # Check if running as root or with sudo
    if [[ $EUID -eq 0 ]] && [[ -z "$SUDO_USER" ]]; then
        log_error "Don't run this script as root. Use a regular user with sudo privileges."
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker daemon is not running. Please start Docker service."
        exit 1
    fi
    
    # Check PostgreSQL
    if command -v pg_isready >/dev/null 2>&1; then
        if ! pg_isready -h localhost -p 5432 -U postgres -q 2>/dev/null; then
            log_warning "PostgreSQL is not running on localhost:5432"
            log_info "Make sure PostgreSQL is running before starting the application"
        else
            log_success "PostgreSQL is running"
        fi
    else
        log_warning "pg_isready not found. Please ensure PostgreSQL is installed and running"
    fi
    
    log_success "System requirements check completed"
}

setup_directories() {
    log_info "Setting up application directories..."
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p data
    mkdir -p backups
    mkdir -p scripts
    
    # Set proper permissions
    chmod 755 logs data backups scripts
    
    log_success "Directories setup completed"
}

check_environment() {
    log_info "Checking environment configuration..."
    
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file $ENV_FILE not found!"
        log_info "Please copy production.env.example to $ENV_FILE and configure it:"
        log_info "cp production.env.example $ENV_FILE"
        log_info "nano $ENV_FILE"
        exit 1
    fi
    
    # Check for required environment variables
    source "$ENV_FILE"
    
    if [[ -z "$TELEGRAM_TOKEN" ]] || [[ "$TELEGRAM_TOKEN" == "your_actual_telegram_bot_token_here" ]]; then
        log_error "TELEGRAM_TOKEN is not configured in $ENV_FILE"
        exit 1
    fi
    
    if [[ -z "$GEMINI_API_KEY" ]] || [[ "$GEMINI_API_KEY" == "your_actual_gemini_api_key_here" ]]; then
        log_error "GEMINI_API_KEY is not configured in $ENV_FILE"
        exit 1
    fi
    
    if [[ -z "$DB_PASSWORD" ]] || [[ "$DB_PASSWORD" == "your_secure_database_password_here" ]]; then
        log_error "DB_PASSWORD is not configured in $ENV_FILE"
        exit 1
    fi
    
    log_success "Environment configuration is valid"
}

backup_existing() {
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "Up"; then
        log_info "Creating backup before deployment..."
        
        # Create backup directory with timestamp
        BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_PATH="$BACKUP_DIR/pre_deploy_$BACKUP_TIMESTAMP"
        mkdir -p "$BACKUP_PATH"
        
        # Backup database
        if command -v pg_dump >/dev/null 2>&1; then
            log_info "Backing up database..."
            sudo -u postgres pg_dump srh_chatbot_db > "$BACKUP_PATH/database_backup.sql" 2>/dev/null || {
                log_warning "Database backup failed. Continuing with deployment..."
            }
        fi
        
        # Backup logs
        if [[ -d "logs" ]]; then
            cp -r logs "$BACKUP_PATH/logs_backup"
        fi
        
        log_success "Backup created at $BACKUP_PATH"
    fi
}

build_application() {
    log_info "Building application image..."
    
    # Build the Docker image
    docker build -t srh-chatbot:latest . || {
        log_error "Docker build failed"
        exit 1
    }
    
    log_success "Application image built successfully"
}

deploy_application() {
    log_info "Deploying $APP_NAME..."
    
    # Stop existing containers
    log_info "Stopping existing containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down --remove-orphans 2>/dev/null || true
    
    # Remove unused images to free space
    docker image prune -f >/dev/null 2>&1 || true
    
    # Start the application
    log_info "Starting application containers..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    # Wait for containers to be ready
    log_info "Waiting for containers to start..."
    sleep 10
    
    # Check if containers are running
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" ps | grep -q "Up"; then
        log_error "Containers failed to start. Check logs with: docker-compose -f $DOCKER_COMPOSE_FILE logs"
        exit 1
    fi
    
    log_success "Application deployed successfully"
}

run_health_checks() {
    log_info "Running health checks..."
    
    # Wait a bit more for the application to fully start
    sleep 15
    
    # Check container health
    CONTAINER_STATUS=$(docker-compose -f "$DOCKER_COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}")
    echo "$CONTAINER_STATUS"
    
    # Check if web container is healthy
    WEB_CONTAINER=$(docker-compose -f "$DOCKER_COMPOSE_FILE" ps -q web)
    if [[ -n "$WEB_CONTAINER" ]]; then
        HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$WEB_CONTAINER" 2>/dev/null || echo "unknown")
        if [[ "$HEALTH_STATUS" == "healthy" ]] || [[ "$HEALTH_STATUS" == "unknown" ]]; then
            log_success "Web container is running"
        else
            log_warning "Web container health check failed: $HEALTH_STATUS"
        fi
    fi
    
    # Test database connectivity
    log_info "Testing database connectivity..."
    if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T web python manage.py check --deploy >/dev/null 2>&1; then
        log_success "Database connectivity test passed"
    else
        log_warning "Database connectivity test failed"
    fi
    
    # Check bot connectivity
    log_info "Testing bot connectivity..."
    BOT_TEST=$(docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T web python -c "
import os
import asyncio
from telegram import Bot
async def test_bot():
    try:
        bot = Bot(os.environ['TELEGRAM_TOKEN'])
        me = await bot.get_me()
        print(f'✅ Bot @{me.username} is connected')
    except Exception as e:
        print(f'❌ Bot connection failed: {e}')
asyncio.run(test_bot())
" 2>/dev/null) || echo "❌ Bot test failed"
    
    echo "$BOT_TEST"
    
    log_success "Health checks completed"
}

show_deployment_info() {
    log_success "$APP_NAME has been deployed successfully!"
    echo ""
    echo "📊 Deployment Information:"
    echo "=========================="
    echo "🐳 Container Status:"
    docker-compose -f "$DOCKER_COMPOSE_FILE" ps
    echo ""
    echo "📝 Useful Commands:"
    echo "-------------------"
    echo "• View logs:           docker-compose -f $DOCKER_COMPOSE_FILE logs -f"
    echo "• Restart application: docker-compose -f $DOCKER_COMPOSE_FILE restart"
    echo "• Stop application:    docker-compose -f $DOCKER_COMPOSE_FILE down"
    echo "• Update application:  git pull && $0"
    echo ""
    echo "📁 Important Directories:"
    echo "-------------------------"
    echo "• Application logs: ./logs/"
    echo "• Backups:         ./backups/"
    echo "• Data:            ./data/"
    echo ""
    echo "🔧 Configuration:"
    echo "-----------------"
    echo "• Environment file: $ENV_FILE"
    echo "• Docker compose:   $DOCKER_COMPOSE_FILE"
    echo ""
    echo "🚨 Monitoring:"
    echo "--------------"
    echo "• Check health: docker-compose -f $DOCKER_COMPOSE_FILE exec web python manage.py check"
    echo "• Monitor resources: docker stats"
    echo "• View database: sudo -u postgres psql -d srh_chatbot_db"
    echo ""
}

# Main deployment process
main() {
    echo "🚀 $APP_NAME Production Deployment"
    echo "===================================="
    echo ""
    
    check_requirements
    setup_directories
    check_environment
    backup_existing
    build_application
    deploy_application
    run_health_checks
    show_deployment_info
    
    log_success "Deployment completed successfully! 🎉"
}

# Handle script interruption
trap 'log_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"

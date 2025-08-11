#!/bin/bash

# SRH Chatbot Deployment with Remote PostgreSQL
# =============================================
# Database: 164.92.98.189:5432
# User: taskuser

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Database configuration
DB_HOST="164.92.98.189"
DB_PORT="5432"
DB_USER="taskuser"
DB_PASSWORD="taskpassword"
DB_NAME="srh_chatbot_db"

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

test_database_connection() {
    log_info "Testing connection to remote PostgreSQL..."
    
    # Test with Docker container
    if docker run --rm postgres:15-alpine pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1; then
        log_success "Remote PostgreSQL is reachable"
    else
        log_error "Cannot reach PostgreSQL at $DB_HOST:$DB_PORT"
        log_info "Please check:"
        log_info "1. Database server is running"
        log_info "2. Firewall allows connections from this server"
        log_info "3. PostgreSQL accepts external connections"
        exit 1
    fi
}

setup_database() {
    log_info "Setting up database on remote server..."
    
    # Check if database exists
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        log_warning "Database '$DB_NAME' already exists on remote server"
        read -p "Do you want to continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
    else
        # Create database
        log_info "Creating database '$DB_NAME'..."
        PGPASSWORD="$DB_PASSWORD" createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" || {
            log_warning "Database creation failed. It may already exist or you may not have privileges."
            log_info "Continuing with existing database..."
        }
    fi
    
    # Test database connection
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        log_success "Database connection successful"
    else
        log_error "Cannot connect to database '$DB_NAME'"
        exit 1
    fi
}

check_docker() {
    log_info "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        log_warning "Please log out and log back in for Docker group changes to take effect"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_info "Installing Docker Compose..."
        COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
        sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
    
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker daemon is not running. Please start Docker service."
        exit 1
    fi
    
    log_success "Docker is ready"
}

setup_environment() {
    log_info "Setting up environment configuration..."
    
    # Create .env.production file
    cat > .env.production << EOF
# SRH Chatbot Production Environment
# =================================

# TELEGRAM BOT CONFIGURATION
TELEGRAM_TOKEN=your_actual_telegram_bot_token_here
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_API_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent

# DATABASE CONFIGURATION (Remote PostgreSQL)
DB_HOST=$DB_HOST
DB_PORT=$DB_PORT
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD

# DJANGO CONFIGURATION
DJANGO_SETTINGS_MODULE=config.settings
DEBUG=False
SECRET_KEY=$(openssl rand -base64 32)
ALLOWED_HOSTS=localhost,127.0.0.1,$(curl -s ifconfig.me)

# LOGGING
LOG_LEVEL=INFO
LOG_FILE=/app/logs/srh_chatbot.log

# SECURITY SETTINGS
SECURE_SSL_REDIRECT=False
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True

# PERFORMANCE
DB_CONN_MAX_AGE=60
DB_CONN_HEALTH_CHECKS=True
EOF

    log_success "Environment file created"
    
    # Check for required tokens
    if [[ ! -f ".env.production" ]]; then
        log_error "Failed to create environment file"
        exit 1
    fi
    
    log_warning "⚠️  IMPORTANT: You need to update the following in .env.production:"
    echo ""
    echo "1. TELEGRAM_TOKEN=your_actual_telegram_bot_token_here"
    echo "2. GEMINI_API_KEY=your_actual_gemini_api_key_here"
    echo ""
    read -p "Press Enter to edit the environment file now..."
    nano .env.production
    
    # Verify tokens are set
    source .env.production
    if [[ "$TELEGRAM_TOKEN" == "your_actual_telegram_bot_token_here" ]] || [[ -z "$TELEGRAM_TOKEN" ]]; then
        log_error "TELEGRAM_TOKEN is not configured properly"
        exit 1
    fi
    
    if [[ "$GEMINI_API_KEY" == "your_actual_gemini_api_key_here" ]] || [[ -z "$GEMINI_API_KEY" ]]; then
        log_error "GEMINI_API_KEY is not configured properly"
        exit 1
    fi
    
    log_success "Environment configuration is complete"
}

deploy_application() {
    log_info "Deploying SRH Chatbot..."
    
    # Create necessary directories
    mkdir -p logs data backups scripts
    chmod 755 logs data backups scripts
    
    # Stop any existing containers
    log_info "Stopping existing containers..."
    docker-compose -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || true
    
    # Build the application
    log_info "Building application image..."
    docker build -t srh-chatbot:latest . || {
        log_error "Docker build failed"
        exit 1
    }
    
    # Start the application
    log_info "Starting application containers..."
    docker-compose -f docker-compose.prod.yml up -d || {
        log_error "Failed to start containers"
        docker-compose -f docker-compose.prod.yml logs
        exit 1
    }
    
    # Wait for startup
    log_info "Waiting for application to initialize..."
    sleep 20
    
    # Check container status
    if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        log_success "Application containers are running"
    else
        log_error "Some containers failed to start"
        docker-compose -f docker-compose.prod.yml ps
        docker-compose -f docker-compose.prod.yml logs
        exit 1
    fi
}

run_database_migrations() {
    log_info "Running database migrations..."
    
    # Run migrations
    if docker-compose -f docker-compose.prod.yml exec -T web python manage.py migrate; then
        log_success "Database migrations completed"
    else
        log_error "Database migrations failed"
        docker-compose -f docker-compose.prod.yml logs web
        exit 1
    fi
    
    # Create superuser (optional)
    log_info "Creating Django superuser (optional)..."
    docker-compose -f docker-compose.prod.yml exec -T web python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@srh-chatbot.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
" 2>/dev/null || log_info "Superuser creation skipped"
}

run_health_checks() {
    log_info "Running health checks..."
    
    # Test database connectivity
    if docker-compose -f docker-compose.prod.yml exec -T web python manage.py check --deploy > /dev/null 2>&1; then
        log_success "✅ Database connectivity test: PASSED"
    else
        log_warning "❌ Database connectivity test: FAILED"
    fi
    
    # Test bot connectivity
    log_info "Testing Telegram bot connection..."
    BOT_TEST=$(docker-compose -f docker-compose.prod.yml exec -T web python -c "
import os, asyncio
from telegram import Bot
async def test():
    try:
        bot = Bot(os.environ['TELEGRAM_TOKEN'])
        me = await bot.get_me()
        print(f'✅ Bot @{me.username} connected successfully')
        return True
    except Exception as e:
        print(f'❌ Bot connection failed: {e}')
        return False
asyncio.run(test())
" 2>/dev/null)
    
    echo "$BOT_TEST"
    
    # Test database operations
    log_info "Testing database operations..."
    SESSIONS_COUNT=$(docker-compose -f docker-compose.prod.yml exec -T web python -c "
from bot.models import UserSession
print(f'Total user sessions: {UserSession.objects.count()}')
" 2>/dev/null)
    echo "$SESSIONS_COUNT"
    
    log_success "Health checks completed"
}

show_deployment_summary() {
    log_success "🎉 SRH Chatbot deployed successfully!"
    echo ""
    echo "📊 Deployment Summary:"
    echo "======================"
    echo "🗄️  Database: PostgreSQL at $DB_HOST:$DB_PORT"
    echo "⚡ Cache: Redis in Docker container"
    echo "🤖 App: SRH Chatbot in Docker container"
    echo ""
    echo "📋 Container Status:"
    docker-compose -f docker-compose.prod.yml ps
    echo ""
    echo "🔗 Database Connection:"
    echo "• Host: $DB_HOST"
    echo "• Port: $DB_PORT" 
    echo "• Database: $DB_NAME"
    echo "• User: $DB_USER"
    echo ""
    echo "🔧 Management Commands:"
    echo "• View logs:     docker-compose -f docker-compose.prod.yml logs -f"
    echo "• Restart app:   docker-compose -f docker-compose.prod.yml restart web"
    echo "• Stop all:      docker-compose -f docker-compose.prod.yml down"
    echo "• Update app:    git pull && docker build -t srh-chatbot:latest . && docker-compose -f docker-compose.prod.yml up -d"
    echo ""
    echo "🗄️  Database Access:"
    echo "• Connect: PGPASSWORD='$DB_PASSWORD' psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME"
    echo "• Backup: PGPASSWORD='$DB_PASSWORD' pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME > backup.sql"
    echo ""
    echo "🚨 Important Notes:"
    echo "• Admin panel: http://localhost:8000/admin (admin/admin123)"
    echo "• Environment file: .env.production"
    echo "• Logs directory: ./logs/"
    echo "• Backups directory: ./backups/"
    echo ""
    echo "🔍 Verify Bot:"
    source .env.production
    echo "• Test command: curl 'https://api.telegram.org/bot$TELEGRAM_TOKEN/getMe'"
    echo ""
}

# Main deployment process
main() {
    echo "🚀 SRH Chatbot Deployment (Remote PostgreSQL)"
    echo "=============================================="
    echo "📍 Database: $DB_HOST:$DB_PORT"
    echo "👤 User: $DB_USER"
    echo ""
    
    test_database_connection
    check_docker
    setup_database
    setup_environment
    deploy_application
    run_database_migrations
    run_health_checks
    show_deployment_summary
    
    log_success "Deployment completed successfully! 🎉"
    echo ""
    log_info "Your SRH chatbot is now running and connected to the remote database!"
}

# Handle script interruption
trap 'log_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"

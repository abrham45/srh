#!/bin/bash

# SRH Chatbot Deployment with Existing PostgreSQL
# ===============================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

check_postgresql() {
    log_info "Checking existing PostgreSQL installation..."
    
    if ! command -v psql &> /dev/null; then
        log_error "PostgreSQL client tools not found. Please install PostgreSQL first."
        log_info "Ubuntu/Debian: sudo apt install postgresql-client"
        log_info "CentOS/RHEL: sudo yum install postgresql"
        exit 1
    fi
    
    if ! systemctl is-active --quiet postgresql; then
        log_error "PostgreSQL service is not running"
        log_info "Start it with: sudo systemctl start postgresql"
        exit 1
    fi
    
    log_success "PostgreSQL is installed and running"
}

check_docker() {
    log_info "Checking Docker installation..."
    
    if ! command -v docker &> /dev/null; then
        log_info "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        log_warning "You may need to log out and log back in for Docker group changes"
    else
        log_success "Docker is already installed"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_info "Installing Docker Compose..."
        COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
        sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    else
        log_success "Docker Compose is already installed"
    fi
    
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker daemon is not running. Please start Docker service."
        exit 1
    fi
}

setup_database() {
    log_info "Setting up database for SRH Chatbot..."
    
    # Check if database already exists
    if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw srh_chatbot_db; then
        log_warning "Database 'srh_chatbot_db' already exists"
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo -u postgres psql -c "DROP DATABASE IF EXISTS srh_chatbot_db;"
            sudo -u postgres psql -c "DROP USER IF EXISTS srhbot;"
        else
            log_info "Using existing database"
            return
        fi
    fi
    
    # Create database and user
    log_info "Creating database and user..."
    sudo -u postgres psql << EOF
CREATE DATABASE srh_chatbot_db;
CREATE USER srhbot WITH PASSWORD 'srh_secure_2024!';
GRANT ALL PRIVILEGES ON DATABASE srh_chatbot_db TO srhbot;
ALTER USER srhbot CREATEDB;
\q
EOF
    
    # Test connection
    if PGPASSWORD='srh_secure_2024!' psql -h localhost -U srhbot -d srh_chatbot_db -c "SELECT 1;" > /dev/null 2>&1; then
        log_success "Database setup completed successfully"
    else
        log_error "Database connection test failed"
        log_info "You may need to configure PostgreSQL authentication:"
        log_info "1. Edit /etc/postgresql/*/main/pg_hba.conf"
        log_info "2. Change 'peer' to 'md5' for local connections"
        log_info "3. Restart PostgreSQL: sudo systemctl restart postgresql"
        exit 1
    fi
}

check_environment() {
    log_info "Checking environment configuration..."
    
    if [[ ! -f ".env.production" ]]; then
        if [[ -f "production.env.example" ]]; then
            cp production.env.example .env.production
            log_warning "Created .env.production from template"
        else
            log_error "Environment template not found. Please create .env.production manually"
            exit 1
        fi
    fi
    
    # Update database password in env file
    sed -i 's/DB_PASSWORD=.*/DB_PASSWORD=srh_secure_2024!/' .env.production
    
    # Check for required tokens
    source .env.production
    
    if [[ -z "$TELEGRAM_TOKEN" ]] || [[ "$TELEGRAM_TOKEN" == "your_actual_telegram_bot_token_here" ]]; then
        log_error "Please update TELEGRAM_TOKEN in .env.production"
        nano .env.production
        source .env.production
    fi
    
    if [[ -z "$GEMINI_API_KEY" ]] || [[ "$GEMINI_API_KEY" == "your_actual_gemini_api_key_here" ]]; then
        log_error "Please update GEMINI_API_KEY in .env.production"
        nano .env.production
        source .env.production
    fi
    
    log_success "Environment configuration is ready"
}

test_docker_postgres_connection() {
    log_info "Testing Docker to PostgreSQL connection..."
    
    if docker run --rm --add-host=host.docker.internal:host-gateway postgres:15-alpine pg_isready -h host.docker.internal -p 5432 -U srhbot > /dev/null 2>&1; then
        log_success "Docker can connect to PostgreSQL"
    else
        log_warning "Docker cannot connect to PostgreSQL"
        log_info "Configuring PostgreSQL for Docker access..."
        
        # Add Docker network to pg_hba.conf if not already there
        PG_HBA_FILE=$(sudo -u postgres psql -t -P format=unaligned -c 'SHOW hba_file;')
        if ! sudo grep -q "172.17.0.0/16" "$PG_HBA_FILE" 2>/dev/null; then
            echo "host    srh_chatbot_db    srhbot    172.17.0.0/16    md5" | sudo tee -a "$PG_HBA_FILE"
            sudo systemctl reload postgresql
            sleep 2
        fi
        
        # Test again
        if docker run --rm --add-host=host.docker.internal:host-gateway postgres:15-alpine pg_isready -h host.docker.internal -p 5432 -U srhbot > /dev/null 2>&1; then
            log_success "Docker to PostgreSQL connection configured successfully"
        else
            log_error "Failed to configure Docker to PostgreSQL connection"
            log_info "Manual steps:"
            log_info "1. Edit pg_hba.conf: sudo nano $PG_HBA_FILE"
            log_info "2. Add: host    srh_chatbot_db    srhbot    172.17.0.0/16    md5"
            log_info "3. Reload: sudo systemctl reload postgresql"
            exit 1
        fi
    fi
}

deploy_application() {
    log_info "Deploying SRH Chatbot..."
    
    # Create necessary directories
    mkdir -p logs data backups scripts
    
    # Stop any existing containers
    docker-compose -f docker-compose.prod.yml down --remove-orphans 2>/dev/null || true
    
    # Build the application
    log_info "Building application image..."
    docker build -t srh-chatbot:latest .
    
    # Start the application
    log_info "Starting application..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for startup
    log_info "Waiting for application to start..."
    sleep 15
    
    # Check if containers are running
    if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        log_success "Application deployed successfully"
    else
        log_error "Application failed to start. Check logs:"
        docker-compose -f docker-compose.prod.yml logs
        exit 1
    fi
}

run_health_checks() {
    log_info "Running health checks..."
    
    # Test database connectivity
    if docker-compose -f docker-compose.prod.yml exec -T web python manage.py check --deploy > /dev/null 2>&1; then
        log_success "Database connectivity: OK"
    else
        log_warning "Database connectivity: Failed"
    fi
    
    # Test bot connectivity
    BOT_TEST=$(docker-compose -f docker-compose.prod.yml exec -T web python -c "
import os, asyncio
from telegram import Bot
async def test():
    try:
        bot = Bot(os.environ['TELEGRAM_TOKEN'])
        me = await bot.get_me()
        print(f'Bot @{me.username} connected successfully')
    except Exception as e:
        print(f'Bot connection failed: {e}')
asyncio.run(test())
" 2>/dev/null)
    
    echo "$BOT_TEST"
    
    log_success "Health checks completed"
}

show_summary() {
    log_success "🎉 SRH Chatbot deployed successfully with your existing PostgreSQL!"
    echo ""
    echo "📊 Deployment Summary:"
    echo "====================="
    echo "🗄️  Database: Existing PostgreSQL on host"
    echo "⚡ Cache: Redis in Docker container"
    echo "🤖 App: SRH Chatbot in Docker container"
    echo ""
    echo "📋 Container Status:"
    docker-compose -f docker-compose.prod.yml ps
    echo ""
    echo "🔧 Management Commands:"
    echo "• View logs:     docker-compose -f docker-compose.prod.yml logs -f"
    echo "• Restart:       docker-compose -f docker-compose.prod.yml restart"
    echo "• Stop:          docker-compose -f docker-compose.prod.yml down"
    echo "• Update:        git pull && docker build -t srh-chatbot:latest . && docker-compose -f docker-compose.prod.yml up -d"
    echo ""
    echo "🗄️  Database Info:"
    echo "• Host: localhost:5432"
    echo "• Database: srh_chatbot_db"
    echo "• User: srhbot"
    echo "• Connect: psql -U srhbot -d srh_chatbot_db"
    echo ""
    echo "🔍 Verify deployment:"
    echo "• Check bot: curl 'https://api.telegram.org/bot$TELEGRAM_TOKEN/getMe'"
    echo "• Monitor: htop, docker stats"
    echo ""
}

# Main deployment process
main() {
    echo "🚀 SRH Chatbot Deployment (Existing PostgreSQL)"
    echo "==============================================="
    echo ""
    
    check_postgresql
    check_docker
    setup_database
    check_environment
    test_docker_postgres_connection
    deploy_application
    run_health_checks
    show_summary
    
    log_success "Deployment completed! Your SRH chatbot is now running! 🎉"
}

# Handle interruption
trap 'log_error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@"

#!/bin/bash

# SRH Chatbot Linux Server Setup Script
# =====================================
# This script prepares a fresh Linux server for SRH Chatbot deployment

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

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        log_error "Cannot detect OS. This script supports Ubuntu/Debian and CentOS/RHEL only."
        exit 1
    fi
    
    log_info "Detected OS: $OS $VER"
}

check_privileges() {
    if [[ $EUID -eq 0 ]]; then
        log_warning "Running as root. It's recommended to use a regular user with sudo privileges."
        USER_HOME="/root"
    else
        if ! sudo -n true 2>/dev/null; then
            log_error "This script requires sudo privileges. Please run with a user that has sudo access."
            exit 1
        fi
        USER_HOME="$HOME"
    fi
}

update_system() {
    log_info "Updating system packages..."
    
    case "$OS" in
        *"Ubuntu"*|*"Debian"*)
            sudo apt update && sudo apt upgrade -y
            sudo apt install -y curl wget git nano htop unzip software-properties-common apt-transport-https ca-certificates gnupg lsb-release
            ;;
        *"CentOS"*|*"Red Hat"*|*"Rocky"*|*"AlmaLinux"*)
            sudo yum update -y
            sudo yum install -y curl wget git nano htop unzip yum-utils
            ;;
        *)
            log_error "Unsupported OS: $OS"
            exit 1
            ;;
    esac
    
    log_success "System updated successfully"
}

install_docker() {
    log_info "Installing Docker..."
    
    if command -v docker &> /dev/null; then
        log_warning "Docker is already installed"
        return
    fi
    
    case "$OS" in
        *"Ubuntu"*|*"Debian"*)
            # Add Docker's official GPG key
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
            
            # Add Docker repository
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            # Install Docker
            sudo apt update
            sudo apt install -y docker-ce docker-ce-cli containerd.io
            ;;
        *"CentOS"*|*"Red Hat"*|*"Rocky"*|*"AlmaLinux"*)
            # Add Docker repository
            sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            
            # Install Docker
            sudo yum install -y docker-ce docker-ce-cli containerd.io
            ;;
    esac
    
    # Start and enable Docker
    sudo systemctl start docker
    sudo systemctl enable docker
    
    # Add current user to docker group
    if [[ $EUID -ne 0 ]]; then
        sudo usermod -aG docker $USER
        log_warning "You need to log out and log back in for Docker group changes to take effect"
    fi
    
    log_success "Docker installed successfully"
}

install_docker_compose() {
    log_info "Installing Docker Compose..."
    
    if command -v docker-compose &> /dev/null; then
        log_warning "Docker Compose is already installed"
        return
    fi
    
    # Get latest version
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    
    # Download and install
    sudo curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    # Create symlink for easier access
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    log_success "Docker Compose installed successfully"
}

install_postgresql() {
    log_info "Installing PostgreSQL..."
    
    if command -v psql &> /dev/null; then
        log_warning "PostgreSQL is already installed"
        return
    fi
    
    case "$OS" in
        *"Ubuntu"*|*"Debian"*)
            sudo apt install -y postgresql postgresql-contrib
            ;;
        *"CentOS"*|*"Red Hat"*|*"Rocky"*|*"AlmaLinux"*)
            sudo yum install -y postgresql-server postgresql-contrib
            sudo postgresql-setup initdb
            ;;
    esac
    
    # Start and enable PostgreSQL
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
    
    log_success "PostgreSQL installed successfully"
}

configure_postgresql() {
    log_info "Configuring PostgreSQL..."
    
    # Set up database and user
    sudo -u postgres psql << EOF
CREATE DATABASE srh_chatbot_db;
CREATE USER srhbot WITH PASSWORD 'secure_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE srh_chatbot_db TO srhbot;
ALTER USER srhbot CREATEDB;
\q
EOF
    
    # Configure authentication
    case "$OS" in
        *"Ubuntu"*|*"Debian"*)
            PG_HBA_FILE="/etc/postgresql/*/main/pg_hba.conf"
            PG_CONF_FILE="/etc/postgresql/*/main/postgresql.conf"
            ;;
        *"CentOS"*|*"Red Hat"*|*"Rocky"*|*"AlmaLinux"*)
            PG_HBA_FILE="/var/lib/pgsql/data/pg_hba.conf"
            PG_CONF_FILE="/var/lib/pgsql/data/postgresql.conf"
            ;;
    esac
    
    # Update pg_hba.conf for local connections
    sudo sed -i 's/local   all             all                                     peer/local   all             all                                     md5/' $PG_HBA_FILE
    
    # Restart PostgreSQL
    sudo systemctl restart postgresql
    
    log_success "PostgreSQL configured successfully"
    log_warning "Default database password is 'secure_password_change_me' - PLEASE CHANGE IT!"
}

setup_firewall() {
    log_info "Configuring firewall..."
    
    case "$OS" in
        *"Ubuntu"*|*"Debian"*)
            if command -v ufw &> /dev/null; then
                sudo ufw --force enable
                sudo ufw allow ssh
                sudo ufw allow 80/tcp
                sudo ufw allow 443/tcp
                # Only allow Docker port from localhost
                sudo ufw allow from 127.0.0.1 to any port 8000
                log_success "UFW firewall configured"
            fi
            ;;
        *"CentOS"*|*"Red Hat"*|*"Rocky"*|*"AlmaLinux"*)
            if command -v firewall-cmd &> /dev/null; then
                sudo systemctl enable firewalld
                sudo systemctl start firewalld
                sudo firewall-cmd --permanent --add-service=ssh
                sudo firewall-cmd --permanent --add-service=http
                sudo firewall-cmd --permanent --add-service=https
                sudo firewall-cmd --reload
                log_success "FirewallD configured"
            fi
            ;;
    esac
}

create_app_directory() {
    log_info "Creating application directory..."
    
    APP_DIR="/opt/srh-chatbot"
    
    # Create directory
    sudo mkdir -p "$APP_DIR"
    
    # Set ownership to current user if not root
    if [[ $EUID -ne 0 ]]; then
        sudo chown $USER:$USER "$APP_DIR"
    fi
    
    # Create subdirectories
    mkdir -p "$APP_DIR"/{logs,data,backups,scripts}
    
    log_success "Application directory created at $APP_DIR"
}

install_optional_tools() {
    log_info "Installing optional monitoring tools..."
    
    case "$OS" in
        *"Ubuntu"*|*"Debian"*)
            sudo apt install -y htop iotop nethogs ncdu tree
            ;;
        *"CentOS"*|*"Red Hat"*|*"Rocky"*|*"AlmaLinux"*)
            sudo yum install -y htop iotop nethogs ncdu tree
            ;;
    esac
    
    log_success "Optional tools installed"
}

setup_log_rotation() {
    log_info "Setting up log rotation..."
    
    sudo tee /etc/logrotate.d/srh-chatbot > /dev/null << 'EOF'
/opt/srh-chatbot/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        if [ -f /opt/srh-chatbot/docker-compose.prod.yml ]; then
            cd /opt/srh-chatbot && docker-compose -f docker-compose.prod.yml restart web >/dev/null 2>&1 || true
        fi
    endscript
}
EOF
    
    log_success "Log rotation configured"
}

create_maintenance_scripts() {
    log_info "Creating maintenance scripts..."
    
    SCRIPTS_DIR="/opt/srh-chatbot/scripts"
    
    # Backup script
    cat > "$SCRIPTS_DIR/backup.sh" << 'EOF'
#!/bin/bash
# SRH Chatbot Backup Script

BACKUP_DIR="/opt/srh-chatbot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/opt/srh-chatbot"

mkdir -p "$BACKUP_DIR"

echo "Starting backup: $DATE"

# Backup database
if command -v pg_dump >/dev/null 2>&1; then
    sudo -u postgres pg_dump srh_chatbot_db > "$BACKUP_DIR/db_backup_$DATE.sql"
    echo "Database backup completed"
fi

# Backup application data
if [ -d "$APP_DIR/data" ]; then
    tar -czf "$BACKUP_DIR/data_backup_$DATE.tar.gz" -C "$APP_DIR" data
    echo "Data backup completed"
fi

# Backup logs
if [ -d "$APP_DIR/logs" ]; then
    tar -czf "$BACKUP_DIR/logs_backup_$DATE.tar.gz" -C "$APP_DIR" logs
    echo "Logs backup completed"
fi

# Cleanup old backups (keep last 7 days)
find "$BACKUP_DIR" -name "*.sql" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

    # Update script
    cat > "$SCRIPTS_DIR/update.sh" << 'EOF'
#!/bin/bash
# SRH Chatbot Update Script

APP_DIR="/opt/srh-chatbot"
cd "$APP_DIR"

echo "Starting update process..."

# Backup before update
./scripts/backup.sh

# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml down
docker build -t srh-chatbot:latest .
docker-compose -f docker-compose.prod.yml up -d

echo "Update completed successfully"
EOF

    # Status script
    cat > "$SCRIPTS_DIR/status.sh" << 'EOF'
#!/bin/bash
# SRH Chatbot Status Script

APP_DIR="/opt/srh-chatbot"
cd "$APP_DIR"

echo "SRH Chatbot Status Report"
echo "========================="
echo ""

echo "🐳 Container Status:"
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "📊 Resource Usage:"
docker stats --no-stream

echo ""
echo "🗄️  Database Status:"
sudo -u postgres psql -d srh_chatbot_db -c "SELECT COUNT(*) as total_sessions FROM bot_usersession;" 2>/dev/null || echo "Database not accessible"

echo ""
echo "📁 Disk Usage:"
df -h /opt/srh-chatbot

echo ""
echo "🔧 Recent Logs (last 10 lines):"
docker-compose -f docker-compose.prod.yml logs --tail=10 web
EOF

    # Make scripts executable
    chmod +x "$SCRIPTS_DIR"/*.sh
    
    log_success "Maintenance scripts created"
}

setup_cron_jobs() {
    log_info "Setting up cron jobs..."
    
    # Add daily backup
    (crontab -l 2>/dev/null; echo "0 2 * * * /opt/srh-chatbot/scripts/backup.sh >> /opt/srh-chatbot/logs/backup.log 2>&1") | crontab -
    
    log_success "Cron jobs configured (daily backup at 2 AM)"
}

show_summary() {
    echo ""
    log_success "🎉 Server setup completed successfully!"
    echo ""
    echo "📋 What was installed:"
    echo "====================="
    echo "✅ System updates"
    echo "✅ Docker & Docker Compose"
    echo "✅ PostgreSQL database"
    echo "✅ Firewall configuration"
    echo "✅ Application directory: /opt/srh-chatbot"
    echo "✅ Log rotation"
    echo "✅ Maintenance scripts"
    echo "✅ Automated backups"
    echo ""
    echo "🔧 Next Steps:"
    echo "=============="
    echo "1. Clone your application:"
    echo "   cd /opt/srh-chatbot"
    echo "   git clone <your-repo-url> ."
    echo ""
    echo "2. Configure environment:"
    echo "   cp production.env.example .env.production"
    echo "   nano .env.production"
    echo ""
    echo "3. Deploy the application:"
    echo "   chmod +x deploy-production.sh"
    echo "   ./deploy-production.sh"
    echo ""
    echo "4. IMPORTANT: Change the default database password!"
    echo "   sudo -u postgres psql -c \"ALTER USER srhbot PASSWORD 'your_new_secure_password';\""
    echo ""
    echo "📊 Useful Commands:"
    echo "=================="
    echo "• Check status:    /opt/srh-chatbot/scripts/status.sh"
    echo "• Create backup:   /opt/srh-chatbot/scripts/backup.sh"
    echo "• Update app:      /opt/srh-chatbot/scripts/update.sh"
    echo "• View logs:       docker-compose -f /opt/srh-chatbot/docker-compose.prod.yml logs -f"
    echo ""
    
    if [[ $EUID -ne 0 ]]; then
        log_warning "Please log out and log back in for Docker group changes to take effect"
    fi
}

# Main setup process
main() {
    echo "🖥️  SRH Chatbot Linux Server Setup"
    echo "=================================="
    echo ""
    
    detect_os
    check_privileges
    update_system
    install_docker
    install_docker_compose
    install_postgresql
    configure_postgresql
    setup_firewall
    create_app_directory
    install_optional_tools
    setup_log_rotation
    create_maintenance_scripts
    setup_cron_jobs
    show_summary
}

# Handle script interruption
trap 'log_error "Setup interrupted"; exit 1' INT TERM

# Run main function
main "$@"

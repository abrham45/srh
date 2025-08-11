# 🚀 SRH Chatbot - Linux Server Deployment Guide

## 📋 Prerequisites

- Linux server (Ubuntu 20.04+ or CentOS 7+ recommended)
- Root or sudo access
- Minimum 2GB RAM, 20GB disk space
- Public IP or domain name (for webhook setup if needed)

## 🔧 Step 1: Server Preparation

### Update System
```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### Install Essential Tools
```bash
# Ubuntu/Debian
sudo apt install -y curl wget git nano htop unzip

# CentOS/RHEL  
sudo yum install -y curl wget git nano htop unzip
```

## 🐳 Step 2: Install Docker & Docker Compose

### Install Docker
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# CentOS/RHEL
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### Install Docker Compose
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Verify Installation
```bash
docker --version
docker-compose --version
```

**⚠️ Log out and log back in for group changes to take effect**

## 🗄️ Step 3: Install PostgreSQL

### Ubuntu/Debian
```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### CentOS/RHEL
```bash
sudo yum install -y postgresql-server postgresql-contrib
sudo postgresql-setup initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Configure PostgreSQL
```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE srh_chatbot_db;
CREATE USER postgres WITH PASSWORD '1234';
GRANT ALL PRIVILEGES ON DATABASE srh_chatbot_db TO postgres;
ALTER USER postgres CREATEDB;
\q
```

### Configure PostgreSQL Authentication
```bash
# Edit pg_hba.conf
sudo nano /etc/postgresql/*/main/pg_hba.conf  # Ubuntu
# OR
sudo nano /var/lib/pgsql/data/pg_hba.conf     # CentOS

# Change this line from 'peer' to 'md5':
local   all             all                                     md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

## 📁 Step 4: Deploy the Application

### Clone Repository
```bash
# Create app directory
sudo mkdir -p /opt/srh-chatbot
sudo chown $USER:$USER /opt/srh-chatbot
cd /opt/srh-chatbot

# Clone your repository (replace with your actual repo URL)
git clone https://github.com/yourusername/srh_chatbot.git .
```

### Set Up Environment Variables
```bash
# Create production environment file
nano .env.production
```

Add the following content to `.env.production`:
```env
# Telegram Bot Configuration
TELEGRAM_TOKEN=your_actual_telegram_bot_token_here
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_API_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent

# Database Configuration
DB_HOST=host.docker.internal
DB_PORT=5432
DB_NAME=srh_chatbot_db
DB_USER=postgres
DB_PASSWORD=1234

# Django Configuration
DJANGO_SETTINGS_MODULE=config.settings
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-server-ip,your-domain.com
```

### Update Docker Compose for Production
```bash
cp docker-compose.yml docker-compose.prod.yml
nano docker-compose.prod.yml
```

Update the content to:
```yaml
version: '3.8'

services:
  web:
    build: .
    env_file:
      - .env.production
    volumes:
      - ./logs:/app/logs
      - /opt/srh-chatbot/data:/app/data  # For persistent data
    ports:
      - "8000:8000"
    restart: unless-stopped
    command: python manage.py run_telegram_bot
    extra_hosts:
      - "host.docker.internal:host-gateway"
    healthcheck:
      test: ["CMD", "python", "manage.py", "check"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 🚀 Step 5: Deploy

### Run Deployment
```bash
# Make scripts executable
chmod +x deploy.sh docker-entrypoint.sh

# Build and start the application
./deploy.sh
```

### Alternative: Manual Deployment
```bash
# Build the image
docker build -t srh-chatbot .

# Stop any existing containers
docker-compose -f docker-compose.prod.yml down

# Start the application
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
```

## 🔒 Step 6: Production Security

### Firewall Configuration
```bash
# Ubuntu (UFW)
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 8000  # If you need direct access
sudo ufw allow 80
sudo ufw allow 443

# CentOS (FirewallD)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### SSL/HTTPS Setup (Optional - if using webhook)
```bash
# Install Nginx
sudo apt install -y nginx  # Ubuntu
sudo yum install -y nginx  # CentOS

# Install Certbot for Let's Encrypt
sudo apt install -y certbot python3-certbot-nginx  # Ubuntu
sudo yum install -y certbot python3-certbot-nginx  # CentOS

# Create Nginx configuration
sudo nano /etc/nginx/sites-available/srh-chatbot  # Ubuntu
sudo nano /etc/nginx/conf.d/srh-chatbot.conf      # CentOS
```

Nginx configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site (Ubuntu)
sudo ln -s /etc/nginx/sites-available/srh-chatbot /etc/nginx/sites-enabled/

# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

## 📊 Step 7: Monitoring & Maintenance

### Create Systemd Service (Alternative to Docker)
```bash
sudo nano /etc/systemd/system/srh-chatbot.service
```

```ini
[Unit]
Description=SRH Chatbot Service
After=docker.service postgresql.service
Requires=docker.service postgresql.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/srh-chatbot
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
User=root

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable srh-chatbot
sudo systemctl start srh-chatbot
```

### Monitoring Commands
```bash
# Check application logs
docker-compose -f docker-compose.prod.yml logs -f

# Check container status
docker-compose -f docker-compose.prod.yml ps

# Monitor resource usage
docker stats

# Check database
sudo -u postgres psql -d srh_chatbot_db -c "SELECT COUNT(*) FROM bot_usersession;"
```

### Log Rotation Setup
```bash
sudo nano /etc/logrotate.d/srh-chatbot
```

```
/opt/srh-chatbot/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f /opt/srh-chatbot/docker-compose.prod.yml restart web
    endscript
}
```

## 🔄 Step 8: Updates & Maintenance

### Update Application
```bash
cd /opt/srh-chatbot

# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml down
docker build -t srh-chatbot .
docker-compose -f docker-compose.prod.yml up -d
```

### Backup Database
```bash
# Create backup script
nano /opt/scripts/backup-srh-chatbot.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/backups/srh-chatbot"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
sudo -u postgres pg_dump srh_chatbot_db > $BACKUP_DIR/srh_chatbot_db_$DATE.sql

# Backup application logs
cp -r /opt/srh-chatbot/logs $BACKUP_DIR/logs_$DATE

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "logs_*" -mtime +7 -exec rm -rf {} +

echo "Backup completed: $DATE"
```

```bash
chmod +x /opt/scripts/backup-srh-chatbot.sh

# Add to crontab for daily backups
crontab -e
# Add: 0 2 * * * /opt/scripts/backup-srh-chatbot.sh
```

## ✅ Step 9: Verification

### Check Deployment
```bash
# Verify containers are running
docker ps

# Check application logs
docker-compose -f docker-compose.prod.yml logs -f web

# Test database connection
docker-compose -f docker-compose.prod.yml exec web python manage.py dbshell

# Check bot status (if using polling)
curl -X GET "https://api.telegram.org/bot$TELEGRAM_TOKEN/getMe"
```

### Health Checks
```bash
# Check if bot is responding
docker-compose -f docker-compose.prod.yml exec web python manage.py shell -c "
from telegram import Bot
import asyncio
bot = Bot('$TELEGRAM_TOKEN')
print('Bot info:', asyncio.run(bot.get_me()))
"
```

## 🚨 Troubleshooting

### Common Issues

1. **Container won't start**: Check logs with `docker-compose logs`
2. **Database connection failed**: Verify PostgreSQL is running and accessible
3. **Permission errors**: Check file ownership and Docker group membership
4. **Out of memory**: Increase server RAM or add swap space
5. **Port conflicts**: Change port in docker-compose.yml

### Get Support
- Check logs: `/opt/srh-chatbot/logs/`
- Container logs: `docker-compose logs`
- System logs: `journalctl -u srh-chatbot`

## 📈 Performance Optimization

### For High Traffic
```bash
# Increase Docker memory limits
nano docker-compose.prod.yml

# Add under web service:
deploy:
  resources:
    limits:
      memory: 1G
    reservations:
      memory: 512M

# PostgreSQL tuning
sudo nano /etc/postgresql/*/main/postgresql.conf

# Add:
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

Your SRH chatbot is now ready for production deployment! 🎉

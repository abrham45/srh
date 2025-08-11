# 🚀 Quick Deployment Guide for Linux Server

## 📋 Prerequisites
- Fresh Linux server (Ubuntu 20.04+ recommended)
- Root or sudo access
- 2GB+ RAM, 20GB+ disk space

## ⚡ Quick Deploy (3 Steps)

### Step 1: Prepare Server
```bash
# Upload files to server
scp -r * user@your-server-ip:/opt/srh-chatbot/

# SSH into server
ssh user@your-server-ip

# Run server setup
cd /opt/srh-chatbot
sudo ./setup-server.sh
```

### Step 2: Configure Environment
```bash
# Copy and edit environment file
cp production.env.example .env.production
nano .env.production

# Update these required values:
# TELEGRAM_TOKEN=your_actual_telegram_bot_token
# GEMINI_API_KEY=your_actual_gemini_api_key  
# DB_PASSWORD=your_secure_database_password
```

### Step 3: Deploy Application
```bash
# Deploy the chatbot
./deploy-production.sh
```

## ✅ Verification
```bash
# Check if running
docker-compose -f docker-compose.prod.yml ps

# View logs  
docker-compose -f docker-compose.prod.yml logs -f

# Test bot
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
```

## 🔧 Management Commands

| Action | Command |
|--------|---------|
| **Check Status** | `./scripts/status.sh` |
| **View Logs** | `docker-compose -f docker-compose.prod.yml logs -f` |
| **Restart** | `docker-compose -f docker-compose.prod.yml restart` |
| **Stop** | `docker-compose -f docker-compose.prod.yml down` |
| **Update App** | `./scripts/update.sh` |
| **Backup** | `./scripts/backup.sh` |

## 🚨 Important Security Notes

1. **Change default database password**:
   ```bash
   sudo -u postgres psql -c "ALTER USER srhbot PASSWORD 'your_new_secure_password';"
   ```

2. **Update .env.production** with your actual tokens and secure passwords

3. **Configure firewall** (handled by setup script)

4. **For webhook mode**: Update `nginx.conf` with your domain and SSL certificates

## 📁 File Structure
```
/opt/srh-chatbot/
├── deploy-production.sh     # Main deployment script
├── setup-server.sh          # Server preparation script  
├── docker-compose.prod.yml  # Production Docker config
├── .env.production          # Environment variables
├── logs/                    # Application logs
├── backups/                 # Database backups
└── scripts/                 # Maintenance scripts
```

## 🆘 Troubleshooting

### Container won't start:
```bash
docker-compose -f docker-compose.prod.yml logs
```

### Database connection issues:
```bash
sudo systemctl status postgresql
sudo -u postgres psql -l
```

### Check disk space:
```bash
df -h
docker system prune -f  # Clean unused Docker resources
```

### View system resources:
```bash
htop
docker stats
```

## 📞 Support
- Check logs in `/opt/srh-chatbot/logs/`
- Review container logs: `docker-compose logs`
- Monitor with: `./scripts/status.sh`

---
**Your SRH Chatbot is ready to help users! 🤖💬**

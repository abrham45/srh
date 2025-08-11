# 🚀 Deploy SRH Chatbot to Your Remote Database

## 📋 Your Database Configuration
- **Host**: `164.92.98.189`
- **Port**: `5432`
- **User**: `taskuser`
- **Password**: `taskpassword`
- **Database**: `srh_chatbot_db` (will be created)

## ⚡ One-Command Deployment

```bash
# Deploy the entire chatbot system
./deploy-remote-db.sh
```

**That's it!** This script will:
1. ✅ Test connection to your PostgreSQL server
2. ✅ Install Docker (if needed)
3. ✅ Create the database (if needed)
4. ✅ Set up environment configuration
5. ✅ Build and deploy the application
6. ✅ Run database migrations
7. ✅ Perform health checks

## 🔧 What You Need to Provide

The script will prompt you to enter:
1. **Telegram Bot Token** (from @BotFather)
2. **Gemini API Key** (from Google AI Studio)

## 📊 Architecture

```
🖥️  Your Linux Server
├── 🐳 Docker Containers:
│   ├── 📱 SRH Chatbot (Web App)
│   └── ⚡ Redis (Cache)
└── 🌐 Remote PostgreSQL
    └── 🗄️  164.92.98.189:5432
        └── 📂 srh_chatbot_db
```

## ✅ After Deployment

### Check Everything is Running:
```bash
# View container status
docker-compose -f docker-compose.prod.yml ps

# View application logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Test Your Bot:
```bash
# Replace YOUR_TOKEN with actual token
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
```

### Access Database:
```bash
# Connect to your database
PGPASSWORD='taskpassword' psql -h 164.92.98.189 -p 5432 -U taskuser -d srh_chatbot_db

# View tables
\dt

# Check user sessions
SELECT COUNT(*) FROM bot_usersession;
```

## 🛠️ Management Commands

| Action | Command |
|--------|---------|
| **View Logs** | `docker-compose -f docker-compose.prod.yml logs -f` |
| **Restart App** | `docker-compose -f docker-compose.prod.yml restart web` |
| **Stop All** | `docker-compose -f docker-compose.prod.yml down` |
| **Update App** | `git pull && docker build -t srh-chatbot . && docker-compose -f docker-compose.prod.yml up -d` |
| **Backup DB** | `PGPASSWORD='taskpassword' pg_dump -h 164.92.98.189 -U taskuser srh_chatbot_db > backup.sql` |

## 🚨 Important Files

- **`.env.production`** - Your configuration (tokens, database settings)
- **`docker-compose.prod.yml`** - Container orchestration
- **`logs/`** - Application logs
- **`backups/`** - Database backups

## 🔍 Troubleshooting

### Can't connect to database:
```bash
# Test connection manually
PGPASSWORD='taskpassword' pg_isready -h 164.92.98.189 -p 5432 -U taskuser
```

### Container won't start:
```bash
# Check detailed logs
docker-compose -f docker-compose.prod.yml logs web
```

### Bot not responding:
```bash
# Test bot token
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
```

## 📈 What You Get

✅ **Complete AI Analysis System**:
- Intent Classification (5th, 10th, 20th conversations...)
- Emotion Detection (5th, 20th, 80th conversations...)
- Risk Assessment (3rd, 6th, 12th conversations...)

✅ **Full FAQ System**:
- 6 categories (Pregnancy, Menstruation, Contraception, STIs, Puberty, Relationships)
- Multilingual (English & Amharic)

✅ **Advanced Features**:
- Automatic location detection (Ethiopian regions)
- Therapeutic communication style
- Medication safety guidelines
- SRH scope restrictions

✅ **Production Ready**:
- Health checks and auto-restart
- Log rotation and management
- Backup automation
- Performance optimization

## 🎉 Your Bot Features

Your users will experience:
- **Smart conversations** with therapeutic tone
- **Comprehensive FAQ** system
- **Location-aware** responses for Ethiopia
- **Safety monitoring** with risk assessment
- **Multilingual** support (English/Amharic)
- **Educational medication** information with disclaimers

---

**Ready to deploy? Run: `./deploy-remote-db.sh`** 🚀

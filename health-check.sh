#!/bin/bash

echo "🩺 SRH Chatbot Health Check"
echo "==========================="

# Function to check service status
check_service() {
    local service_name=$1
    local check_command=$2
    local description=$3
    
    echo -n "🔍 Checking $service_name... "
    if eval "$check_command" > /dev/null 2>&1; then
        echo "✅ $description"
        return 0
    else
        echo "❌ $description"
        return 1
    fi
}

# Check Docker
check_service "Docker" "docker info" "Docker daemon is running"

# Check PostgreSQL (if running locally)
if command -v psql >/dev/null 2>&1; then
    check_service "PostgreSQL" "psql -h localhost -U postgres -d srh_chatbot_db -c 'SELECT 1;'" "PostgreSQL database accessible"
else
    echo "⚠️  PostgreSQL client not found, skipping database check"
fi

# Check if Docker containers are running
if docker info > /dev/null 2>&1; then
    echo ""
    echo "📊 Docker Container Status:"
    if docker-compose ps 2>/dev/null | grep -q "Up"; then
        docker-compose ps
        echo ""
        
        # Check application health
        echo "🩺 Application Health:"
        if docker-compose exec -T web python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.db import connection
try:
    connection.ensure_connection()
    print('✅ Database connection from container: OK')
except Exception as e:
    print(f'❌ Database connection from container: FAILED - {e}')
" 2>/dev/null; then
            echo "✅ Application can connect to database"
        else
            echo "❌ Application cannot connect to database"
        fi
        
        # Check if bot command is available
        if docker-compose exec -T web python manage.py help run_telegram_bot > /dev/null 2>&1; then
            echo "✅ Telegram bot command available"
        else
            echo "❌ Telegram bot command not available"
        fi
        
    else
        echo "❌ No containers are running"
        echo "   Run: docker-compose up -d"
    fi
else
    echo "⚠️  Docker not running, skipping container checks"
fi

echo ""
echo "📋 Summary:"
echo "   📁 Project: SRH Chatbot"
echo "   🗄️  Database: PostgreSQL (host)"
echo "   🐳 Container: Django app"
echo "   🤖 Bot: Telegram + Gemini AI"
echo ""
echo "🚀 To start: ./deploy.sh"
echo "📝 To view logs: docker-compose logs -f" 
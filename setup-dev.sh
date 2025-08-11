#!/bin/bash

echo "🔧 SRH Chatbot Development Setup"
echo "================================"

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "🐍 Python version: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check PostgreSQL connection (development)
echo "🔍 Checking database connection..."
python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.db import connection
try:
    connection.ensure_connection()
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    print('   Make sure PostgreSQL is running and database exists')
"

# Run migrations
echo "🗄️ Running database migrations..."
python manage.py migrate

# Check if everything is working
echo "🧪 Running system check..."
python manage.py check

echo ""
echo "✅ Development setup complete!"
echo ""
echo "🚀 To run the bot:"
echo "   source venv/bin/activate"
echo "   python manage.py run_telegram_bot"
echo ""
echo "🔧 For Docker deployment:"
echo "   ./deploy.sh" 
#!/bin/bash

echo "🚀 SRH Chatbot Docker Deployment Script"
echo "======================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if PostgreSQL is running on host (if pg_isready is available)
echo "🔍 Checking host PostgreSQL..."
if command -v pg_isready >/dev/null 2>&1; then
    if pg_isready -h localhost -p 5432 -U postgres -q 2>/dev/null; then
        echo "✅ PostgreSQL is running on host"
    else
        echo "❌ PostgreSQL is not running on host. Please start PostgreSQL first."
        echo "   Make sure PostgreSQL is running on localhost:5432"
        exit 1
    fi
else
    echo "⚠️  pg_isready not found. Assuming PostgreSQL is running on localhost:5432"
    echo "   Please ensure PostgreSQL is running before continuing..."
    echo "   Press Enter to continue or Ctrl+C to cancel..."
    read -r
fi

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -t srh-chatbot .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

# Stop existing container if running
echo "🛑 Stopping existing container..."
docker-compose down 2>/dev/null || true

# Start the application
echo "🚀 Starting SRH Chatbot..."
docker-compose up -d

if [ $? -eq 0 ]; then
    echo "✅ SRH Chatbot is now running!"
    echo ""
    echo "📊 Container Status:"
    docker-compose ps
    echo ""
    echo "📝 To view logs: docker-compose logs -f"
    echo "🛑 To stop: docker-compose down"
    echo "🔄 To restart: docker-compose restart"
    echo ""
    echo "🔗 The bot will connect to PostgreSQL at localhost:5432"
    echo "   Make sure your database 'srh_chatbot_db' exists"
else
    echo "❌ Failed to start the application"
    exit 1
fi 
#!/bin/bash

# AI Society D&D - Setup Script
# ==============================
# This script helps you get started quickly

set -e

echo "=================================="
echo "AI Society D&D - Setup Script"
echo "=================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "   Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "✓ Docker found"

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed!"
    echo "   Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✓ Docker Compose found"

# Check if .env exists
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your OpenAI API key!"
    echo "   Run: nano .env"
    echo "   Add: OPENAI_API_KEY=sk-your-key-here"
    echo ""
    read -p "Press Enter when you've added your API key..."
fi

# Check if API key is set
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo ""
    echo "⚠️  Warning: OpenAI API key may not be set correctly in .env"
    echo "   Make sure it starts with 'sk-'"
    echo ""
fi

echo ""
echo "🐳 Starting Docker services..."
echo ""

# Start services
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo "✓ Services are running!"
else
    echo "❌ Services failed to start"
    echo "   Check logs: docker-compose logs"
    exit 1
fi

echo ""
echo "🔍 Checking API health..."

# Try to hit the health endpoint
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✓ API is healthy!"
else
    echo "⚠️  API is starting up... (this is normal)"
    echo "   Give it a few more seconds"
fi

echo ""
echo "=================================="
echo "✅ Setup Complete!"
echo "=================================="
echo ""
echo "🎮 What to do next:"
echo ""
echo "1. Run the demo:"
echo "   python3 demo.py"
echo ""
echo "2. Try the API:"
echo "   curl http://localhost:8000/health"
echo ""
echo "3. Create a campaign:"
echo "   curl -X POST http://localhost:8000/campaigns/create \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"campaign_name\": \"Test\", \"dm_id\": \"me\"}'"
echo ""
echo "4. View logs:"
echo "   docker-compose logs -f"
echo ""
echo "5. Stop services:"
echo "   docker-compose down"
echo ""
echo "📚 Documentation:"
echo "   • START_HERE.md - Overview"
echo "   • QUICKSTART.md - Quick commands"
echo "   • README.md - Full documentation"
echo ""
echo "🚀 Your D&D system is ready to use!"
echo "=================================="

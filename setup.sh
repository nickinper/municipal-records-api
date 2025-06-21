#!/bin/bash
# Municipal Records Processing - Quick Setup Script

echo "🚀 Municipal Records Processing - Setup"
echo "======================================"
echo ""
echo "This script will help you set up:"
echo "1. Database and Redis (via Docker)"
echo "2. Python environment"
echo "3. Stripe configuration"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Docker
echo "🐳 Checking Docker..."
if command_exists docker && command_exists docker-compose; then
    echo -e "${GREEN}✓ Docker found${NC}"
    
    # Start services
    echo "Starting PostgreSQL and Redis..."
    docker-compose up -d
    
    # Wait for services
    echo "Waiting for services to be ready..."
    sleep 5
else
    echo -e "${RED}✗ Docker not found${NC}"
    echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check Python
echo ""
echo "🐍 Checking Python environment..."
if [ -d "venv" ]; then
    echo -e "${GREEN}✓ Virtual environment found${NC}"
else
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv and install dependencies
echo "Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt -q

# Check if .env exists
if [ ! -f .env ]; then
    echo ""
    echo "📄 Creating .env file from template..."
    cat > .env << 'EOF'
# Database
DATABASE_URL=postgresql+asyncpg://municipal_user:secure_password@localhost:5432/municipal_records

# Redis
REDIS_URL=redis://localhost:6379/0

# Stripe keys
STRIPE_SECRET_KEY=sk_test_YOUR_KEY_HERE
STRIPE_PUBLISHABLE_KEY=pk_test_YOUR_KEY_HERE
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET_HERE

# Anthropic
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE

# App settings
BASE_URL=http://localhost:8000
DEBUG=True
LOG_LEVEL=INFO
EOF
fi

# Run database migrations
echo ""
echo "🗄️  Setting up database..."
python -c "
import asyncio
from main import lifespan
from fastapi import FastAPI

app = FastAPI()

async def setup_db():
    async with lifespan(app):
        print('✓ Database tables created')

asyncio.run(setup_db())
" 2>/dev/null

# Stripe setup
echo ""
echo "💳 Stripe Configuration"
echo "Do you want to configure Stripe now? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    python scripts/setup_stripe.py
else
    echo "You can run 'python scripts/setup_stripe.py' later to configure Stripe"
fi

# Final instructions
echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the server:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "API will be available at:"
echo "  http://localhost:8000"
echo "  http://localhost:8000/docs (interactive docs)"
echo ""
echo "To stop services:"
echo "  docker-compose down"
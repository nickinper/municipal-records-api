#!/bin/bash
# Setup script for Municipal Records Processing API

echo "🚀 Municipal Records Processing - Development Setup"
echo "================================================"

# Check for Python 3.11
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [[ ! "$python_version" == "$required_version"* ]]; then
    echo "❌ Error: Python 3.11 is required. Found: $python_version"
    exit 1
fi
echo "✅ Python $python_version found"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "✅ Virtual environment created"

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✅ Dependencies installed"

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium
playwright install-deps chromium
echo "✅ Playwright browsers installed"

# Check for .env file
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration"
else
    echo "✅ .env file exists"
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p screenshots logs
echo "✅ Directories created"

# Check Docker
if command -v docker &> /dev/null; then
    echo "✅ Docker is installed"
    
    read -p "Start PostgreSQL and Redis with Docker? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Starting services..."
        docker-compose up -d postgres redis
        echo "✅ Services started"
        
        # Wait for PostgreSQL to be ready
        echo "Waiting for PostgreSQL to be ready..."
        sleep 5
        
        # Run migrations
        echo "Running database migrations..."
        python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from proprietary.database.models import Base

async def create_tables():
    engine = create_async_engine('postgresql+asyncpg://municipal_user:secure_password@localhost:5432/municipal_records')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(create_tables())
"
        echo "✅ Database initialized"
    fi
else
    echo "⚠️  Docker not found. Please install Docker for local development"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Stripe keys"
echo "2. Run: source venv/bin/activate"
echo "3. Run: python main.py"
echo "4. Visit: http://localhost:8000/docs"
echo ""
echo "For production deployment:"
echo "- Railway: railway up"
echo "- Docker: docker-compose up"
echo ""
echo "Happy coding! 🎉"
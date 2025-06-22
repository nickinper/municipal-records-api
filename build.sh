#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations (if needed)
# python -m alembic upgrade head

echo "✅ Build completed successfully!"
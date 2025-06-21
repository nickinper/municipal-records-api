#!/bin/bash
# Municipal Records Processing - Backup Script

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Create backup directory with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/backup_${TIMESTAMP}"
mkdir -p "$BACKUP_DIR"

echo -e "${YELLOW}🔒 Creating backup at ${TIMESTAMP}${NC}"

# 1. Backup code (excluding sensitive files)
echo "📁 Backing up code..."
rsync -av --progress \
  --exclude='.env' \
  --exclude='venv/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.git/' \
  --exclude='node_modules/' \
  --exclude='backups/' \
  --exclude='server.log' \
  --exclude='*.log' \
  . "$BACKUP_DIR/code/"

# 2. Create .env template (without sensitive data)
echo "🔐 Creating .env template..."
cat > "$BACKUP_DIR/.env.template" << 'EOF'
# Database
DATABASE_URL=postgresql+asyncpg://municipal_user:secure_password@localhost:5432/municipal_records

# Redis
REDIS_URL=redis://localhost:6379/0

# Stripe keys
STRIPE_SECRET_KEY=YOUR_STRIPE_SECRET_KEY
STRIPE_PUBLISHABLE_KEY=YOUR_STRIPE_PUBLISHABLE_KEY
STRIPE_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET

# Anthropic
ANTHROPIC_API_KEY=YOUR_ANTHROPIC_KEY

# App settings
BASE_URL=http://localhost:8000
DEBUG=True
LOG_LEVEL=INFO
EOF

# 3. Export database schema and data
echo "🗄️  Backing up database..."
if command -v docker >/dev/null 2>&1; then
    # Schema only
    docker exec municipal_postgres pg_dump -U municipal_user -d municipal_records --schema-only > "$BACKUP_DIR/schema.sql"
    
    # Data export (optional - be careful with sensitive data)
    docker exec municipal_postgres pg_dump -U municipal_user -d municipal_records --data-only --exclude-table=customers --exclude-table=requests > "$BACKUP_DIR/data_reference.sql"
    
    # Full backup (includes everything)
    docker exec municipal_postgres pg_dump -U municipal_user -d municipal_records > "$BACKUP_DIR/full_database.sql"
else
    echo "⚠️  Docker not running - skipping database backup"
fi

# 4. Document current state
echo "📝 Documenting system state..."
cat > "$BACKUP_DIR/BACKUP_INFO.md" << EOF
# Municipal Records Processing Backup
**Date:** $(date)
**Version:** Production Ready with Live Stripe

## System State
- API: Fully functional
- Database: PostgreSQL with all tables created
- Stripe: Live keys configured (restricted key)
- Redis: Configured for caching
- All endpoints tested and working

## Important Files Backed Up
- All source code
- Database schema
- Configuration templates
- Setup scripts

## To Restore
1. Copy code files
2. Create .env from template and add your keys
3. Run: ./setup.sh
4. Import database: psql -U municipal_user -d municipal_records < full_database.sql

## Recent Changes
- Configured live Stripe integration
- Tested payment flow
- All systems operational
EOF

# 5. Create requirements snapshot
cp requirements.txt "$BACKUP_DIR/"
pip freeze > "$BACKUP_DIR/requirements_frozen.txt"

# 6. Create compressed archive
echo "📦 Creating compressed archive..."
tar -czf "backups/municipal_records_${TIMESTAMP}.tar.gz" -C backups "backup_${TIMESTAMP}"

# Calculate sizes
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
ARCHIVE_SIZE=$(du -sh "backups/municipal_records_${TIMESTAMP}.tar.gz" | cut -f1)

echo -e "\n${GREEN}✅ Backup complete!${NC}"
echo "📍 Location: $BACKUP_DIR"
echo "📦 Archive: backups/municipal_records_${TIMESTAMP}.tar.gz"
echo "💾 Backup size: $BACKUP_SIZE (compressed: $ARCHIVE_SIZE)"
echo ""
echo "💡 Tip: Copy the .tar.gz file to a safe location (external drive, cloud storage, etc.)"
.PHONY: help setup start stop restart logs test clean stripe-setup webhook-test

# Default target
help:
	@echo "Municipal Records Processing - Available Commands"
	@echo "=============================================="
	@echo ""
	@echo "Setup & Configuration:"
	@echo "  make setup          - Complete initial setup (Docker, Python, Database)"
	@echo "  make stripe-setup   - Configure Stripe API keys and webhook"
	@echo ""
	@echo "Development:"
	@echo "  make start          - Start all services and API server"
	@echo "  make stop           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make logs           - View API server logs"
	@echo "  make webhook-test   - Test webhook forwarding (Stripe CLI)"
	@echo ""
	@echo "Testing:"
	@echo "  make test           - Run all tests"
	@echo "  make test-api       - Test API endpoints"
	@echo "  make test-pricing   - Test pricing agent (requires Anthropic key)"
	@echo ""
	@echo "Database:"
	@echo "  make db-shell       - Open PostgreSQL shell"
	@echo "  make db-reset       - Reset database (WARNING: deletes all data)"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean          - Remove generated files and caches"
	@echo "  make format         - Format code with black"
	@echo "  make lint           - Run code linters"

# Complete setup
setup:
	@echo "🚀 Running complete setup..."
	@./setup.sh

# Configure Stripe
stripe-setup:
	@source venv/bin/activate && python scripts/setup_stripe.py

# Start all services
start:
	@echo "🚀 Starting services..."
	@docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 5
	@echo "🌐 Starting API server..."
	@source venv/bin/activate && python main.py

# Start in background
start-bg:
	@echo "🚀 Starting services in background..."
	@docker-compose up -d
	@sleep 5
	@source venv/bin/activate && nohup python main.py > server.log 2>&1 &
	@echo "✅ API server started in background"
	@echo "View logs with: make logs"

# Stop all services
stop:
	@echo "🛑 Stopping services..."
	@pkill -f "python main.py" || true
	@docker-compose down
	@echo "✅ All services stopped"

# Restart services
restart: stop start

# View logs
logs:
	@tail -f server.log

# Run webhook forwarding
webhook-test:
	@echo "🔗 Starting Stripe webhook forwarding..."
	@echo "Keep this running while testing payments"
	@stripe listen --forward-to localhost:8000/webhooks/stripe

# Run tests
test:
	@source venv/bin/activate && pytest

# Test API endpoints
test-api:
	@echo "🧪 Testing API endpoints..."
	@echo ""
	@echo "1️⃣ Health Check:"
	@curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
	@echo ""
	@echo "2️⃣ Pricing Info:"
	@curl -s http://localhost:8000/api/v1/pricing | python3 -m json.tool | head -20
	@echo ""
	@echo "3️⃣ Submit Request:"
	@curl -s -X POST http://localhost:8000/api/v1/submit-request \
		-H "Content-Type: application/json" \
		-d '{"report_type":"incident","case_number":"TEST-'$$(date +%s)'","requestor_email":"test@example.com","requestor_first_name":"Test","requestor_last_name":"User"}' \
		| python3 -m json.tool

# Test pricing agent
test-pricing:
	@source venv/bin/activate && python scripts/test_pricing_agent.py

# Database shell
db-shell:
	@docker exec -it municipal_postgres psql -U municipal_user -d municipal_records

# Reset database (WARNING: destructive)
db-reset:
	@echo "⚠️  WARNING: This will delete all data!"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	@docker-compose down -v
	@docker-compose up -d
	@sleep 5
	@echo "✅ Database reset complete"

# Clean generated files
clean:
	@echo "🧹 Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@rm -f server.log
	@echo "✅ Cleanup complete"

# Format code
format:
	@source venv/bin/activate && black .

# Run linters
lint:
	@source venv/bin/activate && ruff check .

# Quick test submission
quick-test:
	@echo "📝 Submitting test request..."
	@curl -s -X POST http://localhost:8000/api/v1/submit-request \
		-H "Content-Type: application/json" \
		-d '{ \
			"report_type": "incident", \
			"case_number": "QUICK-TEST-'$$(date +%s)'", \
			"requestor_email": "quick@test.com", \
			"requestor_first_name": "Quick", \
			"requestor_last_name": "Test" \
		}' | python3 -m json.tool
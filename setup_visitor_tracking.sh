#!/bin/bash
# setup_visitor_tracking.sh
# Initialize visitor tracking feature

echo "🚀 Setting up Visitor Tracking..."

# 1. Install dependencies
echo "📦 Installing httpx..."
pip install httpx

# 2. Create database migration
echo "🗄️  Creating database migration..."
cd backend
alembic revision --autogenerate -m "add visitor tracking table"

# 3. Apply migration
echo "📝 Applying migration..."
alembic upgrade head

# 4. Test API endpoints
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Start the API: uvicorn backend.api:app --reload"
echo "2. Track a visitor: curl -X POST http://localhost:8000/api/track/visitor"
echo "3. View analytics: curl -H 'Authorization: Bearer YOUR_TOKEN' http://localhost:8000/api/visitors/analytics"
echo ""
echo "📖 Documentation: backend/VISITOR_TRACKING.md"

#!/bin/bash
# Setup script for Enterprise Document Intelligence Platform

echo "🚀 Enterprise Document Intelligence Platform - Setup"
echo "=================================================="

# Check Python version
echo "📌 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python version: $python_version"

# Check PostgreSQL
echo "📌 Checking PostgreSQL..."
if command -v psql &> /dev/null; then
    echo "✅ PostgreSQL is installed"
else
    echo "⚠️  PostgreSQL not found. Please install PostgreSQL 14+"
    echo "   macOS: brew install postgresql@14"
    exit 1
fi

# Create virtual environment
echo "📌 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "✅ Virtual environment created"

# Install backend dependencies
echo "📌 Installing backend dependencies..."
cd backend
pip install --upgrade pip
pip install -r requirements.txt
cd ..
echo "✅ Backend dependencies installed"

# Install frontend dependencies
echo "📌 Installing frontend dependencies..."
cd frontend
pip install -r requirements.txt
cd ..
echo "✅ Frontend dependencies installed"

# Setup environment file
echo "📌 Setting up environment variables..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file from template"
    echo "⚠️  Please edit .env and add your API keys:"
    echo "   - OPENAI_API_KEY"
    echo "   - DATABASE_URL"
else
    echo "✅ .env file already exists"
fi

# Create directories
echo "📌 Creating directories..."
mkdir -p uploads
mkdir -p logs
mkdir -p chromadb_data
echo "✅ Directories created"

# Setup database
echo "📌 Database setup..."
read -p "Do you want to create the database now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter database name (default: docdb): " dbname
    dbname=${dbname:-docdb}
    
    echo "Creating database: $dbname"
    createdb $dbname 2>/dev/null || echo "Database may already exist"
    
    echo "Running schema..."
    psql $dbname < database/schema.sql
    echo "✅ Database schema created"
fi

echo ""
echo "=================================================="
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Start backend: cd backend && uvicorn main:app --reload"
echo "3. Start frontend: cd frontend && streamlit run app.py"
echo ""
echo "📚 Documentation: See README.md"
echo "=================================================="

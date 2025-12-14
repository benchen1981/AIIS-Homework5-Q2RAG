# Demo Mode - Quick Start Guide

## 🎉 Demo Mode is Running!

Your Enterprise Document Intelligence Platform is now running in **DEMO MODE** without requiring PostgreSQL.

### 🌐 Access Points

- **Frontend UI**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### ✅ What Works in Demo Mode

1. **Document Upload** ✅
   - Upload PDF, DOCX, TXT files
   - Files are stored in `./uploads` directory
   - Basic metadata tracking

2. **Document Management** ✅
   - List all uploaded documents
   - View document details
   - Delete documents
   - Filter by status and type

3. **System Statistics** ✅
   - Total documents count
   - Upload tracking
   - System health monitoring

4. **Web Interface** ✅
   - Multi-page Streamlit UI
   - Home, Upload, Search, Admin pages
   - Real-time API health check

### ⚠️ Limitations in Demo Mode

1. **No AI Processing** ❌
   - Text extraction disabled (requires OpenAI API)
   - Metadata extraction disabled
   - No semantic search
   - No RAG query answering

2. **In-Memory Storage** ⚠️
   - Data is lost when server restarts
   - No persistent database
   - Limited to single server instance

3. **Mock Responses** ℹ️
   - Search queries return demo responses
   - No real document analysis

### 🚀 Upgrade to Full Version

When you're ready for full functionality:

```bash
# 1. Install PostgreSQL
brew install postgresql@14
brew services start postgresql@14

# 2. Create database
createdb docdb
psql docdb < database/schema.sql

# 3. Set OpenAI API key in .env
OPENAI_API_KEY=sk-your-actual-key-here

# 4. Start full version
cd backend
python3 -m uvicorn main:app --reload
```

### 📝 Current Server Status

**Backend (Port 8000)**
- Status: ✅ Running
- Mode: Demo (In-Memory)
- Health: http://localhost:8000/api/health

**Frontend (Port 8501)**
- Status: ✅ Running
- URL: http://localhost:8501

### 🛑 To Stop Servers

Press `Ctrl+C` in the terminal windows where the servers are running.

### 📚 Next Steps

1. **Try uploading a document** - Go to the Upload page
2. **View documents** - Check the Admin dashboard
3. **Test search** - Try a query (will show demo response)
4. **Explore API** - Visit http://localhost:8000/docs

When you're satisfied with the demo and want full AI capabilities, follow the upgrade steps above!

---

**Note**: This demo mode allows you to evaluate the user interface and basic functionality without setting up a database or AI services.

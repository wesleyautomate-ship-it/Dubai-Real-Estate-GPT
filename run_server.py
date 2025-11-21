"""
Dubai Real Estate Search API Server Launcher
"""

import uvicorn
from backend.config import API_HOST, API_PORT

if __name__ == "__main__":
    print("=" * 70)
    print("🏠 Dubai Real Estate Semantic Search API")
    print("=" * 70)
    print(f"\n📡 Starting server at http://{API_HOST}:{API_PORT}")
    print(f"📚 API Documentation: http://{API_HOST}:{API_PORT}/api/docs")
    print(f"🔍 Search UI: http://{API_HOST}:{API_PORT}/")
    print("\n" + "=" * 70 + "\n")
    
    uvicorn.run(
        "backend.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info"
    )


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from routers import projects
load_dotenv()
from routers import users
from database import supabase


app = FastAPI(
    title = "AI Engineering API",
    description = "Backend API for Six-Figure AI Engineering application",
    version ="1.0.0"
)

app.include_router(projects.router)

#configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

#HEALTH check endpoints

# Health check endpoints
@app.get("/")
async def root():
    return("AI Engineering app is running!")

@app.get("/health")
async def health_check():
    return {
    "status": "healthy",
    "version": "1.0.0"}

@app.get("/posts")
async def get_all_posts():
    """Get all blog posts"""
    try:
        result = supabase.table("posts").select("*").order("created_at", desc=True).execute()
        return result.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




if __name__ == "__main__":
    import uvicorn
    uvicorn. run(app, host="0.0.0.0", port=8000, reload=True)



from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from routers import users, projects, files,chats
from database import supabase
from dotenv import load_dotenv

load_dotenv()



app = FastAPI(
    title = "AI Engineering API",
    description = "Backend API for Six-Figure AI Engineering application",
    version ="1.0.0"
)

app.include_router(projects.router)
app.include_router(files.router)
app.include_router(chats.router)

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

@app.post("/create-user")
async def clerk_webhook(webhook_data: dict):
    try:
        # Get the event type and user data from the webhook payload
        event_type = webhook_data.get("type")

        if event_type == "user.created":
            user_data = webhook_data.get("data", {})
            clerk_id = user_data.get("id")

        if not clerk_id:
            raise HTTPException(status_code=400, detail="Invalid webhook payload: missing user ID")

        existing = supabase.table("users").select("id").eq("clerk_id", clerk_id).execute()

        if existing.data:
            return {"message": "User already exists"}

        result = supabase.table("users").insert({
            "clerk_id": clerk_id
        }).execute()

        return  {
            "message": "User created successfully",
            "data": result.data[0]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn. run(app, host="0.0.0.0", port=8000, reload=True)


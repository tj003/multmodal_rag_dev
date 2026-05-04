
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.routes.userRoutes import router as userRoutes
from src.routes.projectRoutes import router as projectRoutes
from src.routes.projectFilesRoutes import router as projectFilesRoutes
from src.routes.chatRoutes import router as chatRoutes


app = FastAPI(
    title = "AI Engineering API",
    description = "Backend API for Six-Figure AI Engineering application",
    version ="1.0.0"
)

app.include_router(userRoutes, prefix="/api/user")
app.include_router(projectRoutes, prefix="/api/projects")
app.include_router(projectFilesRoutes, prefix="/api/projects")
app.include_router(chatRoutes, prefix="/api/chats")

#configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
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



if __name__ == "__main__":
    import uvicorn
    uvicorn. run(app, host="0.0.0.0", port=8000, reload=True)


import structlog 
from fastapi import FastAPI

#configure structlog
structlog.configure(
    processors = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

app = FastAPI()

@app.get("/")
async def root():
    logger.info("root_endpoint_called")
    return {"message": "Hello World"}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    logger.info("user_endpoint_called", user_id=user_id)
    return {"user_id": user_id, "name": "John Doe"}
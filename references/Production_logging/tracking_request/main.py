import structlog 
from fastapi import FastAPI
import uuid 
structlog.configure(
    processors = [
        structlog.contextvars.merge_contextvars,# Merges context from contextvars
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger(__name__)

app = FastAPI()

def validate_user():
    logger.info("validating_user")  # Notice: no user_id needed!
    return True

def fetch_from_db():
    logger.info("fetching_from_database")  # No user_id here either!
    return {"name": "John"}

@app.get("/users/{user_id}")
async def get_user(user_id: int):
    request_id = str(uuid.uuid4())

    structlog.contextvars.clear_contextvars()# clear any prevous context
    structlog.contextvars.bind_contextvars(user_id=user_id, request_id=request_id)

    logger.info("request received")
    validate_user()
    data  = fetch_from_db()
    logger.info("returning data")
    return data
import structlog
from fastapi import FastAPI, Request
import uuid

# Configure structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,  # Merges context from contextvars
        structlog.processors.add_log_level,  # Add log level to each log
        structlog.processors.TimeStamper(fmt="iso"),  # Add timestamp
        structlog.processors.JSONRenderer()  # Output as JSON
    ]
)

logger = structlog.get_logger(__name__)
# Create FastAPI app
app = FastAPI()

#THe middleware
@app.middleware("http")
async def logging_middleware(request:Request, call_next):
    # Clear old context
    structlog.contextvars.clear_contextvars()
     # Generate request ID
    request_id = str(uuid.uuid4())
    
    # Bind context that applies to ALL requests
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path
    )
    
    logger.info("request_started")
    
    # Process the request
    response = await call_next(request)
    
    logger.info("request_completed", status_code=response.status_code)
    
    return response

def validate_user():
    logger.info("validating_user")  # Notice: no user_id needed!
    return True

def fetch_from_db():
    logger.info("fetching_from_database")  # No user_id here either!
    return {"name": "John"}

@app.get("/users/{user_id}")
async def get_user(user_id: int):

    # Bind context to contextvars - affects ALL loggers in this request  
    structlog.contextvars.bind_contextvars(user_id=user_id)

    logger.info("request_received")
    validate_user()
    data = fetch_from_db()
    logger.info("returning_data")
    return data

# Run the server when script is executed
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
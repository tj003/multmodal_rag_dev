from fastapi import FastAPI
import time
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def fake_llm():
    text  = "This is a fake LLM response that is being streamed back to the client."
    for word in text.split():
        yield word + " "
        time.sleep(0.3)

@app.get("/stream")
def stream():
    return StreamingResponse(fake_llm(), media_type="text/plain")

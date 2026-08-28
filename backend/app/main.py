from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import upload
from app.routers import chat
app.include_router(chat.router)

app = FastAPI(
    title="AI Data Scientist Platform",
    description="Upload any dataset, chat with it, get analysis and predictions.",
    version="0.1.0",
)

# Allow frontend (React/Streamlit) to call this API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api/v1", tags=["upload"])


@app.get("/")
def health_check():
    return {"status": "ok", "message": "AI Data Scientist backend running"}

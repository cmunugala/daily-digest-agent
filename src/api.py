from fastapi import FastAPI
from pydantic import BaseModel

from src.agent import run_daily_digest_workflow
from src.database import init_db

# Initialize database
init_db()

# --- API ---
app = FastAPI(
    title="Daily Digest Agent API",
    description="Endpoints for generating personalized news digests.",
    version="0.1.0",
)


# --- Models ---
class DigestRequest(BaseModel):
    username: str
    user_question: str


class DigestResponse(BaseModel):
    digest: str


# --- Endpoints ---
@app.get("/", tags=["General"])
def get_root():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/digest", tags=["Agent"], response_model=DigestResponse)
def create_digest(request: DigestRequest):
    """
    Runs the daily digest workflow to research a topic and generate a summary.
    """
    digest = run_daily_digest_workflow(request.username, request.user_question)
    return {"digest": digest}

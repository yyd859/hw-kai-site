import sys
import os

# Ensure backend dir is in path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from agent.chat_agent import process_message, get_or_create_session
from agent.planner import select_recipe
from agent.generator import generate_output
from agent.validator import validate_output

app = FastAPI(title="HW-KAI Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response Models ───────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    message: str
    action: str = "chat"


class Spec(BaseModel):
    object: Optional[str] = None
    trigger: Optional[str] = None
    needs_light: bool = False
    needs_sound: bool = False
    needs_display: bool = False
    needs_sensor: bool = False
    sensor_type: Optional[str] = None
    extra_notes: Optional[str] = None


class GenerateRequest(BaseModel):
    session_id: str
    spec: dict


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    return await process_message(req.session_id, req.message)


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    spec = req.spec

    # Select recipe based on spec
    recipe = select_recipe(spec)
    if not recipe:
        return {
            "error": "暂不支持该需求，请描述更简单的功能（如：按钮控制LED）",
            "validation": {"passed": False, "warnings": [], "errors": ["未找到匹配方案"]}
        }

    # Generate output
    output = generate_output(recipe)

    # Validate
    result = validate_output(output)
    return result

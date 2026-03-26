import os
import sys
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.chat_agent import process_message
from agent.generator import GenerationNotSupportedError, generate_output
from agent.module_selector import MissingComponentsError, select_modules
from agent.pin_allocator import PinAllocationError, allocate_pins

app = FastAPI(title="HW-KAI Agent API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    needs_actuator: bool = False
    actuator_type: Optional[str] = None
    extra_notes: Optional[str] = None


class GenerateRequest(BaseModel):
    session_id: str
    spec: dict[str, Any]


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    return await process_message(req.session_id, req.message)


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    spec = req.spec

    try:
        selection = select_modules(spec)
        hardware_plan = allocate_pins(selection["board"], selection["selected_modules"])
        return generate_output(selection["board"], selection["selected_modules"], hardware_plan, spec)
    except MissingComponentsError as exc:
        return {
            "error": "当前库里缺少可满足需求的模块",
            "error_type": "missing_components",
            "missing_capabilities": exc.missing_capabilities,
        }
    except GenerationNotSupportedError as exc:
        return {
            "error": "当前模块组合暂时还不能自动生成代码",
            "error_type": exc.error_type,
            "selected_module_ids": exc.module_ids,
        }
    except PinAllocationError as exc:
        return {
            "error": str(exc),
            "error_type": "pin_allocation_failed",
        }

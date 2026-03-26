import os
import sys
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.generator import GenerationNotSupportedError, generate_output
from agent.module_selector import MissingComponentsError, select_modules
from agent.pin_allocator import PinAllocationError, allocate_pins
from runtime.chat_runtime import process_chat_message
from runtime.tool_registry import build_plan_from_context, preflight_build_context

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
    return await process_chat_message(req.session_id, req.message)


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    spec = req.spec

    try:
        if any(key in spec for key in ["project_brief", "requirements", "selected_module_ids", "capabilities", "abstract_bom", "resolved_components"]):
            return build_plan_from_context(spec)

        selection = select_modules(spec)
        hardware_plan = allocate_pins(selection["board"], selection["selected_modules"])
        return generate_output(selection["board"], selection["selected_modules"], hardware_plan, spec)
    except MissingComponentsError as exc:
        if any(key in spec for key in ["project_brief", "requirements", "selected_module_ids", "capabilities", "abstract_bom", "resolved_components"]):
            preflight = preflight_build_context(spec)
            return {
                "message": "当前还不能直接生成，但已整理出可落地部分和缺口。",
                "assistant_message": "当前还不能直接生成，但已整理出可落地部分和缺口。",
                "error": "当前库里缺少可满足需求的模块",
                "error_type": "missing_components",
                "missing_capabilities": exc.missing_capabilities,
                "resolved_components": preflight.get("resolved_components", []),
                "unresolved_roles": preflight.get("unresolved_roles", []),
                "gap_analysis": preflight.get("gap_analysis", {}),
                "ready_to_build": False,
                "options": ["按降级 MVP 继续", "看看替代方案", "先补充库再做"],
                "current_spec": preflight.get("normalized_context"),
            }
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

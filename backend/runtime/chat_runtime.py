from __future__ import annotations

from typing import Any

from agent.module_selector import MissingComponentsError
from runtime.planner import LLMUnavailableError, plan_next_step
from runtime.session_memory import append_history, get_session, merge_memory
from runtime.tool_registry import ToolExecutionError, build_plan_from_context, execute_tool_call, preflight_build_context


async def process_chat_message(session_id: str, message: str) -> dict[str, Any]:
    session = get_session(session_id)
    append_history(session, "user", message)

    try:
        envelope = await plan_next_step(session.memory, session.history, message)
    except LLMUnavailableError:
        return _error_response(session_id, "AI 当前不可用，请稍后再试。", "llm_unavailable")
    except Exception:
        return _error_response(session_id, "AI 当前不可用，请稍后再试。", "llm_unavailable")

    return await _run_runtime_loop(session, envelope)


async def _run_runtime_loop(session, envelope: dict[str, Any]) -> dict[str, Any]:
    tool_results: list[dict[str, Any]] = []
    latest = envelope

    for _ in range(4):
        merge_memory(session, latest.get("memory_patch"))
        next_step = latest.get("next") or {"type": "continue"}
        next_type = next_step.get("type", "continue")

        if next_type == "tool":
            calls = next_step.get("calls") or []
            if not calls:
                break

            tool_results = []
            for call in calls[:3]:
                try:
                    result = execute_tool_call(call)
                    tool_results.append(result)
                    _apply_tool_result_to_memory(session, result)
                except ToolExecutionError as exc:
                    return _error_response(session.session_id, f"工具调用失败：{exc}", "tool_execution_failed")

            append_history(session, "assistant", {"planner": latest, "tool_results": tool_results})
            try:
                latest = await plan_next_step(session.memory, session.history, None, tool_results)
            except LLMUnavailableError:
                return _error_response(session.session_id, "AI 当前不可用，请稍后再试。", "llm_unavailable")
            except Exception:
                return _error_response(session.session_id, "AI 当前不可用，请稍后再试。", "llm_unavailable")
            continue

        if next_type == "build":
            build_context = next_step.get("build_context") or _memory_to_build_context(session.memory)
            preflight = preflight_build_context(build_context)
            session.memory["last_build_check"] = preflight

            if not preflight.get("buildable"):
                return _response(
                    session,
                    message=latest.get("speak") or "现在还不能生成，因为库里缺少关键组件。",
                    error_type=preflight.get("error_type") or "missing_components",
                    commitment=latest.get("commitment"),
                    current_spec=preflight.get("normalized_context"),
                    extra={"missing_components": preflight.get("missing_components", [])},
                )

            try:
                generated = build_plan_from_context(build_context)
            except MissingComponentsError as exc:
                return _response(
                    session,
                    message=latest.get("speak") or "现在还不能生成，因为库里缺少关键组件。",
                    error_type="missing_components",
                    commitment=latest.get("commitment"),
                    current_spec=build_context,
                    extra={"missing_components": exc.missing_capabilities},
                )
            except Exception as exc:
                error_type = getattr(exc, "error_type", "generation_not_supported_yet")
                return _response(
                    session,
                    message=latest.get("speak") or "当前组合还不能自动生成。",
                    error_type=error_type,
                    commitment=latest.get("commitment"),
                    current_spec=build_context,
                )

            merge_memory(session, {**(latest.get("memory_patch") or {}), **generated["meta"].get("build_context", {}), "ready_to_build": True})
            session.turn += 1
            append_history(session, "assistant", latest.get("speak") or "已生成方案。")
            return {
                "session_id": session.session_id,
                "message": latest.get("speak") or "已生成方案。",
                "assistant_message": latest.get("speak") or "已生成方案。",
                "options": [],
                "ready_to_build": True,
                "is_ready_for_final": True,
                "error_type": None,
                "commitment": latest.get("commitment", {}),
                "current_spec": generated["meta"].get("build_context", build_context),
                "build_output": generated,
                "tool_results": tool_results,
            }

        if next_type == "fail":
            return _response(
                session,
                message=latest.get("speak") or "这个需求当前无法完成。",
                error_type=next_step.get("error_type") or "missing_components",
                commitment=latest.get("commitment"),
                current_spec=_memory_to_build_context(session.memory),
                extra={"missing_components": next_step.get("missing_components", [])},
            )

        if next_type == "confirm":
            merge_memory(session, {**(latest.get("memory_patch") or {}), "ready_to_build": True})
            return _response(
                session,
                message=latest.get("speak") or "如果这版理解没问题，我就可以开始生成。",
                commitment=latest.get("commitment"),
                current_spec=_memory_to_build_context(session.memory),
                ready_to_build=True,
                options=["确认，开始生成", "我再补充一下"],
            )

        return _response(
            session,
            message=latest.get("speak") or "我还需要一点信息。",
            commitment=latest.get("commitment"),
            current_spec=_memory_to_build_context(session.memory),
            ready_to_build=bool(session.memory.get("ready_to_build")),
            extra={"tool_results": tool_results},
        )

    return _response(
        session,
        message=latest.get("speak") or "我先停在这里，你可以继续补充。",
        commitment=latest.get("commitment"),
        current_spec=_memory_to_build_context(session.memory),
        extra={"tool_results": tool_results},
    )


def _apply_tool_result_to_memory(session, result: dict[str, Any]) -> None:
    tool = result.get("tool")
    payload = result.get("result") or {}
    if tool == "library.search":
        merge_memory(session, {"last_search": payload.get("modules", [])})
    elif tool == "library.inspect":
        item = payload.get("item") or {}
        inspected = dict(session.memory.get("last_inspected") or {})
        if item.get("id"):
            inspected[item["id"]] = item
        selected = list(session.memory.get("selected_module_ids") or [])
        if payload.get("kind") == "module" and item.get("id") and item["id"] not in selected:
            selected.append(item["id"])
        merge_memory(session, {"last_inspected": inspected, "selected_module_ids": selected})


def _memory_to_build_context(memory: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_brief": memory.get("project_brief", ""),
        "requirements": memory.get("requirements", []),
        "constraints": memory.get("constraints", []),
        "selected_module_ids": memory.get("selected_module_ids", []),
        "selected_board_id": memory.get("selected_board_id", "esp32_devkit_v1"),
    }


def _response(session, message: str, commitment: dict[str, Any] | None = None, current_spec: dict[str, Any] | None = None, ready_to_build: bool = False, error_type: str | None = None, options: list[str] | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    session.turn += 1
    append_history(session, "assistant", message)
    payload = {
        "session_id": session.session_id,
        "message": message,
        "assistant_message": message,
        "options": options or [],
        "ready_to_build": ready_to_build,
        "is_ready_for_final": ready_to_build,
        "error_type": error_type,
        "commitment": commitment or {},
        "current_spec": current_spec or _memory_to_build_context(session.memory),
    }
    if extra:
        payload.update(extra)
    return payload


def _error_response(session_id: str, message: str, error_type: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "message": message,
        "assistant_message": message,
        "options": [],
        "ready_to_build": False,
        "is_ready_for_final": False,
        "error_type": error_type,
        "commitment": {},
        "current_spec": None,
    }

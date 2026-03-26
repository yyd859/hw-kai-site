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
                return _gap_response(
                    session,
                    latest=latest,
                    build_context=build_context,
                    preflight=preflight,
                    fallback_message="现在还不能直接生成，但我已经把可落地部分和缺口整理出来了。",
                )

            try:
                generated = build_plan_from_context(build_context)
            except MissingComponentsError as exc:
                gap_preflight = preflight_build_context({**build_context, "unresolved_roles": exc.missing_capabilities})
                gap_preflight["missing_components"] = exc.missing_capabilities
                gap_preflight["error_type"] = "missing_components"
                return _gap_response(
                    session,
                    latest=latest,
                    build_context=build_context,
                    preflight=gap_preflight,
                    fallback_message="生成前发现还有缺口，我先把已能落地和未 resolve 的部分给你列清楚。",
                )
            except Exception as exc:
                error_type = getattr(exc, "error_type", "generation_not_supported_yet")
                gap_preflight = preflight_build_context(build_context)
                gap_preflight["error_type"] = error_type
                return _gap_response(
                    session,
                    latest=latest,
                    build_context=build_context,
                    preflight=gap_preflight,
                    fallback_message="抽象方案已经明确，但当前组合还不能直接自动生成，我先给你一个 gap handling 结果。",
                )

            merge_memory(
                session,
                {
                    **(latest.get("memory_patch") or {}),
                    **generated["meta"].get("build_context", {}),
                    "ready_to_build": True,
                },
            )
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
            if next_step.get("error_type") == "missing_components" and _has_abstract_direction(session.memory, latest):
                fallback = latest.get("speak") or "我先不把它当成终点，而是把缺口和替代路径整理给你。"
                preflight = preflight_build_context(_memory_to_build_context(session.memory))
                preflight["missing_components"] = next_step.get("missing_components", preflight.get("missing_components", []))
                preflight["error_type"] = next_step.get("error_type") or preflight.get("error_type")
                return _gap_response(session, latest, _memory_to_build_context(session.memory), preflight, fallback)

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
        resolved = payload.get("resolved_components", [])
        selected_module_ids = [item.get("module_id") for item in resolved if item.get("module_id")]
        merge_memory(
            session,
            {
                "last_search": payload.get("modules", []),
                "last_resolution": payload,
                "resolved_components": resolved,
                "unresolved_roles": payload.get("unresolved_roles", []),
                "gap_analysis": payload.get("gap_analysis", {}),
                "selected_module_ids": selected_module_ids or session.memory.get("selected_module_ids", []),
            },
        )
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
        "subsystems": memory.get("subsystems", []),
        "abstract_bom": memory.get("abstract_bom", []),
        "open_questions": memory.get("open_questions", []),
        "selected_direction": memory.get("selected_direction", ""),
        "capabilities": memory.get("capabilities", []),
        "resolved_components": memory.get("resolved_components", []),
        "unresolved_roles": memory.get("unresolved_roles", []),
        "gap_analysis": memory.get("gap_analysis", {}),
        "selected_module_ids": memory.get("selected_module_ids", []),
        "selected_board_id": memory.get("selected_board_id", "esp32_devkit_v1"),
    }


def _gap_response(
    session,
    latest: dict[str, Any],
    build_context: dict[str, Any],
    preflight: dict[str, Any],
    fallback_message: str,
) -> dict[str, Any]:
    merged_context = {**build_context, **(preflight.get("normalized_context") or {})}
    resolved_components = preflight.get("resolved_components") or merged_context.get("resolved_components") or session.memory.get("resolved_components", [])
    unresolved_roles = preflight.get("unresolved_roles") or merged_context.get("unresolved_roles") or []
    missing_components = preflight.get("missing_components") or []
    gap_analysis = preflight.get("gap_analysis") or merged_context.get("gap_analysis") or {}
    gap_analysis = {
        "resolved": gap_analysis.get("resolved") or [_resolved_line(item) for item in resolved_components],
        "unresolved": gap_analysis.get("unresolved") or [_unresolved_line(item) for item in unresolved_roles],
        "suggestions": gap_analysis.get("suggestions") or _default_gap_suggestions(unresolved_roles or missing_components),
    }

    merge_memory(
        session,
        {
            **(latest.get("memory_patch") or {}),
            **(preflight.get("normalized_context") or {}),
            "resolved_components": resolved_components,
            "unresolved_roles": unresolved_roles,
            "gap_analysis": gap_analysis,
            "ready_to_build": False,
        },
    )

    message = latest.get("speak") or _compose_gap_message(resolved_components, unresolved_roles, gap_analysis, fallback_message)
    return _response(
        session,
        message=message,
        commitment=latest.get("commitment"),
        current_spec={**merged_context, "resolved_components": resolved_components, "unresolved_roles": unresolved_roles, "gap_analysis": gap_analysis},
        ready_to_build=False,
        error_type=preflight.get("error_type"),
        options=["按降级 MVP 继续", "看看替代方案", "先补充库再做"],
        extra={
            "missing_components": missing_components,
            "resolved_components": resolved_components,
            "unresolved_roles": unresolved_roles,
            "gap_analysis": gap_analysis,
        },
    )


def _compose_gap_message(
    resolved_components: list[dict[str, Any]],
    unresolved_roles: list[Any],
    gap_analysis: dict[str, Any],
    fallback_message: str,
) -> str:
    resolved_text = "、".join(gap_analysis.get("resolved") or [_resolved_line(item) for item in resolved_components]) or "暂时还没有已 resolve 的角色"
    unresolved_text = "、".join(gap_analysis.get("unresolved") or [_unresolved_line(item) for item in unresolved_roles]) or "暂无明显缺口"
    suggestions = gap_analysis.get("suggestions") or _default_gap_suggestions(unresolved_roles)
    suggestion_text = "；".join(suggestions[:3])
    return f"{fallback_message} 已能落地：{resolved_text}。还没 resolve：{unresolved_text}。可选路径：{suggestion_text}。"


def _resolved_line(item: dict[str, Any]) -> str:
    role = item.get("role") or item.get("capability") or "角色"
    module_id = item.get("module_id") or item.get("label") or "unknown"
    return f"{role} -> {module_id}"


def _unresolved_line(item: Any) -> str:
    if isinstance(item, dict):
        role = item.get("role") or item.get("capability") or "unknown"
        capability = item.get("capability") or ""
        return f"{role} ({capability})" if capability and capability != role else str(role)
    return str(item)


def _default_gap_suggestions(unresolved_roles: list[Any]) -> list[str]:
    text = " ".join(_unresolved_line(item).lower() for item in unresolved_roles)
    suggestions = ["先按已 resolve 的部分做一个最小 MVP", "把缺失角色换成更简单的替代方案", "后续补库后再扩展成完整版"]
    if "camera" in text or "vision" in text or "视觉" in text:
        suggestions[1] = "把视觉识别改成按钮、红外或其他非视觉触发"
    return suggestions


def _has_abstract_direction(memory: dict[str, Any], latest: dict[str, Any]) -> bool:
    context = {**memory, **(latest.get("memory_patch") or {}), **(latest.get("commitment") or {})}
    return bool(context.get("selected_direction") and context.get("abstract_bom"))


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

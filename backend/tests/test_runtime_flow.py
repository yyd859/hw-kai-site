from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from runtime import chat_runtime, planner  # noqa: E402
from runtime.session_memory import _sessions  # noqa: E402
from runtime.tool_registry import build_plan_from_context, library_search, preflight_build_context  # noqa: E402


class PlannerSanitizationTests(unittest.TestCase):
    def test_early_library_search_is_downgraded_to_continue(self):
        envelope = {
            "speak": "",
            "memory_patch": {"project_brief": "做一个会提醒喝水的桌面装置"},
            "next": {
                "type": "tool",
                "calls": [{"tool": "library.search", "arguments": {"query": "reminder", "capabilities": ["sound"]}}],
            },
        }

        sanitized = planner._sanitize_envelope(envelope, session_memory={}, latest_user_message="做一个会提醒喝水的桌面装置")
        self.assertEqual(sanitized["next"]["type"], "continue")
        self.assertIn("先", sanitized["speak"])


class RuntimeGapHandlingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        _sessions.clear()

    async def test_missing_components_becomes_gap_handling_response(self):
        envelope = {
            "speak": "",
            "commitment": {
                "project_brief": "做一个识别宠物再自动喂食的装置",
                "subsystems": ["检测宠物", "执行喂食"],
                "abstract_bom": [
                    {"role": "pet detection", "capability": "camera_vision", "notes": "识别是谁"},
                    {"role": "feeder actuator", "capability": "actuator", "notes": "控制出粮"},
                ],
                "selected_direction": "先做最小可验证版",
            },
            "memory_patch": {
                "project_brief": "做一个识别宠物再自动喂食的装置",
                "subsystems": ["检测宠物", "执行喂食"],
                "abstract_bom": [
                    {"role": "pet detection", "capability": "camera_vision", "notes": "识别是谁"},
                    {"role": "feeder actuator", "capability": "actuator", "notes": "控制出粮"},
                ],
                "selected_direction": "先做最小可验证版",
                "resolved_components": [{"role": "feeder actuator", "capability": "actuator", "module_id": "relay_module", "label": "Relay Module"}],
                "unresolved_roles": [{"role": "pet detection", "capability": "camera_vision", "notes": "识别是谁"}],
            },
            "next": {
                "type": "build",
                "build_context": {
                    "project_brief": "做一个识别宠物再自动喂食的装置",
                    "subsystems": ["检测宠物", "执行喂食"],
                    "abstract_bom": [
                        {"role": "pet detection", "capability": "camera_vision", "notes": "识别是谁"},
                        {"role": "feeder actuator", "capability": "actuator", "notes": "控制出粮"},
                    ],
                    "selected_direction": "先做最小可验证版",
                    "resolved_components": [{"role": "feeder actuator", "capability": "actuator", "module_id": "relay_module", "label": "Relay Module"}],
                },
            },
        }

        with patch.object(chat_runtime, "plan_next_step", AsyncMock(return_value=envelope)):
            response = await chat_runtime.process_chat_message("gap-case", "我想做个能识别宠物自动喂食的东西")

        self.assertFalse(response["ready_to_build"])
        self.assertEqual(response["error_type"], "missing_components")
        self.assertIn("resolved_components", response)
        self.assertIn("unresolved_roles", response)
        self.assertIn("gap_analysis", response)
        self.assertTrue(response["options"])
        self.assertIn("camera", str(response["unresolved_roles"]).lower())


class BuildCompatibilityTests(unittest.TestCase):
    def test_button_light_still_builds(self):
        output = build_plan_from_context(
            {
                "project_brief": "按按钮亮灯",
                "requirements": ["按下按钮时点亮灯环"],
                "selected_direction": "直接做最简互动版",
                "abstract_bom": [
                    {"role": "trigger input", "capability": "button"},
                    {"role": "light output", "capability": "light"},
                ],
                "resolved_components": [
                    {"role": "trigger input", "capability": "button", "module_id": "push_button"},
                    {"role": "light output", "capability": "light", "module_id": "ws2812_led_ring"},
                ],
            }
        )
        self.assertEqual(output["meta"]["combo"], "button_light")

    def test_auto_watering_still_builds(self):
        output = build_plan_from_context(
            {
                "project_brief": "自动浇花",
                "requirements": ["土壤太干时自动浇水"],
                "selected_direction": "先做阈值触发的自动版",
                "abstract_bom": [
                    {"role": "soil sensing", "capability": "soil_moisture"},
                    {"role": "watering actuator", "capability": "pump"},
                ],
                "resolved_components": [
                    {"role": "soil sensing", "capability": "soil_moisture", "module_id": "soil_moisture_sensor"},
                    {"role": "watering actuator", "capability": "pump", "module_id": "relay_module"},
                ],
            }
        )
        self.assertEqual(output["meta"]["combo"], "soil_relay")

    def test_late_resolution_can_return_partial_gap(self):
        result = library_search(
            query="宠物识别喂食器",
            roles=[
                {"role": "pet detection", "capability": "camera_vision", "notes": "识别是谁"},
                {"role": "feeder actuator", "capability": "actuator", "notes": "控制出粮"},
            ],
        )
        self.assertTrue(result["resolved_components"])
        self.assertTrue(result["unresolved_roles"])

    def test_preflight_preserves_gap_analysis(self):
        preflight = preflight_build_context(
            {
                "project_brief": "做一个识别宠物再自动喂食的装置",
                "selected_direction": "先做最小可验证版",
                "abstract_bom": [
                    {"role": "pet detection", "capability": "camera_vision"},
                    {"role": "feeder actuator", "capability": "actuator"},
                ],
                "resolved_components": [{"role": "feeder actuator", "capability": "actuator", "module_id": "relay_module"}],
            }
        )
        self.assertFalse(preflight["buildable"])
        self.assertIn("gap_analysis", preflight)
        self.assertTrue(preflight["gap_analysis"]["unresolved"])


if __name__ == "__main__":
    unittest.main()

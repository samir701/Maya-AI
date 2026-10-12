"""Unit tests for Tool foundation and SystemInfoTool execution."""

import unittest
from core.zetta.tools.registry import ToolRegistry
from core.zetta.tools.system.system_info import SystemInfoTool


class TestTools(unittest.TestCase):

    def test_tool_registry_and_execution(self):
        registry = ToolRegistry()
        tool = SystemInfoTool()
        registry.register(tool)

        tools_list = registry.list_tools()
        self.assertGreaterEqual(len(tools_list), 1)
        self.assertTrue(any(t["name"] == "system_info" for t in tools_list))

        result = registry.execute("system_info", {})
        self.assertTrue(result.success)
        self.assertIsNotNone(result.data.get("os"))
        self.assertIsNotNone(result.data.get("python_version"))




if __name__ == "__main__":
    unittest.main()

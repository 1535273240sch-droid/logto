import sys

with open(sys.argv[1], "r") as f:
    content = f.read()

# 1. Add import for ImageTool
old_import = "from ..core.tool_registry import ToolRegistry, ToolExecutionRecord, ToolStatus"
new_import = old_import + "\nfrom ..tools.image import ImageTool"
content = content.replace(old_import, new_import)

# 2. Add self._register_tools() call in __init__ after self.registry = ToolRegistry()
old_init = "self.registry = ToolRegistry()\n        self.planner = Planner()"
new_init = "self.registry = ToolRegistry()\n        self._register_tools()\n        self.planner = Planner()"
content = content.replace(old_init, new_init)

# 3. Add _register_tools method before "# ── Step 1: Context Builder"
old_marker = "# ── Step 1: Context Builder"
new_method = """    def _register_tools(self):
        from ..tools.stock import StockTool
        from ..tools.weather import WeatherTool
        from ..tools.http import HttpTool
        self.registry.register("image_generate", ImageTool())
        self.registry.register("stock_query", StockTool())
        self.registry.register("weather_query", WeatherTool())
        self.registry.register("http_fetch", HttpTool())

# ── Step 1: Context Builder"""
content = content.replace(old_marker, new_method)

# 4. Add execute_tool method after "return self._tool_records\n\n    # ── Step 6: Observation"
old_exec = "return self._tool_records\n\n    # ── Step 6: Observation"
new_exec = """return self._tool_records

    async def execute_tool(self, tool_name: str, command: str) -> ToolExecutionRecord:
        record = await self.registry.execute(tool_name, command, timeout=30)
        if record:
            record.intent = self._intent.intent_type if self._intent else ""
            self._tool_records.append(record)
        return record

    # ── Step 6: Observation"""
content = content.replace(old_exec, new_exec)

with open(sys.argv[1], "w") as f:
    f.write(content)

# Verify
print("import:", "ImageTool" in content)
print("init_call:", "self._register_tools()" in content)
print("def_method:", "def _register_tools" in content)
print("def_exec:", "def execute_tool" in content)
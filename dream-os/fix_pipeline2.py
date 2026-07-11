import sys

with open(sys.argv[1], "r") as f:
    lines = f.readlines()

result = []
# Track changes
import_added = False
init_modified = False
method_added = False
exec_added = False

for i, line in enumerate(lines):
    # 1. Add import after the existing import line
    if "from ..core.tool_registry import ToolRegistry, ToolExecutionRecord, ToolStatus" in line and not import_added:
        result.append(line)
        result.append("from ..tools.image import ImageTool\n")
        import_added = True
        continue

    # 2. Add self._register_tools() after self.registry = ToolRegistry()
    if "self.registry = ToolRegistry()" in line and not init_modified:
        result.append(line)
        result.append("        self._register_tools()\n")
        init_modified = True
        continue

    # 3. Insert _register_tools method before the "def build_context" line
    #    (which is right after the Step 1 comment)
    if "async def build_context(self, user_input: str) -> list[dict]:" in line and not method_added:
        # Add the _register_tools method before this line
        result.append("    def _register_tools(self):\n")
        result.append("        from ..tools.stock import StockTool\n")
        result.append("        from ..tools.weather import WeatherTool\n")
        result.append("        from ..tools.http import HttpTool\n")
        result.append('        self.registry.register("image_generate", ImageTool())\n')
        result.append('        self.registry.register("stock_query", StockTool())\n')
        result.append('        self.registry.register("weather_query", WeatherTool())\n')
        result.append('        self.registry.register("http_fetch", HttpTool())\n')
        result.append("\n")
        result.append(line)
        method_added = True
        continue

    # 4. Add execute_tool method after the execute method
    #    The execute method ends with "return self._tool_records" followed by
    #    "# Step 6: Observation" or "async def observe"
    if "return self._tool_records" in line and not exec_added:
        # Only add execute_tool after the execute method
        # (identify by checking if "async def observe" is nearby)
        nearby = " ".join(l.strip() for l in lines[i : min(i + 6, len(lines))])
        if "async def observe" in nearby:
            result.append(line)
            result.append("\n")
            result.append("    async def execute_tool(self, tool_name: str, command: str) -> ToolExecutionRecord:\n")
            result.append("        record = await self.registry.execute(tool_name, command, timeout=30)\n")
            result.append("        if record:\n")
            result.append('            record.intent = self._intent.intent_type if self._intent else ""\n')
            result.append("            self._tool_records.append(record)\n")
            result.append("        return record\n")
            result.append("\n")
            exec_added = True
            continue

    result.append(line)

with open(sys.argv[1], "w") as f:
    f.writelines(result)

print(f"import_added: {import_added}")
print(f"init_modified: {init_modified}")
print(f"method_added: {method_added}")
print(f"exec_added: {exec_added}")
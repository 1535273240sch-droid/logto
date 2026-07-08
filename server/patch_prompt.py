import re

with open("/app/app/core/agent_loop.py", "r") as f:
    content = f.read()

old = "## 可用工具"
new = "## 可用工具\n- time_query: 查询当前北京时间（直接调用，无需参数）\n"

content = content.replace(old, new, 1)

old2 = "1. 常识/百科问题直接回答，不调用工具"
new2 = "1. 日期、时间、星期、几点了等问题必须调用 time_query，禁止用 shell_exec 查时间"

content = content.replace(old2, new2)

with open("/app/app/core/agent_loop.py", "w") as f:
    f.write(content)

print("PATCH DONE")

#!/bin/bash
curl -s -X POST http://1.14.125.204:8009/v1/chat/completions \
  -H "Authorization: Bearer sk-mimo" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mimo-v2.5-pro",
    "messages": [{"role": "user", "content": "北京天气怎么样"}],
    "tools": [{
      "type": "function",
      "function": {
        "name": "weather_query",
        "description": "查询城市实时天气",
        "parameters": {
          "type": "object",
          "properties": {
            "command": {"type": "string", "description": "weather:城市名"}
          },
          "required": ["command"]
        }
      }
    }],
    "tool_choice": "auto",
    "max_tokens": 200
  }' --max-time 15 2>&1 | head -c 500
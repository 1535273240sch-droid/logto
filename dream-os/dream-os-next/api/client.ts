/**
 * API 客户端 — 统一请求入口
 */
const BASE = "/api";

export async function streamChat(
  message: string,
  mode: string,
  onEvent: (event: any) => void,
  signal?: AbortSignal
): Promise<void> {
  const taskId = `task_${Date.now()}`;
  const res = await fetch(`${BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, mode, task_id: taskId }),
    signal,
  });
  if (!res.ok || !res.body) return;
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (line.startsWith("data:")) {
        try {
          const data = JSON.parse(line.slice(5).trim());
          onEvent(data);
        } catch {}
      }
    }
  }
}

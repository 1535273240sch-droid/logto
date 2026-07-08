/** DEPAdapter — 将后端 SSE 事件转换为 DEP 协议
 *
 * 支持三种协议来源：
 *   1. V3 AutoLoop  → 透传（事件已是标准 DEP 格式）
 *   2. 旧 AgentPipeline → adaptAgentPipeline()
 *   3. 当前 Chat AgentLoop → adaptCurrentChat()
 */

import { DEPEventType, DEPPayload } from "../types/dep";

interface RawEvent {
  type: string;
  [key: string]: unknown;
}

// ═══════════════════════════════════════════════
//  当前 Chat 协议 (agent_loop.py run_chat)
//  事件: content / done / tool_start / tool_result
// ═══════════════════════════════════════════════

function makeBase(taskId: string) {
  return { task_id: taskId, timestamp: new Date().toISOString() };
}

export function adaptCurrentChat(raw: RawEvent, taskId: string): DEPPayload | null {
  const base = makeBase(taskId);

  switch (raw.type) {
    case "content":
      return {
        ...base,
        type: DEPEventType.CONTENT_DELTA,
        data: { chunk: (raw.content as string) || "" },
      } as DEPPayload;

    case "done":
      return {
        ...base,
        type: DEPEventType.TASK_COMPLETED,
        data: { success: true, summary: "", artifacts_count: 0, duration_ms: 0 },
      } as DEPPayload;

    case "tool_start":
      return {
        ...base,
        type: DEPEventType.AGENT_PROGRESS,
        data: {
          agent: (raw.tool as string) || "tool",
          progress_percent: 30,
          step: 0,
          total_steps: 0,
          current_step: `调用工具: ${raw.tool} — ${raw.description || ""}`,
        },
      } as DEPPayload;

    case "tool_result":
      return {
        ...base,
        type: DEPEventType.AGENT_PROGRESS,
        data: {
          agent: (raw.tool as string) || "tool",
          progress_percent: 70,
          step: 0,
          total_steps: 0,
          current_step: raw.success ? "工具执行成功" : `工具失败: ${(raw.output as string)?.slice(0, 80) || ""}`,
        },
      } as DEPPayload;

    // Dev 模式（V3 不可用时的模拟模式）
    case "dev_start":
      return {
        ...base,
        type: DEPEventType.FEATURE_LOADED,
        data: {
          feature_id: "dev",
          feature_name: "开发者",
          agents: ((raw.agents as Array<{ role: string }>) || []).map((a) => a.role),
        },
      } as DEPPayload;

    case "agent_start":
      return {
        ...base,
        type: DEPEventType.AGENT_STARTED,
        data: {
          agent: (raw.agent as string) || (raw.name as string) || "",
          agent_role: (raw.agent as string) || "",
          description: (raw.task as string) || (raw.name as string) || "",
        },
      } as DEPPayload;

    case "agent_complete":
      return {
        ...base,
        type: DEPEventType.AGENT_FINISHED,
        data: {
          agent: (raw.agent as string) || "",
          success: raw.success !== false,
          duration_ms: 0,
        },
      } as DEPPayload;

    case "dev_complete":
      return {
        ...base,
        type: DEPEventType.DELIVERY_READY,
        data: {
          summary: (raw.summary as string) || "开发完成",
          artifacts: [],
          duration_ms: 0,
          total_tool_calls: 0,
        },
      } as DEPPayload;

    default:
      return null;
  }
}


// ═══════════════════════════════════════════════
//  旧 AgentPipeline 协议（历史兼容）
// ═══════════════════════════════════════════════

export function adaptAgentPipeline(raw: RawEvent, taskId: string): DEPPayload | null {
  const base = makeBase(taskId);

  switch (raw.type) {
    case "pipeline_start":
      return { ...base, type: DEPEventType.TASK_CREATED, data: { feature: "chat", user_input: "", mode: "chat" } } as DEPPayload;
    case "step_start":
      return { ...base, type: DEPEventType.AGENT_STARTED, data: { agent: (raw.step as string) || "agent", agent_role: (raw.label as string) || "", description: (raw.label as string) || "" } } as DEPPayload;
    case "step_complete":
      return { ...base, type: DEPEventType.AGENT_FINISHED, data: { agent: (raw.step as string) || "agent", success: raw.status === "success", duration_ms: (raw.duration_ms as number) || 0 } } as DEPPayload;
    case "tool_start":
      return { ...base, type: DEPEventType.AGENT_PROGRESS, data: { agent: (raw.tool as string) || "agent", progress_percent: 0, step: 0, total_steps: 0, current_step: (raw.description as string) || "" } } as DEPPayload;
    case "tool_result":
      return { ...base, type: DEPEventType.AGENT_PROGRESS, data: { agent: (raw.tool as string) || "agent", progress_percent: 50, step: 0, total_steps: 0, current_step: (raw.result_preview as string) || "" } } as DEPPayload;
    case "final":
      return { ...base, type: DEPEventType.TASK_COMPLETED, data: { success: true, summary: (raw.answer as string) || "", artifacts_count: 0, duration_ms: 0 } } as DEPPayload;
    case "error":
      return { ...base, type: DEPEventType.TASK_ERROR, data: { error_code: "PIPELINE_ERROR", message: (raw.content as string) || (raw.message as string) || "Unknown error", recoverable: false } } as DEPPayload;
    case "intent":
      return null;
    default:
      return null;
  }
}


// ═══════════════════════════════════════════════
//  旧 Orchestrator 事件 → DEP (历史兼容)
// ═══════════════════════════════════════════════

export function adaptOrchestrator(raw: RawEvent, taskId: string): DEPPayload | null {
  const base = makeBase(taskId);

  switch (raw.type) {
    case "dev_start":
      return { ...base, type: DEPEventType.FEATURE_LOADED, data: { feature_id: "dev", feature_name: "Developer", agents: ((raw.agents as Array<{ role: string }>) || []).map((a) => a.role) } } as DEPPayload;
    case "agent_handoff":
      return { ...base, type: DEPEventType.AGENT_STARTED, data: { agent: (raw.to as string) || "", agent_role: (raw.to as string) || "", description: `Handoff from ${raw.from}` } } as DEPPayload;
    case "progress_update":
      return { ...base, type: DEPEventType.AGENT_PROGRESS, data: { agent: (raw.current_agent as string) || "", progress_percent: (raw.percent as number) || 0, step: (raw.completed as number) || 0, total_steps: (raw.total as number) || 0, current_step: (raw.summary as string) || "" } } as DEPPayload;
    case "dev_complete":
      return { ...base, type: DEPEventType.DELIVERY_READY, data: { summary: (raw.summary as string) || "", artifacts: [], duration_ms: (raw.duration_ms as number) || 0, total_tool_calls: (raw.total_tool_calls as number) || 0 } } as DEPPayload;
    case "loop_iteration":
      if (raw.status === "retrying") {
        return { ...base, type: DEPEventType.TASK_RETRY, data: { error_code: "TEST_FAILED", message: (raw.reason as string) || "Retrying", recoverable: true } } as DEPPayload;
      }
      return null;
    default:
      return null;
  }
}


// ═══════════════════════════════════════════════
//  统一适配入口
//  优先尝试当前协议 → 旧 pipeline → 旧 orchestrator
// ═══════════════════════════════════════════════

export function adaptToDEP(
  raw: RawEvent,
  taskId: string,
  source: "pipeline" | "orchestrator" | "auto" = "auto"
): DEPPayload | null {
  // 1. V3 事件直接透传（已经是 DEP 格式）
  if (
    raw.type && typeof raw.type === "string" &&
    (raw.type === "task_created" || raw.type === "agent_started" ||
     raw.type === "agent_progress" || raw.type === "agent_finished" ||
     raw.type === "artifact_created" || raw.type === "delivery_ready" ||
     raw.type === "task_completed" || raw.type === "task_error" ||
     raw.type === "content_delta" || raw.type === "feature_loaded")
  ) {
    const base = makeBase(taskId);
    return { ...base, ...raw, type: raw.type as DEPEventType } as DEPPayload;
  }

  // 2. 当前 Chat 协议
  const current = adaptCurrentChat(raw, taskId);
  if (current) return current;

  // 3. 历史兼容
  if (source === "pipeline") return adaptAgentPipeline(raw, taskId);
  if (source === "orchestrator") return adaptOrchestrator(raw, taskId);

  // 4. 全尝试
  return adaptAgentPipeline(raw, taskId) || adaptOrchestrator(raw, taskId);
}

export default adaptToDEP;

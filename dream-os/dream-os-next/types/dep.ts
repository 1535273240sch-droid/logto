/**
 * DEP Event Type 定义 — 同时包含后端直接发送和前端内部使用的事件
 */

export enum DEPEventType {
  // 任务生命周期
  TASK_CREATED    = "task_created",
  TASK_PLANNING   = "task_planning",
  TASK_STARTED    = "task_started",
  TASK_COMPLETED  = "task_completed",

  // Feature
  FEATURE_LOADED  = "feature_loaded",

  // Agent
  AGENT_STARTED   = "agent_started",
  AGENT_PROGRESS  = "agent_progress",
  AGENT_FINISHED  = "agent_finished",

  // 流式内容
  CONTENT_DELTA   = "content_delta",

  // Artifact
  ARTIFACT_CREATED = "artifact_created",
  DELIVERY_READY   = "delivery_ready",

  // 异常
  TASK_RETRY      = "task_retry",
  TASK_WARNING    = "task_warning",
  TASK_ERROR      = "task_error",
  TASK_CANCELLED  = "task_cancelled",
}

// ── 事件数据结构 ──

export interface DEPEvent {
  type: DEPEventType;
  task_id: string;
  timestamp: string;
  data: Record<string, unknown>;
}

// ── 具体事件 Payload ──

export interface TaskCreatedPayload extends DEPEvent {
  type: DEPEventType.TASK_CREATED;
  data: {
    feature: string;
    user_input: string;
    mode: string;
  };
}

export interface TaskPlanningPayload extends DEPEvent {
  type: DEPEventType.TASK_PLANNING;
  data: {
    intent: string;
    plan_summary: string;
    estimated_steps: number;
  };
}

export interface FeatureLoadedPayload extends DEPEvent {
  type: DEPEventType.FEATURE_LOADED;
  data: {
    feature_id: string;
    feature_name: string;
    agents: string[];
  };
}

export interface AgentStartedPayload extends DEPEvent {
  type: DEPEventType.AGENT_STARTED;
  data: {
    agent: string;
    agent_role: string;
    description: string;
  };
}

export interface AgentProgressPayload extends DEPEvent {
  type: DEPEventType.AGENT_PROGRESS;
  data: {
    agent: string;
    progress_percent: number;
    step: number;
    total_steps: number;
    current_step: string;
  };
}

export interface AgentFinishedPayload extends DEPEvent {
  type: DEPEventType.AGENT_FINISHED;
  data: {
    agent: string;
    success: boolean;
    duration_ms: number;
  };
}

export interface ContentDeltaPayload extends DEPEvent {
  type: DEPEventType.CONTENT_DELTA;
  data: {
    chunk: string;
  };
}

export interface ArtifactCreatedPayload extends DEPEvent {
  type: DEPEventType.ARTIFACT_CREATED;
  data: {
    artifact_id: string;
    artifact_type: string;
    name: string;
    preview_url?: string;
    files: string[];
  };
}

export interface DeliveryReadyPayload extends DEPEvent {
  type: DEPEventType.DELIVERY_READY;
  data: {
    summary: string;
    artifacts: Array<{
      id: string;
      type: string;
      name: string;
      url?: string;
    }>;
    duration_ms: number;
    total_tool_calls: number;
  };
}

export interface TaskCompletedPayload extends DEPEvent {
  type: DEPEventType.TASK_COMPLETED;
  data: {
    success: boolean;
    summary: string;
    artifacts_count: number;
    duration_ms: number;
  };
}

export interface TaskErrorPayload extends DEPEvent {
  type: DEPEventType.TASK_ERROR;
  data: {
    error_code: string;
    message: string;
    agent?: string;
    recoverable: boolean;
  };
}

// ── 联合类型 ──

export type DEPPayload =
  | TaskCreatedPayload
  | TaskPlanningPayload
  | FeatureLoadedPayload
  | AgentStartedPayload
  | AgentProgressPayload
  | AgentFinishedPayload
  | ContentDeltaPayload
  | ArtifactCreatedPayload
  | DeliveryReadyPayload
  | TaskCompletedPayload
  | TaskErrorPayload;

// ── SSE 解析 ──

export function parseDEPLine(line: string): DEPPayload | null {
  if (!line.startsWith("data: ")) return null;
  try {
    return JSON.parse(line.slice(6)) as DEPPayload;
  } catch {
    return null;
  }
}

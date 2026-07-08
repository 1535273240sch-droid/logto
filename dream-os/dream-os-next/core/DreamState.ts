/**
 * DreamState — 状态机
 *
 * Dream OS 核心状态机，驱动整个 Living Canvas。
 *
 * 四态：Idle → Thinking → Working → Delivery → Idle
 * 预留：Review / Error
 *
 * 所有界面根据 DreamState 自动渲染，禁止 if dev / if plugin 判断。
 * Feature 只负责内容，DreamState 负责状态。
 */

import { DreamStateVariant, AgentStatus, Artifact } from "../types/dream";
import { eventBus } from "./EventBus";

export interface TaskContext {
  task_id: string;
  feature: string;
  user_input: string;
  progress_percent: number;
  current_agent?: string;
}

export interface DreamStateSnapshot {
  state: DreamStateVariant;
  activeTask: TaskContext | null;
  agents: AgentStatus[];
  artifacts: Artifact[];
  backgroundTaskCount: number;
  thinkingMessage: string;
  content: string;
}

type StateChangeListener = (snapshot: DreamStateSnapshot) => void;

export class DreamState {
  private static _instance: DreamState;

  private _state: DreamStateVariant = DreamStateVariant.IDLE;
  private _activeTask: TaskContext | null = null;
  private _agents: AgentStatus[] = [];
  private _artifacts: Artifact[] = [];
  private _backgroundTaskCount = 0;
  private _thinkingMessage = "";
  private _content = "";
  private _listeners: StateChangeListener[] = [];

  private constructor() {}

  static getInstance(): DreamState {
    if (!DreamState._instance) {
      DreamState._instance = new DreamState();
    }
    return DreamState._instance;
  }

  // ── 状态转换 ──

  /** 进入 Thinking */
  enterThinking(task: TaskContext, message = "正在理解你的目标..."): void {
    this._state = DreamStateVariant.THINKING;
    this._activeTask = task;
    this._thinkingMessage = message;
    this._agents = [];
    this._content = "";
    this._emit();
  }

  /** 进入 Working */
  enterWorking(): void {
    this._state = DreamStateVariant.WORKING;
    this._thinkingMessage = "";
    this._emit();
  }

  /** 进入 Delivery */
  enterDelivery(): void {
    this._state = DreamStateVariant.DELIVERY;
    this._emit();
  }

  /** 回到 Idle */
  enterIdle(): void {
    this._state = DreamStateVariant.IDLE;
    this._activeTask = null;
    this._agents = [];
    this._artifacts = [];
    this._thinkingMessage = "";
    this._content = "";
    this._emit();
  }

  // ── Agent 状态 ──

  updateAgent(agent: AgentStatus): void {
    const idx = this._agents.findIndex((a) => a.agent === agent.agent);
    if (idx >= 0) {
      this._agents[idx] = agent;
    } else {
      this._agents.push(agent);
    }
    this._emit();
  }

  // ── Content 流式追加 ──

  appendContent(chunk: string): void {
    this._content += chunk;
    this._emit();
  }

  // ── Artifact ──

  addArtifact(artifact: Artifact): void {
    this._artifacts.push(artifact);
    this._emit();
  }

  // ── 后台任务 ──

  setBackgroundTaskCount(count: number): void {
    this._backgroundTaskCount = count;
    this._emit();
  }

  // ── 快照 ──

  getSnapshot(): DreamStateSnapshot {
    return {
      state: this._state,
      activeTask: this._activeTask,
      agents: [...this._agents],
      artifacts: [...this._artifacts],
      backgroundTaskCount: this._backgroundTaskCount,
      thinkingMessage: this._thinkingMessage,
      content: this._content,
    };
  }

  get currentState(): DreamStateVariant {
    return this._state;
  }

  get isIdle(): boolean {
    return this._state === DreamStateVariant.IDLE;
  }

  // ── 监听 ──

  subscribe(listener: StateChangeListener): () => void {
    this._listeners.push(listener);
    return () => {
      this._listeners = this._listeners.filter((l) => l !== listener);
    };
  }

  private _emit(): void {
    const snapshot = this.getSnapshot();
    for (const listener of this._listeners) {
      try {
        listener(snapshot);
      } catch (err) {
        console.error("[DreamState] Listener error:", err);
      }
    }
  }
}

export const dreamState = DreamState.getInstance();
export default dreamState;

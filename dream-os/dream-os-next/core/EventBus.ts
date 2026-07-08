/**
 * EventBus — Dream OS 事件总线
 *
 * 所有模块间通信统一通过 EventBus。
 * 禁止跨模块直接调用。
 * 支持通配符订阅（如 task.* 匹配 task_created、task_completed 等）。
 */

import { DEPPayload } from "../types/dep";

type EventHandler = (event: DEPPayload) => void | Promise<void>;

interface Subscription {
  pattern: string;
  handler: EventHandler;
  id: string;
}

export class EventBus {
  private static _instance: EventBus;
  private _subscriptions: Subscription[] = [];
  private _history: DEPPayload[] = [];
  private _maxHistory = 500;

  private constructor() {}

  static getInstance(): EventBus {
    if (!EventBus._instance) {
      EventBus._instance = new EventBus();
    }
    return EventBus._instance;
  }

  /** 订阅事件（支持通配符 *） */
  subscribe(pattern: string, handler: EventHandler): string {
    const id = `sub_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    this._subscriptions.push({ pattern, handler, id });
    return id;
  }

  /** 取消订阅 */
  unsubscribe(id: string): void {
    this._subscriptions = this._subscriptions.filter((s) => s.id !== id);
  }

  /** 发布事件 */
  async publish(event: DEPPayload): Promise<void> {
    this._history.push(event);
    if (this._history.length > this._maxHistory) {
      this._history = this._history.slice(-this._maxHistory);
    }

    const matched = this._subscriptions.filter((s) =>
      this._matchPattern(s.pattern, event.type)
    );

    for (const sub of matched) {
      try {
        await sub.handler(event);
      } catch (err) {
        console.error(`[EventBus] Handler error for ${event.type}:`, err);
      }
    }
  }

  /** 获取历史事件 */
  getHistory(eventType?: string, limit = 50): DEPPayload[] {
    if (eventType) {
      return this._history.filter((e) => e.type === eventType).slice(-limit);
    }
    return this._history.slice(-limit);
  }

  /** 清空历史 */
  clearHistory(): void {
    this._history = [];
  }

  private _matchPattern(pattern: string, eventType: string): boolean {
    if (pattern === "*") return true;
    if (pattern.endsWith("*")) {
      return eventType.startsWith(pattern.slice(0, -1));
    }
    return pattern === eventType;
  }
}

export const eventBus = EventBus.getInstance();
export default eventBus;

/**
 * ProviderStore — AI 引擎配置管理
 *
 * 职责：
 * - Provider CRUD
 * - 自动保存到 localStorage
 * - 后台同步到服务器
 * - 连接测试
 * - 默认模型切换
 *
 * 不耦合任何 UI 组件，不依赖任何 Feature。
 */

import {
  ProviderConfig,
  ProviderConnectionTestResult,
  ProviderStatus,
  DEFAULT_PROVIDERS,
} from "../types/provider";

const STORAGE_KEY = "dream_os_providers";
const SYNC_URL = "/api/ai-engine/providers";

type ProviderListener = (providers: ProviderConfig[]) => void;

export class ProviderStore {
  private static _instance: ProviderStore;
  private _providers: ProviderConfig[] = [];
  private _listeners: ProviderListener[] = [];
  private _saveTimer: ReturnType<typeof setTimeout> | null = null;
  private _ready = false;

  private constructor() {}

  static getInstance(): ProviderStore {
    if (!ProviderStore._instance) {
      ProviderStore._instance = new ProviderStore();
    }
    return ProviderStore._instance;
  }

  /** 初始化：从 localStorage 加载，无数据则用默认值 */
  async init(): Promise<void> {
    if (this._ready) return;

    // 1. 从 localStorage 加载
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        this._providers = JSON.parse(stored);
      } catch {
        this._initDefaults();
      }
    } else {
      this._initDefaults();
    }

    // 2. 尝试从服务器同步
    await this._syncFromServer();

    this._ready = true;
    this._notify();
  }

  private _initDefaults(): void {
    this._providers = DEFAULT_PROVIDERS.map((p, i) => ({
      ...p,
      id: `provider_${i}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }));
    this._autoSave();
  }

  // ── CRUD ──

  getAll(): ProviderConfig[] {
    return [...this._providers];
  }

  getEnabled(): ProviderConfig[] {
    return this._providers.filter((p) => p.enabled);
  }

  getDefault(): ProviderConfig | undefined {
    return this._providers.find((p) => p.isDefault && p.enabled);
  }

  getById(id: string): ProviderConfig | undefined {
    return this._providers.find((p) => p.id === id);
  }

  /** 新增 Provider */
  addProvider(config: Omit<ProviderConfig, "id" | "createdAt" | "updatedAt" | "status" | "latencyMs" | "lastTested">): ProviderConfig {
    const provider: ProviderConfig = {
      ...config,
      id: `provider_${Date.now()}`,
      status: "disconnected",
      latencyMs: null,
      lastTested: null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    this._providers.push(provider);
    this._autoSave();
    this._notify();
    return provider;
  }

  /** 更新 Provider */
  updateProvider(id: string, updates: Partial<ProviderConfig>): void {
    const idx = this._providers.findIndex((p) => p.id === id);
    if (idx < 0) return;
    this._providers[idx] = {
      ...this._providers[idx],
      ...updates,
      updatedAt: new Date().toISOString(),
    };
    this._autoSave();
    this._notify();
  }

  /** 删除 Provider */
  removeProvider(id: string): void {
    this._providers = this._providers.filter((p) => p.id !== id);
    this._autoSave();
    this._notify();
  }

  /** 设置默认模型 */
  setDefault(id: string): void {
    this._providers = this._providers.map((p) => ({
      ...p,
      isDefault: p.id === id,
      updatedAt: p.id === id ? new Date().toISOString() : p.updatedAt,
    }));
    this._autoSave();
    this._notify();
  }

  /** 切换启用/禁用 */
  toggleEnabled(id: string): void {
    const provider = this.getById(id);
    if (provider) {
      this.updateProvider(id, { enabled: !provider.enabled });
    }
  }

  // ── 连接测试 ──

  async testConnection(id: string): Promise<ProviderConnectionTestResult> {
    const provider = this.getById(id);
    if (!provider) {
      return { success: false, message: "Provider 不存在", latencyMs: null };
    }

    this.updateProvider(id, { status: "testing" });

    const startTime = performance.now();

    try {
      const response = await fetch(provider.baseUrl + "/models", {
        headers: {
          Authorization: `Bearer ${provider.apiKey}`,
          "Content-Type": "application/json",
        },
        signal: AbortSignal.timeout(10000),
      });

      const latencyMs = Math.round(performance.now() - startTime);

      if (response.ok) {
        const result: ProviderConnectionTestResult = {
          success: true,
          message: "连接成功",
          latencyMs,
        };
        this.updateProvider(id, {
          status: "connected",
          latencyMs,
          lastTested: new Date().toISOString(),
        });
        return result;
      } else if (response.status === 401 || response.status === 403) {
        const result: ProviderConnectionTestResult = {
          success: false,
          message: "API Key 错误",
          latencyMs,
          errorCode: "auth_error",
        };
        this.updateProvider(id, { status: "error" });
        return result;
      } else {
        const result: ProviderConnectionTestResult = {
          success: false,
          message: `服务器返回 ${response.status}`,
          latencyMs,
          errorCode: "unknown",
        };
        this.updateProvider(id, { status: "error" });
        return result;
      }
    } catch (err) {
      const latencyMs = Math.round(performance.now() - startTime);
      const errorMsg = (err as Error).message || "Unknown error";

      let errorCode: ProviderConnectionTestResult["errorCode"] = "network_error";
      let message = "网络异常";

      if (errorMsg.includes("timeout") || errorMsg.includes("Timeout")) {
        message = "连接超时";
      } else if (errorMsg.includes("fetch") || errorMsg.includes("NetworkError")) {
        message = "Base URL 无法访问";
      }

      const result: ProviderConnectionTestResult = {
        success: false,
        message,
        latencyMs,
        errorCode,
      };
      this.updateProvider(id, { status: "error" });
      return result;
    }
  }

  // ── 持久化 ──

  private _autoSave(): void {
    // 防抖：300ms 内多次修改只保存一次
    if (this._saveTimer) clearTimeout(this._saveTimer);
    this._saveTimer = setTimeout(() => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this._providers));
      this._syncToServer();
      this._saveTimer = null;
    }, 300);
  }

  private async _syncToServer(): Promise<void> {
    try {
      await fetch(SYNC_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ providers: this._providers }),
      });
    } catch {
      // 服务器不可用时静默失败，配置已保存在 localStorage
    }
  }

  private async _syncFromServer(): Promise<void> {
    try {
      const res = await fetch(SYNC_URL);
      if (res.ok) {
        const data = await res.json();
        if (data.providers && Array.isArray(data.providers)) {
          this._providers = data.providers;
          localStorage.setItem(STORAGE_KEY, JSON.stringify(this._providers));
        }
      }
    } catch {
      // 服务器不可用，使用 localStorage 数据
    }
  }

  // ── 监听 ──

  subscribe(listener: ProviderListener): () => void {
    this._listeners.push(listener);
    return () => {
      this._listeners = this._listeners.filter((l) => l !== listener);
    };
  }

  private _notify(): void {
    const snapshot = this.getAll();
    for (const listener of this._listeners) {
      try { listener(snapshot); } catch (err) {
        console.error("[ProviderStore] Listener error:", err);
      }
    }
  }
}

export const providerStore = ProviderStore.getInstance();
export default providerStore;

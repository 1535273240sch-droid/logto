/**
 * AI Engine Center — Provider 类型定义
 *
 * 每个 Provider 独立配置，通过 Registry 注册。
 * 不写死任何模型，新增 Provider 只注册不修改核心代码。
 */

export type ProviderStatus = "connected" | "disconnected" | "error" | "testing";

export interface ProviderConfig {
  id: string;               // 唯一标识: openai / deepseek / ollama ...
  name: string;             // 显示名称: OpenAI / DeepSeek / Ollama ...
  apiKey: string;           // API Key
  baseUrl: string;          // Base URL
  modelId: string;          // Model ID
  isDefault: boolean;       // 是否默认模型
  enabled: boolean;         // 是否启用
  status: ProviderStatus;   // 连接状态
  latencyMs: number | null; // 响应延迟(ms)
  lastTested: string | null; // 最后测试时间
  createdAt: string;        // 创建时间
  updatedAt: string;        // 更新时间
}

export interface ProviderConnectionTestResult {
  success: boolean;
  message: string;
  latencyMs: number | null;
  errorCode?: "auth_error" | "network_error" | "model_not_found" | "unknown";
}

// 默认 Provider 模板
export const DEFAULT_PROVIDERS: Omit<ProviderConfig, "id" | "createdAt" | "updatedAt">[] = [
  {
    name: "OpenAI",
    apiKey: "",
    baseUrl: "https://api.openai.com/v1",
    modelId: "gpt-4o",
    isDefault: true,
    enabled: true,
    status: "disconnected",
    latencyMs: null,
    lastTested: null,
  },
  {
    name: "DeepSeek",
    apiKey: "",
    baseUrl: "https://api.deepseek.com/v1",
    modelId: "deepseek-chat",
    isDefault: false,
    enabled: false,
    status: "disconnected",
    latencyMs: null,
    lastTested: null,
  },
  {
    name: "Claude",
    apiKey: "",
    baseUrl: "https://api.anthropic.com/v1",
    modelId: "claude-sonnet-4-20250514",
    isDefault: false,
    enabled: false,
    status: "disconnected",
    latencyMs: null,
    lastTested: null,
  },
  {
    name: "Gemini",
    apiKey: "",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta",
    modelId: "gemini-2.5-pro",
    isDefault: false,
    enabled: false,
    status: "disconnected",
    latencyMs: null,
    lastTested: null,
  },
  {
    name: "Ollama (本地)",
    apiKey: "ollama",
    baseUrl: "http://localhost:11434/v1",
    modelId: "llama3",
    isDefault: false,
    enabled: false,
    status: "disconnected",
    latencyMs: null,
    lastTested: null,
  },
];

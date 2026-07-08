/**
 * Dream OS 核心类型定义
 *
 * DreamState + Feature + Artifact + Canvas
 * 这些类型是 Core 与所有 Feature 的契约。
 */

// ── DreamState（四态机）──

export enum DreamStateVariant {
  IDLE      = "idle",
  THINKING  = "thinking",
  WORKING   = "working",
  DELIVERY  = "delivery",
}

// 预留
export enum DreamStateVariantReserved {
  REVIEW = "review",
  ERROR  = "error",
}

// ── Feature 接口 ──

export interface FeatureDescriptor {
  id: string;
  name: string;
  description: string;
  icon: string;
  agents: string[];
  triggerKeywords: string[];
  artifactTypes: string[];
}

export interface Feature {
  descriptor: FeatureDescriptor;
  renderer: unknown;         // React 组件（具体类型由前端决定）
  taskCard: unknown;         // 任务卡片
  artifactRenderer: unknown; // 成果渲染器
  commands: Record<string, () => void>;
  toolAdapter: unknown;
}

// ── Artifact ──

export interface Artifact {
  id: string;
  task_id: string;
  type: string;               // website | ppt | image | document | code
  name: string;
  description: string;
  status: "ready" | "building" | "failed";
  preview_url?: string;
  download_url?: string;
  files: ArtifactFile[];
  created_at: string;
  updated_at: string;
  project_id?: string;
}

export interface ArtifactFile {
  filename: string;
  file_type: string;
  size: number;
  lines?: number;
}

// ── Canvas Context ──

export interface CanvasContext {
  state: DreamStateVariant;
  activeTask?: {
    task_id: string;
    feature: string;
    user_input: string;
    progress_percent: number;
    current_agent?: string;
  };
  agents: AgentStatus[];
  artifacts: Artifact[];
  backgroundTasks: number;
}

export interface AgentStatus {
  agent: string;
  role: string;
  status: "waiting" | "running" | "done" | "failed";
  progress_percent: number;
  description?: string;
}

// ── Registry 配置 ──

export interface RegistryConfig {
  features: Record<string, Feature>;
  plugins: Record<string, unknown>;
  renderers: Record<string, unknown>;
  commands: Record<string, () => void>;
}

// ── Theme Token（DDL）──

export interface ThemeTokens {
  colors: {
    bgPrimary: string;
    bgSecondary: string;
    bgCard: string;
    bgGlass: string;
    border: string;
    borderGlass: string;
    textPrimary: string;
    textSecondary: string;
    textMuted: string;
    accent: string;
    accentHover: string;
    accentLight: string;
    success: string;
    error: string;
    warning: string;
  };
  radii: {
    button: number;
    input: number;
    card: number;
    cardLarge: number;
    modal: number;
  };
  spacing: {
    xs: number;    // 8
    sm: number;    // 16
    md: number;    // 24
    lg: number;    // 32
    xl: number;    // 40
    xxl: number;   // 48
    xxxl: number;  // 64
  };
  fontSize: {
    logo: number;     // 40-48
    h1: number;       // 28
    h2: number;       // 22
    body: number;     // 16
    caption: number;  // 14
    status: number;   // 13
  };
  fontWeight: {
    regular: number;  // 400
    medium: number;   // 500
  };
}

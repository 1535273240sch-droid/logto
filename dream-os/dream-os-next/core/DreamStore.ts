/**
 * DreamStore — zustand 全局状态管理
 * 替代散落的 useState/Context，提供统一的响应式状态
 */
import { create } from "zustand";

export interface AgentState {
  id: string;
  role: string;
  status: "pending" | "running" | "done" | "failed";
  progress: number;
  message: string;
}

export interface DreamStoreState {
  // 状态
  state: "IDLE" | "THINKING" | "WORKING" | "DELIVERY";
  taskId: string | null;
  thinkingMessage: string;
  content: string;
  agents: AgentState[];
  artifacts: Array<{ id: string; name: string; type: string; preview_url?: string }>;
  backgroundTaskCount: number;

  // 操作
  enterThinking: (taskId: string, message: string) => void;
  enterWorking: () => void;
  enterDelivery: () => void;
  enterIdle: () => void;
  appendContent: (text: string) => void;
  setContent: (text: string) => void;
  setAgentStatus: (id: string, status: string) => void;
  setAgentProgress: (id: string, progress: number, message: string) => void;
  addAgent: (id: string, role: string) => void;
  addArtifact: (artifact: any) => void;
}

export const useDreamStore = create<DreamStoreState>((set) => ({
  state: "IDLE",
  taskId: null,
  thinkingMessage: "",
  content: "",
  agents: [],
  artifacts: [],
  backgroundTaskCount: 0,

  enterThinking: (taskId, message) =>
    set({ state: "THINKING", taskId, thinkingMessage: message, content: "", agents: [], artifacts: [] }),

  enterWorking: () => set({ state: "WORKING", thinkingMessage: "" }),

  enterDelivery: () => set({ state: "DELIVERY" }),

  enterIdle: () => set({ state: "IDLE", taskId: null, agents: [], artifacts: [], thinkingMessage: "", content: "" }),

  appendContent: (text) => set((s) => ({ content: s.content + text })),

  setContent: (text) => set({ content: text }),

  setAgentStatus: (id, status) =>
    set((s) => ({
      agents: s.agents.map((a) => (a.id === id ? { ...a, status: status as any } : a)),
    })),

  setAgentProgress: (id, progress, message) =>
    set((s) => ({
      agents: s.agents.map((a) => (a.id === id ? { ...a, progress, message } : a)),
    })),

  addAgent: (id, role) =>
    set((s) => ({
      agents: [...s.agents.filter((a) => a.id !== id), { id, role, status: "pending", progress: 0, message: "" }],
    })),

  addArtifact: (artifact) => set((s) => ({ artifacts: [...s.artifacts, artifact] })),
}));

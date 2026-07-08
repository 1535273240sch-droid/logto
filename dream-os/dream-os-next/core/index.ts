/**
 * Core — Dream OS 核心层
 *
 * Core 是整个系统不可替换的基础能力。
 * Feature 必须依赖 Core，Core 永远不知道 Feature 的存在。
 * 新增功能：只注册，不修改 Core。
 */

export { DreamState, dreamState } from "./DreamState";
export type { DreamStateSnapshot, TaskContext } from "./DreamState";

export { EventBus, eventBus } from "./EventBus";

export { Registry, registry } from "./Registry";

export { theme, sp, color, radius } from "./Theme";

export { config } from "./Config";

export { ArtifactStore, artifactStore } from "./ArtifactStore";

export { QualityGuardian, qualityGuardian } from "./QualityGuardian";
export type { GuardResult } from "./QualityGuardian";

export { ProviderStore, providerStore } from "./ProviderStore";
export { UIProtector, uiProtector } from "./UIProtector";
export type { ProviderConfig, ProviderConnectionTestResult } from "../types/provider";
// Zustand store
export { useDreamStore } from "./DreamStore";
export type { AgentState, DreamStoreState } from "./DreamStore";

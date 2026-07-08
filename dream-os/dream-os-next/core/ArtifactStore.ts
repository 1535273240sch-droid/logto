/**
 * ArtifactStore — 成果存储
 *
 * 所有成果自动归档进入 Artifact Vault。
 * 按日期、项目、类型自动分类。
 * 支持：继续编辑、再次执行、重新部署、下载、删除。
 */

import { Artifact } from "../types/dream";

type GroupBy = "date" | "project" | "type";

interface ArtifactGroup {
  key: string;
  label: string;
  artifacts: Artifact[];
}

export class ArtifactStore {
  private static _instance: ArtifactStore;
  private _artifacts: Artifact[] = [];
  private _listeners: Array<() => void> = [];

  private constructor() {}

  static getInstance(): ArtifactStore {
    if (!ArtifactStore._instance) {
      ArtifactStore._instance = new ArtifactStore();
    }
    return ArtifactStore._instance;
  }

  /** 添加成果 */
  add(artifact: Artifact): void {
    this._artifacts.unshift(artifact);
    this._notify();
  }

  /** 删除成果 */
  remove(id: string): void {
    this._artifacts = this._artifacts.filter((a) => a.id !== id);
    this._notify();
  }

  /** 获取全部成果 */
  getAll(): Artifact[] {
    return [...this._artifacts];
  }

  /** 按分组键获取 */
  getGrouped(by: GroupBy = "date"): ArtifactGroup[] {
    const groups = new Map<string, Artifact[]>();

    for (const artifact of this._artifacts) {
      let key: string;
      switch (by) {
        case "date":
          key = artifact.created_at.slice(0, 10); // YYYY-MM-DD
          break;
        case "project":
          key = artifact.project_id || "未分类";
          break;
        case "type":
          key = artifact.type;
          break;
      }
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(artifact);
    }

    return Array.from(groups.entries()).map(([key, artifacts]) => ({
      key,
      label: key,
      artifacts,
    }));
  }

  /** 数量 */
  get count(): number {
    return this._artifacts.length;
  }

  /** 监听变化 */
  subscribe(listener: () => void): () => void {
    this._listeners.push(listener);
    return () => {
      this._listeners = this._listeners.filter((l) => l !== listener);
    };
  }

  private _notify(): void {
    for (const listener of this._listeners) {
      try { listener(); } catch (err) {
        console.error("[ArtifactStore] Listener error:", err);
      }
    }
  }
}

export const artifactStore = ArtifactStore.getInstance();
export default artifactStore;

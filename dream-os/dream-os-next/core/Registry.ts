/**
 * Registry — 统一注册中心
 *
 * 新增功能：只注册，不修改核心。
 * Core 永远不知道 Feature 的存在，只提供能力。
 * Feature 依赖 Core，Core 不依赖 Feature。
 *
 * Registry 统一管理：
 * - Feature （完整能力：chat/dev/plugin/ppt...）
 * - Plugin （工具插件）
 * - Renderer （成果渲染器）
 * - Command （命令）
 */

import { Feature, FeatureDescriptor } from "../types/dream";

export class Registry {
  private static _instance: Registry;

  private _features: Map<string, Feature> = new Map();
  private _featureDescriptors: Map<string, FeatureDescriptor> = new Map();

  private constructor() {}

  static getInstance(): Registry {
    if (!Registry._instance) {
      Registry._instance = new Registry();
    }
    return Registry._instance;
  }

  /** 注册 Feature */
  registerFeature(feature: Feature): void {
    const descriptor = feature.descriptor;
    this._features.set(descriptor.id, feature);
    this._featureDescriptors.set(descriptor.id, descriptor);
    console.debug(`[Registry] Feature registered: ${descriptor.id}`);
  }

  /** 获取 Feature */
  getFeature(id: string): Feature | undefined {
    return this._features.get(id);
  }

  /** 获取所有 Feature 描述符 */
  listFeatures(): FeatureDescriptor[] {
    return Array.from(this._featureDescriptors.values());
  }

  /** 是否有此 Feature */
  hasFeature(id: string): boolean {
    return this._features.has(id);
  }

  /** 取消注册 */
  unregisterFeature(id: string): void {
    this._features.delete(id);
    this._featureDescriptors.delete(id);
  }

  /** 获取全部 Feature 数量 */
  get count(): number {
    return this._features.size;
  }
}

export const registry = Registry.getInstance();
export default registry;

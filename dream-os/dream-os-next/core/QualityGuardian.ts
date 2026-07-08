/**
 * Quality Guardian — 质量守护者
 *
 * 所有模块开发、注册、修改必须通过 Quality Guardian。
 * 检查项：
 * 1. 架构合规性（Core → Registry → Feature）
 * 2. 模块边界（禁止跨模块直接调用）
 * 3. Feature 注册合法性
 * 4. 事件协议合规性
 * 5. 设计语言合规性
 */

import { Feature, FeatureDescriptor } from "../types/dream";
import { DEPEventType } from "../types/dep";
import { theme } from "./Theme";

export interface GuardResult {
  passed: boolean;
  errors: string[];
  warnings: string[];
}

export class QualityGuardian {
  private static _instance: QualityGuardian;
  private _failedChecks: GuardResult[] = [];

  private constructor() {}

  static getInstance(): QualityGuardian {
    if (!QualityGuardian._instance) {
      QualityGuardian._instance = new QualityGuardian();
    }
    return QualityGuardian._instance;
  }

  // ── Feature 注册检查 ──

  checkFeatureRegistration(feature: Feature): GuardResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    const desc = feature.descriptor;

    // 1. 必须提供完整 descriptor
    if (!desc.id) errors.push("Feature 缺少 id");
    if (!desc.name) errors.push("Feature 缺少 name");
    if (!desc.description) warnings.push("Feature 缺少 description");
    if (!desc.icon) warnings.push("Feature 缺少 icon");

    // 2. Feature ID 必须是唯一的小写字符串
    if (desc.id && !/^[a-z_]+$/.test(desc.id)) {
      errors.push(`Feature id "${desc.id}" 必须是小写字母和下划线`);
    }

    // 3. 必须提供 renderer
    if (!feature.renderer) {
      errors.push(`Feature "${desc.id}" 缺少 renderer`);
    }

    // 4. 必须提供 artifact renderer
    if (!feature.artifactRenderer) {
      warnings.push(`Feature "${desc.id}" 缺少 artifactRenderer`);
    }

    const result: GuardResult = {
      passed: errors.length === 0,
      errors,
      warnings,
    };

    this._failedChecks.push(result);
    return result;
  }

  // ── 模块边界检查 ──

  checkModuleBoundary(caller: string, target: string): GuardResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Feature 不能直接调用 Feature
    if (caller.startsWith("features/") && target.startsWith("features/")) {
      errors.push(
        `跨 Feature 调用禁止: ${caller} → ${target}。请使用 EventBus 通信。`
      );
    }

    // Core 不能调用 Feature
    if (caller.startsWith("core/") && target.startsWith("features/")) {
      errors.push(
        `Core 禁止调用 Feature: ${caller} → ${target}。违反 DAS 架构原则。`
      );
    }

    const result: GuardResult = {
      passed: errors.length === 0,
      errors,
      warnings,
    };

    this._failedChecks.push(result);
    return result;
  }

  // ── 事件协议检查 ──

  checkEventProtocol(eventType: string): GuardResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    const validTypes = Object.values(DEPEventType) as string[];
    if (!validTypes.includes(eventType)) {
      errors.push(
        `事件类型 "${eventType}" 不在 DEP 中。有效类型: ${validTypes.join(", ")}`
      );
    }

    const result: GuardResult = {
      passed: errors.length === 0,
      errors,
      warnings,
    };

    this._failedChecks.push(result);
    return result;
  }

  // ── 设计语言检查 ──

  checkDesignTokens(style: Record<string, string | number>): GuardResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // 检查是否使用了硬编码颜色（非 Theme Token）
    const colorValues = Object.values(style).filter(
      (v) => typeof v === "string" && v.startsWith("#")
    );

    const knownColors = new Set(Object.values(theme.colors));
    for (const color of colorValues) {
      if (!knownColors.has(color as string)) {
        warnings.push(
          `使用了非 Theme Token 颜色: ${color}。请使用 color() 函数。`
        );
      }
    }

    const result: GuardResult = {
      passed: errors.length === 0,
      errors,
      warnings,
    };

    this._failedChecks.push(result);
    return result;
  }

  // ── 全量检查 ──

  runAllChecks(): GuardResult {
    const allErrors: string[] = [];
    const allWarnings: string[] = [];

    for (const check of this._failedChecks) {
      allErrors.push(...check.errors);
      allWarnings.push(...check.warnings);
    }

    return {
      passed: allErrors.length === 0,
      errors: allErrors,
      warnings: allWarnings,
    };
  }

  // ── 获取检查历史 ──

  getHistory(): GuardResult[] {
    return [...this._failedChecks];
  }

  clearHistory(): void {
    this._failedChecks = [];
  }
}

export const qualityGuardian = QualityGuardian.getInstance();
export default qualityGuardian;

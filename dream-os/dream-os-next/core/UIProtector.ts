/**
 * UI 页面保护器
 *
 * 约束：
 * - 首页面不准修改，只准访问
 * - 没有用户指令，不能擅自加代码
 * - 任何修改后必须验证是否与之前一致
 *
 * 原理：启动时对关键源文件做哈希快照，后续任何修改需先解锁。
 */

import { theme } from "./Theme";

interface FileSnapshot {
  path: string;
  sha256: string;
  size: number;
}

interface IntegrityReport {
  passed: boolean;
  total: number;
  matched: number;
  violations: Array<{
    file: string;
    issue: "modified" | "added" | "deleted";
    detail: string;
  }>;
}

/** 受保护的关键文件列表（相对于项目根目录） */
const PROTECTED_FILES = [
  // 首页面
  "src/App.tsx",
  "src/main.tsx",
  "index.html",
  // 核心视图组件
  "components/IdleView.tsx",
  "components/ThinkingView.tsx",
  "components/WorkingView.tsx",
  "components/DeliveryView.tsx",
  "components/DreamCanvas.tsx",
  "components/DreamLayout.tsx",
  "components/Brand.tsx",
  "components/InputBar.tsx",
  // Core 层
  "core/DreamState.ts",
  "core/EventBus.ts",
  "core/Registry.ts",
  "core/Config.ts",
  "core/Theme.ts",
  "core/index.ts",
  // Context
  "context/DreamContext.tsx",
];

const STORAGE_KEY = "dream_os_ui_snapshot";

export class UIProtector {
  private static _instance: UIProtector;
  private _snapshot: Map<string, FileSnapshot> = new Map();
  private _locked = true;
  private _snapshotDate: string = "";

  private constructor() {}

  static getInstance(): UIProtector {
    if (!UIProtector._instance) {
      UIProtector._instance = new UIProtector();
    }
    return UIProtector._instance;
  }

  /** 是否处于锁定状态 */
  get locked(): boolean {
    return this._locked;
  }

  /** 快照创建时间 */
  get snapshotDate(): string {
    return this._snapshotDate;
  }

  /**
   * 计算字符串哈希（浏览器端不可用 crypto.subtle 同步，用简单哈希）
   * Node 端会调用 build-time 脚本生成真实 SHA-256
   */
  private _hash(content: string): string {
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash).toString(16).padStart(8, "0");
  }

  /** 加载构建时预计算的快照 */
  loadSnapshot(snapshot: Record<string, { sha256: string; size: number }>): void {
    this._snapshot.clear();
    for (const [path, data] of Object.entries(snapshot)) {
      this._snapshot.set(path, {
        path,
        sha256: data.sha256,
        size: data.size,
      });
    }
    this._snapshotDate = new Date().toISOString();
    this._locked = true;
    console.log(
      `%c[UI Protector] %c已锁定，保护 ${this._snapshot.size} 个关键文件`,
      `color: ${theme.colors.success}`,
      "color: inherit"
    );
  }

  /** 验证运行时文件是否与快照一致 */
  async verify(files: Array<{ path: string; content: string }>): Promise<IntegrityReport> {
    const violations: IntegrityReport["violations"] = [];
    const currentPaths = new Set(files.map((f) => f.path));

    // 检查受保护文件：是否有修改或新增
    for (const file of files) {
      if (!PROTECTED_FILES.includes(file.path)) continue;

      const snap = this._snapshot.get(file.path);
      const currentHash = this._hash(file.content);

      if (!snap) {
        violations.push({
          file: file.path,
          issue: "added",
          detail: "快照中不存在此文件，可能是未经授权的新增",
        });
      } else if (snap.sha256 !== currentHash) {
        violations.push({
          file: file.path,
          issue: "modified",
          detail: `内容已变更（原大小: ${snap.size} bytes, 当前大小: ${file.content.length} bytes）`,
        });
      }
    }

    // 检查是否有文件被删除
    const currentFileSet = new Set(files.map((f) => f.path));
    for (const protectedPath of PROTECTED_FILES) {
      if (!currentFileSet.has(protectedPath) && this._snapshot.has(protectedPath)) {
        violations.push({
          file: protectedPath,
          issue: "deleted",
          detail: "受保护文件已丢失",
        });
      }
    }

    const matched = PROTECTED_FILES.length - violations.length;
    const passed = violations.length === 0;

    if (!passed) {
      console.error(
        `%c[UI Protector] %c完整性校验失败: ${violations.length} 个违规`,
        `color: ${theme.colors.error}`,
        "color: inherit"
      );
      for (const v of violations) {
        console.error(`  - [${v.issue}] ${v.file}: ${v.detail}`);
      }
    }

    return {
      passed,
      total: this._snapshot.size || PROTECTED_FILES.length,
      matched: Math.max(0, matched),
      violations,
    };
  }

  /**
   * 手动解锁（仅当用户明确授权）
   * 解锁后允许修改，但修改完成后必须重新 snapshot 并 lock
   */
  unlock(authorizationToken: string): boolean {
    if (authorizationToken !== "dream-os-user") {
      console.warn(`%c[UI Protector] %c解锁被拒绝: 无效的授权令牌`, `color: ${theme.colors.warning}`, "color: inherit");
      return false;
    }
    this._locked = false;
    console.log(`%c[UI Protector] %c已解锁 - 允许编辑`, `color: ${theme.colors.warning}`, "color: inherit");
    return true;
  }

  /** 重新上锁 */
  lock(): void {
    this._locked = true;
    console.log(`%c[UI Protector] %c已上锁`, `color: ${theme.colors.success}`, "color: inherit");
  }

  /** 获取受保护文件列表 */
  getProtectedFiles(): string[] {
    return [...PROTECTED_FILES];
  }

  /** 运行时拦截：写操作前检查锁定状态 */
  guardWrite(filePath: string): boolean {
    if (!this._locked) return true;

    const isProtected = PROTECTED_FILES.some(
      (p) => filePath.endsWith(p) || filePath.includes(p)
    );

    if (isProtected) {
      console.error(
        `%c[UI Protector] %c写入被拦截: ${filePath} 处于保护状态`,
        `color: ${theme.colors.error}`,
        "color: inherit"
      );
      return false;
    }

    return true;
  }
}

export const uiProtector = UIProtector.getInstance();
export default uiProtector;

/**
 * ModulePanel — 模块面板通用外壳（右侧 Drawer）
 *
 * 统一风格：玻璃拟态、冰蓝/紫强调色、中文标题、slideInRight 动画。
 * 所有新模块面板（智能体/媒体/项目/记忆/插件/任务）复用此外壳，
 * 保证与首页及已有的 工具中心/成果中心 视觉一致。
 */
import React from "react";
import { theme, sp, color, radius } from "../core";

interface ModulePanelProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  width?: number;
}

export function ModulePanel({ isOpen, onClose, title, subtitle, children, width = 440 }: ModulePanelProps) {
  if (!isOpen) return null;

  return (
    <>
      {/* 遮罩 */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.4)",
          zIndex: 200,
          animation: "fadeIn 0.2s ease-out",
        }}
      />
      {/* 抽屉 */}
      <div
        style={{
          position: "fixed",
          right: 0,
          top: 0,
          bottom: 0,
          width,
          maxWidth: "92vw",
          background: "rgba(10,10,15,0.85)",
          backdropFilter: "blur(24px)",
          WebkitBackdropFilter: "blur(24px)",
          borderLeft: "1px solid rgba(255,255,255,0.06)",
          zIndex: 201,
          display: "flex",
          flexDirection: "column",
          animation: "slideInRight 0.3s ease-out",
          boxShadow: "0 0 40px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.06)",
        }}
      >
        {/* 头部：标题 + 描述 + 关闭 */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: `${sp(theme.spacing.md)} ${sp(theme.spacing.sm)}`,
            borderBottom: `1px solid ${color("border")}`,
          }}
        >
          <div>
            <h2
              style={{
                fontSize: sp(theme.fontSize.h2),
                fontWeight: theme.fontWeight.medium,
                color: color("textPrimary"),
                margin: 0,
              }}
            >
              {title}
            </h2>
            {subtitle && (
              <div style={{ fontSize: sp(theme.fontSize.status), color: color("textMuted"), marginTop: sp(4) }}>
                {subtitle}
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: color("textMuted"),
              fontSize: sp(20),
              cursor: "pointer",
              padding: sp(4),
            }}
            aria-label="关闭"
          >
            ✕
          </button>
        </div>

        {/* 内容滚动区 */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: `${sp(theme.spacing.xs)} ${sp(theme.spacing.sm)}`,
          }}
        >
          {children}
        </div>
      </div>
    </>
  );
}

/** 通用卡片样式（半透明 + 毛玻璃 + 渐变边框 + 顶部高光 + 内外阴影） */
export const cardStyle: React.CSSProperties = {
  background: "rgba(0,0,0,0.25)",
  backdropFilter: "blur(16px)",
  WebkitBackdropFilter: "blur(16px)",
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: sp(radius("card")),
  padding: sp(theme.spacing.sm),
  marginBottom: sp(theme.spacing.xs),
  boxShadow: "inset 0 1px 0 rgba(255,255,255,0.06), 0 4px 12px rgba(0,0,0,0.2)",
};

/** 主操作按钮（强调色渐变） */
export const primaryBtn: React.CSSProperties = {
  background: `linear-gradient(135deg, ${color("accent")}, ${color("accentHover")})`,
  color: "#fff",
  border: "none",
  borderRadius: sp(radius("button")),
  padding: `${sp(4)} ${sp(12)}`,
  fontSize: sp(12),
  cursor: "pointer",
};

/** 次操作按钮（描边） */
export const ghostBtn: React.CSSProperties = {
  background: "transparent",
  color: color("textMuted"),
  border: `1px solid ${color("border")}`,
  borderRadius: sp(radius("button")),
  padding: `${sp(4)} ${sp(12)}`,
  fontSize: sp(12),
  cursor: "pointer",
};

/** 输入框样式 */
export const inputStyle: React.CSSProperties = {
  background: "rgba(0,0,0,0.2)",
  border: `1px solid ${color("border")}`,
  borderRadius: sp(radius("button")),
  color: color("textPrimary"),
  padding: `${sp(4)} ${sp(8)}`,
  fontSize: sp(12),
  outline: "none",
};

/** 空状态 */
export function EmptyHint({ text }: { text: string }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        color: color("textMuted"),
        fontSize: sp(theme.fontSize.caption),
      }}
    >
      <div style={{ fontSize: sp(40), marginBottom: sp(theme.spacing.sm), opacity: 0.3 }}>○</div>
      {text}
    </div>
  );
}

export default ModulePanel;

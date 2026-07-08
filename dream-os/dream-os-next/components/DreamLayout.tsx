/**
 * DreamLayout — 全局固定布局
 *
 * DAS 规定：Dream OS 全局固定布局，布局永远保持稳定。变化的是内容，不是布局。
 *
 * 布局结构：
 * ┌─────────────────────────────────────────────────┐
 * │  Logo + 理念                模型 | Artifact | 设置  │
 * ├─────────────────────────────────────────────────┤
 * │                                           │
 * │              Dream Canvas (内容区)                │
 * │                                           │
 * ├─────────────────────────────────────────────────┤
 * │ 输入框（底部固定）                                  │
 * └─────────────────────────────────────────────────┘
 */

import React, { useState } from "react";
import { theme, sp, color, radius } from "../core";
import { useDreamContext } from "../context/DreamContext";

interface DreamLayoutProps {
  children: React.ReactNode;
}

export function DreamLayout({ children }: DreamLayoutProps) {
  const { dreamState } = useDreamContext();
  const snapshot = dreamState.getSnapshot();

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        backgroundColor: color("bgPrimary"),
        background: `
          radial-gradient(ellipse at 50% 50%, rgba(${parseInt(color("accent").slice(1), 16)}, 0.03) 0, transparent 70%),
          radial-gradient(ellipse at 30% 70%, rgba(${parseInt(color("accent").slice(1), 16)}, 0.02) 0, transparent 60%),
          radial-gradient(ellipse at 70% 30%, rgba(${parseInt(color("accent").slice(1), 16)}, 0.02) 0, transparent 60%)
        `,
        backgroundSize: "200% 200%",
        animation: "dreamField 16s ease-in-out infinite",
      }}
    >
      {/* Top Bar */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: `${sp(theme.spacing.md)} ${sp(theme.spacing.sm)}`,
        }}
      >
        <div style={{ paddingLeft: sp(theme.spacing.sm) }}>
          <h1
            style={{
              fontSize: sp(theme.fontSize.logo),
              fontWeight: theme.fontWeight.medium,
              color: color("textPrimary"),
              letterSpacing: "4px",
              margin: 0,
            }}
          >
            Dream OS
          </h1>
          <p
            style={{
              fontSize: sp(theme.fontSize.caption),
              color: color("textMuted"),
              fontWeight: theme.fontWeight.regular,
              marginTop: sp(4),
              marginBottom: 0,
            }}
          >
            把想法交给我，把时间留给你
          </p>
        </div>
        <div
          style={{
            display: "flex",
            gap: sp(theme.spacing.xs),
            alignItems: "flex-start",
            paddingRight: sp(theme.spacing.sm),
          }}
        >
          {/* Controls are injected here */}
          {children.props?.controls}
        </div>
      </header>

      {/* Main Content — Dream Canvas */}
      <main
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          overflowY: "auto",
          overflowX: "hidden",
          paddingBottom: sp(theme.spacing.lg),
        }}
      >
        {children}
      </main>
    </div>
  );
}

export default DreamLayout;

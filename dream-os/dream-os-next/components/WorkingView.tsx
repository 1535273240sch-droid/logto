/**
 * Working View — 8 数字员工动画面板
 *
 * 极简风：8 个 CSS 绘制的线条小人坐在电脑桌前，
 * 2x4 网格排列，状态区分运行/待命/完成。
 * 页面入场：Logo 先淡入，小人从底部依次升起，瞬间闪烁工作光。
 */

import React from "react";
import { theme, sp, color, radius } from "../core";
import { useDreamContext } from "../context/DreamContext";
import { AgentStatus } from "../types/dream";
import { Brand } from "./Brand";
import { InputBar } from "./InputBar";

// ── 8 位数字员工定义 ──

const DEV_AGENTS = [
  { key: "planner",   label: "规划师" },
  { key: "architect", label: "架构师" },
  { key: "coder",     label: "程序员" },
  { key: "executor",  label: "执行者" },
  { key: "reviewer",  label: "审查员" },
  { key: "tester",    label: "测试员" },
  { key: "deployer",  label: "部署员" },
  { key: "reporter",  label: "报告员" },
];

// ── 极简线条小人（纯 CSS） ──

interface StickFigureProps {
  status: string;
  flashDelay: number;
}

function StickFigure({ status, flashDelay }: StickFigureProps) {
  const isRunning = status === "running";
  const isDone = status === "done";
  const isPending = status === "pending" || status === "waiting";

  const lineColor = isPending
    ? "rgba(255,255,255,0.12)"
    : isDone
    ? "rgba(255,255,255,0.35)"
    : "rgba(255,255,255,0.75)";

  return (
    <div style={{ position: "relative", width: 80, height: 72 }}>
      {/* Head */}
      <div
        style={{
          position: "absolute", top: 0, left: "50%", marginLeft: -4,
          width: 8, height: 8, borderRadius: "50%",
          border: `1px solid ${lineColor}`,
          opacity: isPending ? 0.4 : 1,
        }}
      />

      {/* Body */}
      <div
        style={{
          position: "absolute", top: 9, left: "50%",
          width: 0, height: 14,
          borderLeft: `1px solid ${lineColor}`,
          opacity: isPending ? 0.4 : 1,
        }}
      />

      {/* Left arm */}
      <div
        style={{
          position: "absolute", top: 16, left: "50%",
          width: 12, height: 0,
          borderTop: `1px solid ${lineColor}`,
          transformOrigin: "0 0",
          transform: "rotate(-25deg)",
          animation: isRunning ? "typingArmL 0.8s ease-in-out infinite" : "none",
          opacity: isPending ? 0.4 : 1,
        }}
      />

      {/* Right arm */}
      <div
        style={{
          position: "absolute", top: 16, left: "50%",
          width: 12, height: 0,
          borderTop: `1px solid ${lineColor}`,
          transformOrigin: "0 0",
          transform: "rotate(25deg)",
          animation: isRunning ? "typingArmR 0.8s ease-in-out infinite" : "none",
          opacity: isPending ? 0.4 : 1,
        }}
      />

      {/* Desk */}
      <div
        style={{
          position: "absolute", bottom: 18, left: "50%", marginLeft: -22,
          width: 44, height: 0,
          borderTop: `1px solid ${lineColor}`,
          opacity: isPending ? 0.2 : 0.5,
        }}
      />

      {/* Screen */}
      <div
        style={{
          position: "absolute", bottom: 20, left: "50%", marginLeft: -10,
          width: 20, height: 14,
          border: `1px solid ${lineColor}`,
          borderRadius: 2,
          background: isRunning ? "rgba(108,92,231,0.06)" : "transparent",
          boxShadow: isRunning ? "0 0 6px rgba(108,92,231,0.18)" : "none",
          animation: isRunning
            ? `screenGlow 2.5s ease-in-out infinite, agentFlash 1.2s ease-out ${flashDelay}s`
            : `agentFlash 1.2s ease-out ${flashDelay}s`,
          opacity: isPending ? 0.3 : 1,
        }}
      />

      {/* Cursor */}
      {isRunning && (
        <div
          style={{
            position: "absolute", bottom: 22, left: "50%", marginLeft: 2,
            width: 1, height: 8,
            background: "rgba(108,92,231,0.6)",
            animation: "cursorBlink 0.8s step-end infinite",
          }}
        />
      )}
    </div>
  );
}

// ── 主视图 ──

interface WorkingViewProps {
  disabled: boolean;
  onCancel: () => void;
}

export function WorkingView({ disabled, onCancel }: WorkingViewProps) {
  const { dreamState } = useDreamContext();
  const snapshot = dreamState.getSnapshot();
  const { agents, content } = snapshot;

  const agentMap: Record<string, string> = {};
  agents.forEach((a: AgentStatus) => {
    agentMap[a.agent] = a.status;
  });

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        width: "100%",
        paddingBottom: sp(theme.spacing.lg),
        overflowY: "auto",
        overflowX: "hidden",
      }}
    >
      {/* Logo — 缓慢呼吸放大 */}
      <div style={{ animation: "logoBreathe 6s ease-in-out infinite" }}>
        <Brand />
      </div>

      {/* 2x4 数字员工网格 */}
      <div
        style={{
          width: "100%",
          maxWidth: 620,
          padding: `0 ${sp(theme.spacing.md)}`,
          marginTop: sp(theme.spacing.xxxl),
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: `${sp(theme.spacing.xl)} ${sp(theme.spacing.sm)}`,
            justifyItems: "center",
          }}
        >
          {DEV_AGENTS.map((agent, idx) => {
            const status = agentMap[agent.key] || "pending";
            const riseDelay = 0.3 + idx * 0.08;
            const flashDelay = riseDelay + 0.8;

            return (
              <div
                key={agent.key}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: sp(10),
                  animation: `agentRise 0.8s cubic-bezier(0.16, 1, 0.3, 1) ${riseDelay}s both`,
                }}
              >
                <StickFigure status={status} flashDelay={flashDelay} />

                <span
                  style={{
                    fontSize: sp(10),
                    color:
                      status === "running"
                        ? color("accentLight")
                        : status === "done"
                        ? color("textMuted")
                        : "rgba(255,255,255,0.18)",
                    fontWeight: status === "running" ? 500 : 400,
                    letterSpacing: "1px",
                    transition: "color 0.6s ease",
                  }}
                >
                  {agent.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 流式内容 */}
      {content && (
        <div
          style={{
            width: "100%",
            maxWidth: 560,
            padding: `0 ${sp(theme.spacing.md)}`,
            marginTop: sp(theme.spacing.xl),
          }}
        >
          <div
            style={{
              background: "rgba(255,255,255,0.015)",
              backdropFilter: "blur(16px)",
              borderRadius: sp(radius("card")),
              padding: sp(theme.spacing.sm),
              fontSize: sp(theme.fontSize.body),
              color: color("textPrimary"),
              lineHeight: "1.8",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              animation: "fadeInUp 0.5s ease-out",
              border: "1px solid rgba(255,255,255,0.03)",
            }}
          >
            {content}
            <span
              style={{
                display: "inline-block", width: 2, height: sp(16),
                background: color("accentLight"), marginLeft: sp(2),
                animation: "pulse 1s infinite",
                verticalAlign: "text-bottom", borderRadius: 1,
              }}
            />
          </div>
        </div>
      )}

      {/* 底部输入框 */}
      <div style={{ marginTop: sp(24) }}>
        <InputBar
          placeholder="Dream OS 正在执行..."
          disabled={disabled}
          onSubmit={() => {}}
          onCancel={onCancel}
        />
      </div>

      <div style={{ flex: 1 }} />
    </div>
  );
}

export default WorkingView;
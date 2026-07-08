import React from "react";
import { theme, sp, color, radius } from "../core";
import { useDreamContext } from "../context/DreamContext";
import { Artifact } from "../types/dream";
import { Brand } from "./Brand";
import { InputBar } from "./InputBar";

interface DeliveryViewProps {
  onSubmit: (value: string, mode?: string) => void;
}

const ACTION_LABELS: Record<string, string> = {
  website: "打开网站",
  ppt: "在线预览",
  image: "下载图片",
  document: "在线阅读",
  code: "查看源码",
};

export function DeliveryView({ onSubmit }: DeliveryViewProps) {
  const { dreamState } = useDreamContext();
  const snapshot = dreamState.getSnapshot();
  const { artifacts, content } = snapshot;

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
      <Brand />

      <div
        style={{
          width: "100%",
          maxWidth: 560,
          padding: `0 ${sp(theme.spacing.md)}`,
          marginTop: sp(theme.spacing.md),
        }}
      >
        <div
          style={{
            background: "rgba(255,255,255,0.015)",
            backdropFilter: "blur(16px)",
            borderRadius: sp(radius("cardLarge")),
            padding: sp(theme.spacing.md),
            animation: "fadeInUp 0.5s ease-out",
            border: "1px solid rgba(255,255,255,0.03)",
          }}
        >
          <div
            style={{
              fontSize: sp(11), fontWeight: 500, color: color("textMuted"),
              marginBottom: sp(theme.spacing.sm), textTransform: "uppercase",
              letterSpacing: "1px", opacity: 0.6,
            }}
          >
            任务完成
          </div>

          {content && (
            <div
              style={{
                fontSize: sp(theme.fontSize.body), color: color("textPrimary"),
                lineHeight: "1.8", whiteSpace: "pre-wrap", wordBreak: "break-word",
                marginBottom: sp(theme.spacing.md),
              }}
            >
              {content}
            </div>
          )}

          {artifacts.map((artifact: Artifact) => {
            const actionLabel = ACTION_LABELS[artifact.type] || "打开成果";
            return (
              <div
                key={artifact.id}
                style={{
                  padding: sp(theme.spacing.sm), borderRadius: sp(radius("card")),
                  background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.04)",
                  marginBottom: sp(theme.spacing.xs),
                }}
              >
                <div style={{ fontSize: sp(theme.fontSize.body), fontWeight: 500, color: color("textPrimary"), marginBottom: sp(theme.spacing.xs) }}>
                  {artifact.name}
                </div>
                {artifact.preview_url && (
                  <button
                    style={{
                      background: "linear-gradient(135deg, #6c5ce7, #a29bfe)", color: "#fff",
                      border: "none", borderRadius: sp(radius("button")),
                      padding: `${sp(8)} ${sp(18)}`, fontSize: sp(theme.fontSize.caption),
                      cursor: "pointer", boxShadow: "0 4px 16px rgba(108,92,231,0.3)",
                    }}
                    onClick={() => window.open(artifact.preview_url, "_blank")}
                  >
                    {actionLabel}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ marginTop: sp(24) }}>
        <InputBar placeholder="继续输入下一个目标..." onSubmit={onSubmit} />
      </div>
      <div style={{ flex: 1 }} />
    </div>
  );
}

export default DeliveryView;

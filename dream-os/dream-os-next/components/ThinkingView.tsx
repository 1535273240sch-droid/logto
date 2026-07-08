import React from "react";
import { theme, sp, color } from "../core";
import { Brand } from "./Brand";
import { InputBar } from "./InputBar";

interface ThinkingViewProps {
  message: string;
  disabled: boolean;
  onCancel: () => void;
}

export function ThinkingView({ message, disabled, onCancel }: ThinkingViewProps) {
  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        paddingBottom: "8vh",
      }}
    >
      <Brand />

      <div
        style={{
          marginTop: sp(theme.spacing.lg),
          display: "flex",
          alignItems: "center",
          gap: sp(10),
          animation: "fadeInUp 0.6s ease-out",
        }}
      >
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            style={{
              width: 4, height: 4, borderRadius: "50%",
              backgroundColor: color("accentLight"),
              animation: `thinkingDot 1.6s ease-in-out ${i * 0.25}s infinite`,
            }}
          />
        ))}
        <span style={{ fontSize: sp(14), color: color("textSecondary"), fontWeight: 400, marginLeft: sp(6) }}>
          {message}
        </span>
      </div>

      <div style={{ marginTop: sp(24) }}>
        <InputBar placeholder="Dream OS 正在思考..." disabled={disabled} onSubmit={() => {}} onCancel={onCancel} />
      </div>
      <div style={{ flex: 1 }} />
    </div>
  );
}

export default ThinkingView;

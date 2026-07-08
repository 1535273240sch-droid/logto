/**
 * Brand — Logo + 产品理念文案
 *
 * Idle: 大字号居中 + 完整文案
 * Thinking/Working/Delivery: 极简小字，右上区域，不遮挡内容
 */

import React from "react";
import { theme, sp, color } from "../core";
import { useDreamContext } from "../context/DreamContext";
import { DreamStateVariant } from "../types/dream";

interface BrandProps {
  isTyping?: boolean;
}

const TAGLINE = "我们相信，\nAI 的价值，不在于回答问题。\n而在于帮助人真正完成目标。\n\nDream OS，\n致力于把一句目标，\n变成最终成果。";

export function Brand({ isTyping = false }: BrandProps) {
  const { dreamState } = useDreamContext();
  const snapshot = dreamState.getSnapshot();
  const isIdle = snapshot.state === DreamStateVariant.IDLE;

  const showTagline = isIdle && !isTyping;

  // Idle: centered, large
  // Non-idle: small, subtle, top area
  return (
    <div
      style={{
        marginTop: isIdle && !isTyping ? "16vh" : isIdle ? "12vh" : "0.5vh",
        transition: "margin-top 0.8s cubic-bezier(0.4, 0, 0.2, 1)",
        textAlign: "center",
        position: "relative",
        zIndex: 1,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          fontSize: sp(isIdle && !isTyping ? 30 : 11),
          fontWeight: 500,
          color: color(isIdle ? "textPrimary" : "textMuted"),
          letterSpacing: isIdle && !isTyping ? "5px" : "2px",
          transition: "all 0.8s cubic-bezier(0.4, 0, 0.2, 1)",
          marginBottom: sp(4),
          opacity: isIdle ? 0.9 : 0.25,
          fontFamily: "'SF Pro Display', -apple-system, sans-serif",
        }}
      >
        Dream OS
      </div>

      {showTagline && (
        <div
          style={{
            fontSize: sp(12),
            color: color("textMuted"),
            fontWeight: 300,
            lineHeight: "1.9",
            opacity: 0.55,
            whiteSpace: "pre-line",
            marginTop: sp(16),
            animation: "fadeIn 0.8s ease-out",
          }}
        >
          {TAGLINE}
        </div>
      )}
    </div>
  );
}

export default Brand;

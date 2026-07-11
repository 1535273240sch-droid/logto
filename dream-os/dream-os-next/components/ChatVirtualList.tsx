/**
 * ChatVirtualList — 聊天虚拟滚动列表
 *
 * 使用 @tanstack/react-virtual 动态高度模式（measureElement），
 * 只渲染可视区域内的消息，解决「聊多了页面堆积、渲染卡顿」的问题。
 *
 * 视觉规范（与主页 InputBar 完全统一）：
 * - 外层 1px padding 技巧做紫色渐变描边
 * - 内层 rgba 玻璃背景 + blur(28px)
 * - 顶部 1px 高光（linear-gradient white → 透明）
 * - 胶囊形：borderRadius 28（与 InputBar 一致）
 * - 阴影：内/外组合
 *
 * 打字机特效：
 * - 流式输出时（live item + content 增长），字符逐个出现
 * - 内容到达时自动重置可见长度
 * - 末尾闪烁光标（cursorBlink）
 */

import React, { useRef, useEffect, useMemo } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { theme, sp, color, radius } from "../core";
import { Artifact } from "../types/dream";

export interface ChatItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  artifacts?: Artifact[];
  ts: number;
  /** 当前是否在流式输出（打字机效果用） */
  streaming?: boolean;
}

interface ChatVirtualListProps {
  items: ChatItem[];
  onArtifactOpen?: (url: string) => void;
}

// ─── 视觉常量（与 InputBar 完全一致） ───
const BORDER_GRADIENT = "linear-gradient(135deg, rgba(108,92,231,0.55) 0%, rgba(162,155,254,0.20) 50%, rgba(255,255,255,0.05) 100%)";
const INNER_BG = "rgba(0,0,0,0.35)";
const TOP_HIGHLIGHT = "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.14) 50%, transparent 100%)";

// AI 气泡专用：与主页 InputBar 完全一致的胶囊尺寸
const AI_BORDER_GRADIENT = "linear-gradient(135deg, rgba(108,92,231,0.55) 0%, rgba(162,155,254,0.20) 50%, rgba(255,255,255,0.05) 100%)";
const AI_INNER_BG = "rgba(0,0,0,0.35)";
const AI_TOP_HIGHLIGHT = "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.14) 50%, transparent 100%)";
const BUBBLE_BOX_SHADOW = "inset 0 1px 0 rgba(255,255,255,0.06), 0 4px 18px rgba(0,0,0,0.28)";
const BUBBLE_BLUR = 28; // 与 InputBar 完全一致
const BUBBLE_RADIUS = 28; // 胶囊形，与 InputBar 一致

// 打字机光标 keyframe（使用内联 SVG 闪烁）
const CURSOR_BLINK = "cursorBlink 1s steps(1) infinite";

// ─── 单个气泡组件 ───
function ChatBubble({
  item,
  onArtifactOpen,
}: {
  item: ChatItem;
  onArtifactOpen?: (url: string) => void;
}) {
  const isUser = item.role === "user";

  // 打字机效果：流式输出时逐字渲染
  // - 首次挂载时若 streaming=true，从 0 开始（用于新一条 AI 消息）
  // - 首次挂载时若 streaming=false，显示全部（用于历史消息 + 思考态）
  // - 当 content 从空变成有内容时，触发 typewriter 重置
  const [visibleLen, setVisibleLen] = React.useState(item.streaming ? 0 : item.content.length);
  const [hasStartedTypewriter, setHasStartedTypewriter] = React.useState(
    item.streaming && item.content.length > 0
  );
  const isStreaming = !!item.streaming;
  const targetLen = item.content.length;
  const prevContentRef = React.useRef(item.content);

  // 当内容从空跳到有内容（思考态 → 流式开始），重置打字机
  useEffect(() => {
    if (
      isStreaming &&
      !hasStartedTypewriter &&
      targetLen > 0 &&
      prevContentRef.current !== item.content
    ) {
      setVisibleLen(0);
      setHasStartedTypewriter(true);
    }
    prevContentRef.current = item.content;
  }, [isStreaming, hasStartedTypewriter, targetLen, item.content]);

  useEffect(() => {
    if (!isStreaming) {
      setVisibleLen(targetLen);
      return;
    }
    // 流式：每 ~12ms 显示一个字符
    if (visibleLen < targetLen) {
      const timer = setTimeout(() => {
        setVisibleLen((prev) => Math.min(prev + 2, targetLen));
      }, 12);
      return () => clearTimeout(timer);
    }
  }, [visibleLen, targetLen, isStreaming]);

  // 实际可见的字符数（取 min，避免 visibleLen 越界时显示空）
  const effectiveVisibleLen = Math.min(visibleLen, targetLen);
  const displayedContent = item.content.slice(0, effectiveVisibleLen);
  const showCursor = isStreaming && effectiveVisibleLen >= targetLen;

  // 渐变描边背景（外层）—— 与 InputBar 一致：渐变 + 1px padding 技巧
  const borderBg = isUser
    ? `linear-gradient(135deg, ${color("accent")}, ${color("accentHover")})`
    : BORDER_GRADIENT;

  const innerBg = isUser ? "transparent" : INNER_BG;
  const topHighlight = isUser ? "none" : TOP_HIGHLIGHT;
  const radiusValue = BUBBLE_RADIUS; // 胶囊形，与 InputBar 一致

  return (
    <div
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        animation: "fadeInUp 0.3s ease-out",
      }}
    >
      <div
        style={{
          maxWidth: "84%",
          // 外层 1px 渐变描边
          background: borderBg,
          padding: 1,
          borderRadius: radiusValue,
          boxShadow: BUBBLE_BOX_SHADOW,
        }}
      >
        <div
          style={{
            background: innerBg,
            backdropFilter: `blur(${BUBBLE_BLUR}px)`,
            WebkitBackdropFilter: `blur(${BUBBLE_BLUR}px)`,
            borderRadius: radiusValue - 1,
            padding: `${sp(12)} ${sp(18)}`,
            // 顶部 1px 高光
            backgroundImage: topHighlight,
            backgroundRepeat: "no-repeat",
            backgroundSize: "100% 1px",
            backgroundPosition: "top",
            color: isUser ? "#fff" : color("textPrimary"),
            fontSize: sp(theme.fontSize.body),
            lineHeight: 1.7,
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
          }}
        >
          <span>{displayedContent}</span>
          {(isStreaming || showCursor) && (
            <span
              style={{
                display: "inline-block",
                width: 2,
                height: "1em",
                background: color("accentLight"),
                marginLeft: 2,
                verticalAlign: "text-bottom",
                animation: CURSOR_BLINK,
              }}
            />
          )}

          {item.artifacts && item.artifacts.length > 0 && effectiveVisibleLen >= targetLen && (
            <div style={{ marginTop: sp(10) }}>
              {item.artifacts.map((a: Artifact) => (
                <div
                  key={a.id}
                  style={{
                    background: "rgba(255,255,255,0.04)",
                    border: "1px solid rgba(255,255,255,0.06)",
                    borderRadius: sp(radius("card")),
                    padding: sp(8),
                    marginBottom: 6,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <span style={{ fontSize: 12 }}>{a.name}</span>
                  {a.preview_url && (
                    <button
                      onClick={() => onArtifactOpen?.(a.preview_url)}
                      style={{
                        background: `linear-gradient(135deg, ${color("accent")}, ${color("accentHover")})`,
                        color: "#fff",
                        border: "none",
                        borderRadius: sp(radius("button")),
                        padding: `2px 10px`,
                        fontSize: 11,
                        cursor: "pointer",
                      }}
                    >
                      打开
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function ChatVirtualList({ items, onArtifactOpen }: ChatVirtualListProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 80,
    overscan: 6,
    getItemKey: (index: number) => items[index].id,
  });

  // 新消息 / 流式内容增长时自动滚到底部
  const lastCount = useRef(items.length);
  const lastLen = useRef(0);
  useEffect(() => {
    const last = items[items.length - 1];
    const grew = last ? last.content.length : 0;
    if (items.length > lastCount.current || grew > lastLen.current) {
      virtualizer.scrollToIndex(items.length - 1, { align: "end" });
    }
    lastCount.current = items.length;
    lastLen.current = grew;
  }, [items, virtualizer]);

  return (
    <div
      ref={parentRef}
      style={{
        height: "100%",
        overflowY: "auto",
        overflowX: "hidden",
        // 顶部预留避开 HeaderControls
        padding: `80px ${sp(theme.spacing.md)} ${sp(theme.spacing.md)}`,
      }}
    >
      <div style={{ height: virtualizer.getTotalSize(), position: "relative", width: "100%" }}>
        {virtualizer.getVirtualItems().map((v) => {
          const item = items[v.index];
          return (
            <div
              key={item.id}
              data-index={v.index}
              ref={virtualizer.measureElement}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                transform: `translateY(${v.start}px)`,
                paddingBottom: sp(10),
              }}
            >
              <ChatBubble item={item} onArtifactOpen={onArtifactOpen} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ChatVirtualList;

/**
 * ChatVirtualList — 聊天虚拟滚动列表
 *
 * 使用 @tanstack/react-virtual 动态高度模式（measureElement），
 * 只渲染可视区域内的消息，解决「聊多了页面堆积、渲染卡顿」的问题。
 *
 * - 动态行高（每条消息高度不一，流式内容会增长）
 * - 新消息自动滚动到底部
 * - 用户消息右对齐（强调色气泡），AI 消息左对齐（深色玻璃 + 渐变边框，与主页风格一致）
 */
import React, { useRef, useEffect, useCallback } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { theme, sp, color, radius } from "../core";
import { Artifact } from "../types/dream";

export interface ChatItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  artifacts?: Artifact[];
  ts: number;
}

interface ChatVirtualListProps {
  items: ChatItem[];
  onArtifactOpen?: (url: string) => void;
}

// AI 气泡样式：深色玻璃 + 紫色渐变边框 + 顶部高光（与主页 InputBar 一致）
const AI_BUBBLE_BG = "rgba(10,10,18,0.55)";
const AI_BUBBLE_BORDER_GRAD = "linear-gradient(135deg, rgba(108,92,231,0.45) 0%, rgba(162,155,254,0.18) 50%, rgba(255,255,255,0.05) 100%)";
const AI_BUBBLE_BOX_SHADOW = "inset 0 1px 0 rgba(255,255,255,0.06), 0 4px 18px rgba(0,0,0,0.28)";

export function ChatVirtualList({ items, onArtifactOpen }: ChatVirtualListProps) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 120,
    overscan: 6,
    getItemKey: (index: number) => items[index].id,
  });

  // 新消息到达 / 流式内容增长时自动滚到底部
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
        // 顶部预留空间避开 HeaderControls (position: fixed; top: 24px)
        padding: `80px ${sp(theme.spacing.md)} ${sp(theme.spacing.md)}`,
      }}
    >
      <div style={{ height: virtualizer.getTotalSize(), position: "relative", width: "100%" }}>
        {virtualizer.getVirtualItems().map((v) => {
          const item = items[v.index];
          const isUser = item.role === "user";
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
                paddingBottom: sp(theme.spacing.md),
              }}
            >
              <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start" }}>
                <div
                  style={{
                    maxWidth: "82%",
                    background: isUser
                      ? `linear-gradient(135deg, ${color("accent")}, ${color("accentHover")})`
                      : AI_BUBBLE_BORDER_GRAD,
                    padding: 1,
                    borderRadius: sp(radius("cardLarge")),
                    boxShadow: isUser ? "0 4px 16px rgba(108,92,231,0.25)" : AI_BUBBLE_BOX_SHADOW,
                    animation: "fadeInUp 0.3s ease-out",
                  }}
                >
                  <div
                    style={{
                      background: isUser
                        ? "transparent"
                        : AI_BUBBLE_BG,
                      borderRadius: `calc(${sp(radius("cardLarge"))} - 1px)`,
                      padding: sp(theme.spacing.sm),
                      backgroundImage: isUser
                        ? "none"
                        : "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.06) 50%, transparent 100%)",
                      backgroundRepeat: "no-repeat",
                      backgroundSize: "100% 1px",
                      backgroundPosition: "top",
                      color: isUser ? "#fff" : color("textPrimary"),
                      fontSize: sp(theme.fontSize.body),
                      lineHeight: 1.8,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                    }}
                  >
                    {item.content}

                    {item.artifacts && item.artifacts.length > 0 && (
                      <div style={{ marginTop: sp(theme.spacing.sm) }}>
                        {item.artifacts.map((a: Artifact) => (
                          <div
                            key={a.id}
                            style={{
                              background: "rgba(255,255,255,0.04)",
                              border: "1px solid rgba(255,255,255,0.06)",
                              borderRadius: sp(radius("card")),
                              padding: sp(theme.spacing.xs),
                              marginBottom: sp(6),
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              gap: sp(8),
                            }}
                          >
                            <span style={{ fontSize: sp(12) }}>{a.name}</span>
                            {a.preview_url && (
                              <button
                                onClick={() => onArtifactOpen?.(a.preview_url)}
                                style={{
                                  background: `linear-gradient(135deg, ${color("accent")}, ${color("accentHover")})`,
                                  color: "#fff",
                                  border: "none",
                                  borderRadius: sp(radius("button")),
                                  padding: `${sp(2)} ${sp(10)}`,
                                  fontSize: sp(11),
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
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ChatVirtualList;

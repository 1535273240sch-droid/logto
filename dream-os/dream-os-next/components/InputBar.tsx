/**
 * Dream Input — Dream OS 品牌组件 + Living Interface
 *
 * 胶囊形、玻璃、极细光圈呼吸。
 * 发送按钮：隐藏 → 淡入（输入时）→ 淡出（清空后）。
 * 关键词检测：输入时匹配的功能按钮自然浮现。
 * 点击功能按钮：选择模式（高亮），不提交。用户输入完整任务后按 Enter/发送才提交。
 */

import React, { useState, useRef, useEffect, useMemo } from "react";
import { theme, sp, color, radius } from "../core";

interface FeatureHint {
  keywords: string[];
  label: string;
  icon: string;
  mode: string;
}

const FEATURE_HINTS: FeatureHint[] = [
  {
    keywords: ["网站", "网页", "前端", "页面", "开发", "代码", "编程", "写一个", "做一个", "app", "html", "react", "vue", "js"],
    label: "开发模式",
    icon: "⌨",
    mode: "dev",
  },
  {
    keywords: ["ppt", "演示", "幻灯片", "presentation", "演讲稿"],
    label: "制作 PPT",
    icon: "📊",
    mode: "chat",
  },
  {
    keywords: ["图片", "画", "生成图", "海报", "设计", "logo", "插画", "image", "design", "draw"],
    label: "生成图片",
    icon: "🎨",
    mode: "chat",
  },
  {
    keywords: ["文档", "文章", "写一篇", "报告", "总结", "分析", "document", "report", "write"],
    label: "文档模式",
    icon: "📝",
    mode: "chat",
  },
];

interface InputBarProps {
  placeholder?: string;
  disabled?: boolean;
  onSubmit: (value: string, mode?: string) => void;
  onCancel?: () => void;
  onTypingChange?: (isTyping: boolean) => void;
}

export function InputBar({
  placeholder = "今天，你想完成什么？",
  disabled = false,
  onSubmit,
  onCancel,
  onTypingChange,
}: InputBarProps) {
  const [value, setValue] = useState("");
  const [focused, setFocused] = useState(false);
  const [selectedMode, setSelectedMode] = useState<string>("chat");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const prevTyping = useRef(false);

  const isTyping = value.length > 0;

  useEffect(() => {
    if (isTyping !== prevTyping.current) {
      prevTyping.current = isTyping;
      onTypingChange?.(isTyping);
    }
  }, [isTyping, onTypingChange]);

  useEffect(() => {
    if (!disabled) textareaRef.current?.focus();
  }, [disabled]);

  const autoResize = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 120) + "px";
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    autoResize();
  };

  const handleSubmit = () => {
    if (!value.trim() || disabled) return;
    onSubmit(value.trim(), selectedMode);
    setValue("");
    setSelectedMode("chat");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFeatureClick = (hint: FeatureHint) => {
    setSelectedMode(hint.mode);
  };

  const matchedHints = useMemo(() => {
    if (value.trim().length < 2) return [];
    const lower = value.toLowerCase();
    return FEATURE_HINTS.filter((hint) =>
      hint.keywords.some((kw) => lower.includes(kw))
    ).slice(0, 3);
  }, [value]);

  const isActive = focused || isTyping;

  return (
    <div
      style={{
        width: "100%",
        maxWidth: 560,
        padding: `0 ${sp(theme.spacing.md)}`,
        position: "relative",
        zIndex: 1,
      }}
    >
      <div
        style={{
          position: "relative",
          background: "rgba(255,255,255,0.02)",
          backdropFilter: "blur(28px)",
          WebkitBackdropFilter: "blur(28px)",
          borderRadius: 28,
          padding: sp(3),
          border: isActive
            ? "1px solid rgba(108,92,231,0.5)"
            : "1px solid rgba(255,255,255,0.06)",
          animation: "none",
          transition: "border-color 0.8s ease",
          boxShadow: isActive
            ? "0 0 30px rgba(108,92,231,0.35), 0 0 64px rgba(108,92,231,0.18)"
            : "none",
          zIndex: 1,
        }}
      >
        {isActive && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              borderRadius: 28,
              background: "linear-gradient(90deg, transparent 0%, rgba(108,92,231,0) 30%, rgba(108,92,231,0.30) 50%, rgba(108,92,231,0) 70%, transparent 100%)",
              backgroundSize: "200% 100%",
              animation: "shimmer 2.6s linear infinite",
              pointerEvents: "none",
              zIndex: 0,
            }}
          />
        )}

        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          style={{
            width: "100%",
            background: "transparent",
            border: "none",
            color: color("textPrimary"),
            fontSize: sp(theme.fontSize.body),
            padding: `${sp(16)} ${sp(52)} ${sp(16)} ${sp(22)}`,
            resize: "none",
            outline: "none",
            lineHeight: "24px",
            fontFamily: "inherit",
            borderRadius: 26,
            position: "relative",
            zIndex: 1,
            caretColor: color("accentLight"),
          }}
        />

        <div
          style={{
            position: "absolute",
            right: sp(10),
            top: "50%",
            transform: "translateY(-50%)",
            display: "flex",
            alignItems: "center",
            gap: sp(4),
            zIndex: 2,
          }}
        >
          {disabled && (
            <button
              onClick={onCancel}
              style={{
                width: 32, height: 32, borderRadius: "50%",
                border: "none", background: "rgba(225,112,85,0.12)",
                color: color("error"), cursor: "pointer",
                display: "flex", alignItems: "center", justifyContent: "center",
                transition: "all 0.3s ease", opacity: 0.8,
              }}
              aria-label="取消"
            >
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <rect x="2" y="2" width="10" height="10" rx="2" fill="currentColor"/>
              </svg>
            </button>
          )}

          {!disabled && (
            <button
              onClick={handleSubmit}
              disabled={!isTyping}
              style={{
                width: 32, height: 32, borderRadius: "50%",
                border: "none",
                background: isTyping ? "linear-gradient(135deg, #6c5ce7, #a29bfe)" : "rgba(255,255,255,0.04)",
                color: isTyping ? "#fff" : "transparent",
                cursor: isTyping ? "pointer" : "default",
                display: "flex", alignItems: "center", justifyContent: "center",
                opacity: isTyping ? 1 : 0,
                transform: isTyping ? "scale(1)" : "scale(0.6)",
                transition: "all 0.5s cubic-bezier(0.4, 0, 0.2, 1)",
                boxShadow: isTyping ? "0 2px 10px rgba(108,92,231,0.4)" : "none",
                pointerEvents: isTyping ? "auto" : "none",
              }}
              aria-label="发送"
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M8 2L8 14M8 2L4 6M8 2L12 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          )}
        </div>
      </div>

      {matchedHints.length > 0 && (
        <div
          style={{
            display: "flex",
            gap: sp(8),
            marginTop: sp(12),
            justifyContent: "center",
            flexWrap: "wrap",
            animation: "fadeInUp 0.4s ease-out",
          }}
        >
          {matchedHints.map((hint) => {
            const isSelected = selectedMode === hint.mode;
            return (
            <button
              key={hint.mode}
              onClick={() => handleFeatureClick(hint)}
              style={{
                display: "flex", alignItems: "center", gap: sp(6),
                padding: `${sp(8)} ${sp(16)}`,
                background: isSelected
                  ? "rgba(108,92,231,0.18)"
                  : "rgba(255,255,255,0.04)",
                backdropFilter: "blur(12px)",
                border: isSelected
                  ? "1px solid rgba(108,92,231,0.4)"
                  : "1px solid rgba(255,255,255,0.08)",
                borderRadius: sp(radius("button")),
                color: isSelected ? color("accentLight") : color("textSecondary"),
                fontSize: sp(13), cursor: "pointer",
                transition: "all 0.3s ease", whiteSpace: "nowrap",
                boxShadow: isSelected
                  ? "0 0 10px rgba(108,92,231,0.15)"
                  : "none",
              }}
            >
              <span style={{ fontSize: sp(15) }}>{hint.icon}</span>
              <span>{hint.label}</span>
            </button>
          )})}
        </div>
      )}
    </div>
  );
}

export default InputBar;

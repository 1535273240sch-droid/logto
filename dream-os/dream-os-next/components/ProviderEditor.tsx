/**
 * ProviderEditor — 新增 Provider 表单
 *
 * 极简表单：Provider 名称 / Base URL / API Key / Model ID
 * 保存后自动加入 ProviderStore，无需修改其它代码。
 */

import React, { useState } from "react";
import { theme, sp, color, radius } from "../core";
import { ProviderConfig } from "../types/provider";

interface ProviderEditorProps {
  onSave: (config: Omit<ProviderConfig, "id" | "createdAt" | "updatedAt" | "status" | "latencyMs" | "lastTested">) => void;
  onCancel: () => void;
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: sp(radius("button")),
  padding: `${sp(10)} ${sp(14)}`,
  color: color("textPrimary"),
  fontSize: sp(14),
  outline: "none",
  fontFamily: "monospace",
};

const labelStyle: React.CSSProperties = {
  fontSize: sp(11),
  color: color("textMuted"),
  marginBottom: sp(4),
  textTransform: "uppercase" as const,
  letterSpacing: "0.5px",
};

const fieldStyle: React.CSSProperties = {
  marginBottom: sp(14),
};

export function ProviderEditor({ onSave, onCancel }: ProviderEditorProps) {
  const [name, setName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [modelId, setModelId] = useState("");

  const handleSave = () => {
    if (!name.trim() || !baseUrl.trim() || !modelId.trim()) {
      return;
    }
    onSave({
      name: name.trim(),
      baseUrl: baseUrl.trim(),
      apiKey: apiKey.trim(),
      modelId: modelId.trim(),
      isDefault: false,
      enabled: true,
    });
  };

  const isValid = name.trim() && baseUrl.trim() && modelId.trim();

  return (
    <div
      style={{
        background: "rgba(108,92,231,0.05)",
        border: "1px solid rgba(108,92,231,0.15)",
        borderRadius: sp(radius("card")),
        padding: sp(theme.spacing.md),
        marginBottom: sp(theme.spacing.sm),
      }}
    >
      <h3
        style={{
          fontSize: sp(theme.fontSize.caption),
          fontWeight: theme.fontWeight.medium,
          color: color("textPrimary"),
          margin: `0 0 ${sp(theme.spacing.sm)} 0`,
        }}
      >
        新增 Provider
      </h3>

      {/* Provider 名称 */}
      <div style={fieldStyle}>
        <div style={labelStyle}>Provider 名称</div>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="例如: DeepSeek, Qwen, Grok..."
          style={inputStyle}
          autoFocus
        />
      </div>

      {/* Base URL */}
      <div style={fieldStyle}>
        <div style={labelStyle}>Base URL</div>
        <input
          type="text"
          value={baseUrl}
          onChange={(e) => setBaseUrl(e.target.value)}
          placeholder="例如: https://api.deepseek.com/v1"
          style={inputStyle}
        />
      </div>

      {/* API Key */}
      <div style={fieldStyle}>
        <div style={labelStyle}>API Key</div>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="sk-..."
          style={inputStyle}
        />
      </div>

      {/* Model ID */}
      <div style={fieldStyle}>
        <div style={labelStyle}>Model ID</div>
        <input
          type="text"
          value={modelId}
          onChange={(e) => setModelId(e.target.value)}
          placeholder="例如: deepseek-chat"
          style={inputStyle}
        />
      </div>

      {/* Actions */}
      <div style={{ display: "flex", gap: sp(8), marginTop: sp(theme.spacing.xs) }}>
        <button
          onClick={handleSave}
          disabled={!isValid}
          style={{
            flex: 1,
            background: isValid
              ? "linear-gradient(135deg, #6c5ce7, #a29bfe)"
              : "rgba(255,255,255,0.04)",
            border: "none",
            borderRadius: sp(radius("button")),
            padding: `${sp(10)} ${sp(20)}`,
            color: isValid ? "#fff" : color("textMuted"),
            fontSize: sp(14),
            fontWeight: theme.fontWeight.medium,
            cursor: isValid ? "pointer" : "default",
            opacity: isValid ? 1 : 0.5,
            transition: "all 0.2s",
          }}
        >
          保存 Provider
        </button>
        <button
          onClick={onCancel}
          style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: sp(radius("button")),
            padding: `${sp(10)} ${sp(20)}`,
            color: color("textMuted"),
            fontSize: sp(14),
            cursor: "pointer",
          }}
        >
          取消
        </button>
      </div>
    </div>
  );
}

export default ProviderEditor;

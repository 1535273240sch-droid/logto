/**
 * ProviderCard — 单个 AI Provider 管理卡片
 *
 * 每个 Provider 独立配置：
 * - API Key / Base URL / Model ID 编辑
 * - 一键测试连接
 * - 设为默认模型
 * - 启用/禁用
 * - 删除
 *
 * 所有修改自动保存，不依赖保存按钮。
 */

import React, { useState } from "react";
import { theme, sp, color, radius } from "../core";
import { ProviderConfig, ProviderConnectionTestResult } from "../types/provider";

interface ProviderCardProps {
  provider: ProviderConfig;
  onTest: (id: string) => Promise<ProviderConnectionTestResult>;
  onSetDefault: (id: string) => void;
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
  onAutoSave: (id: string, field: string, value: string) => void;
}

const statusColors: Record<string, string> = {
  connected: color("success"),
  disconnected: color("textMuted"),
  error: color("error"),
  testing: color("warning"),
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "rgba(255,255,255,0.04)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: sp(radius("button")),
  padding: sp(8) + " " + sp(12),
  color: color("textPrimary"),
  fontSize: sp(13),
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
  marginBottom: sp(12),
};

export function ProviderCard({
  provider,
  onTest,
  onSetDefault,
  onToggle,
  onDelete,
  onAutoSave,
}: ProviderCardProps) {
  const [testResult, setTestResult] = useState<ProviderConnectionTestResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await onTest(provider.id);
      setTestResult(result);
    } finally {
      setTesting(false);
    }
  };

  const handleFieldBlur = (field: string, value: string) => {
    const current = (provider as any)[field];
    if (current !== value) {
      onAutoSave(provider.id, field, value);
    }
  };

  const maskedApiKey = provider.apiKey
    ? provider.apiKey.slice(0, 6) + "..." + provider.apiKey.slice(-4)
    : "";

  return (
    <div
      style={{
        background: "rgba(255,255,255,0.03)",
        border: "1px solid " + (provider.isDefault ? "rgba(108,92,231,0.3)" : "rgba(255,255,255,0.06)"),
        borderRadius: sp(radius("card")),
        padding: sp(theme.spacing.sm),
        marginBottom: sp(theme.spacing.sm),
        transition: "all 0.2s",
        position: "relative",
      }}
    >
      {/* Header row: name + status + actions */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: sp(theme.spacing.sm),
          flexWrap: "wrap",
          gap: sp(8),
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: sp(8) }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: statusColors[provider.status],
              flexShrink: 0,
              animation: provider.status === "testing" ? "pulse 1s infinite" : undefined,
            }}
          />
          <span
            style={{
              fontSize: sp(theme.fontSize.body),
              fontWeight: theme.fontWeight.medium,
              color: provider.enabled ? color("textPrimary") : color("textMuted"),
            }}
          >
            {provider.name}
          </span>
          {provider.isDefault && (
            <span
              style={{
                fontSize: sp(10),
                background: "rgba(108,92,231,0.2)",
                color: color("accentLight"),
                padding: sp(2) + " " + sp(8),
                borderRadius: sp(radius("button")),
              }}
            >
              默认
            </span>
          )}
          {!provider.enabled && (
            <span style={{ fontSize: sp(10), color: color("textMuted"), opacity: 0.6 }}>
              已禁用
            </span>
          )}
        </div>

        <div style={{ display: "flex", gap: sp(4), alignItems: "center", flexWrap: "wrap" }}>
          {provider.latencyMs != null && (
            <span style={{ fontSize: sp(11), color: color("textMuted"), marginRight: sp(8) }}>
              {provider.latencyMs}ms
            </span>
          )}

          <button
            onClick={handleTest}
            disabled={testing}
            title="测试连接"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: sp(radius("button")),
              padding: sp(4) + " " + sp(10),
              color: color("textSecondary"),
              fontSize: sp(12),
              cursor: testing ? "default" : "pointer",
              opacity: testing ? 0.5 : 1,
            }}
          >
            {testing ? "测试中" : "测试连接"}
          </button>

          {!provider.isDefault && provider.enabled && (
            <button
              onClick={() => onSetDefault(provider.id)}
              title="设为默认模型"
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: sp(radius("button")),
                padding: sp(4) + " " + sp(10),
                color: color("textSecondary"),
                fontSize: sp(12),
                cursor: "pointer",
              }}
            >
              默认
            </button>
          )}

          <button
            onClick={() => onToggle(provider.id)}
            title={provider.enabled ? "禁用" : "启用"}
            style={{
              background: provider.enabled
                ? "rgba(0,184,148,0.1)"
                : "rgba(255,255,255,0.04)",
              border: "1px solid " + (provider.enabled ? "rgba(0,184,148,0.2)" : "rgba(255,255,255,0.08)"),
              borderRadius: sp(radius("button")),
              padding: sp(4) + " " + sp(10),
              color: provider.enabled ? color("success") : color("textMuted"),
              fontSize: sp(12),
              cursor: "pointer",
            }}
          >
            {provider.enabled ? "启用" : "禁用"}
          </button>

          <button
            onClick={() => onDelete(provider.id)}
            title="删除 Provider"
            style={{
              background: "transparent",
              border: "none",
              color: "rgba(225,112,85,0.5)",
              fontSize: sp(16),
              cursor: "pointer",
              padding: sp(2) + " " + sp(6),
            }}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Editable fields */}
      <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
        <div style={fieldStyle}>
          <div style={labelStyle}>API Key</div>
          <div style={{ display: "flex", gap: sp(4) }}>
            <input
              type={showApiKey ? "text" : "password"}
              defaultValue={provider.apiKey}
              placeholder={provider.apiKey ? maskedApiKey : "sk-..."}
              onBlur={(e) => handleFieldBlur("apiKey", e.target.value)}
              style={inputStyle}
            />
            <button
              onClick={() => setShowApiKey(!showApiKey)}
              title={showApiKey ? "隐藏" : "显示"}
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: sp(radius("button")),
                padding: sp(8) + " " + sp(10),
                color: color("textMuted"),
                fontSize: sp(12),
                cursor: "pointer",
                flexShrink: 0,
              }}
            >
              {showApiKey ? "隐藏" : "显示"}
            </button>
          </div>
        </div>

        <div style={fieldStyle}>
          <div style={labelStyle}>Base URL</div>
          <input
            type="text"
            defaultValue={provider.baseUrl}
            onBlur={(e) => handleFieldBlur("baseUrl", e.target.value)}
            style={inputStyle}
          />
        </div>

        <div style={fieldStyle}>
          <div style={labelStyle}>Model ID</div>
          <input
            type="text"
            defaultValue={provider.modelId}
            onBlur={(e) => handleFieldBlur("modelId", e.target.value)}
            style={inputStyle}
          />
        </div>
      </div>

      {/* Test result */}
      {testResult && (
        <div
          style={{
            marginTop: sp(theme.spacing.xs),
            padding: sp(8) + " " + sp(12),
            borderRadius: sp(radius("button")),
            background: testResult.success
              ? "rgba(0,184,148,0.08)"
              : "rgba(225,112,85,0.08)",
            border: "1px solid " + (testResult.success ? "rgba(0,184,148,0.2)" : "rgba(225,112,85,0.2)"),
            fontSize: sp(13),
            color: testResult.success ? color("success") : color("error"),
            display: "flex",
            alignItems: "center",
            gap: sp(8),
          }}
        >
          <span>{testResult.success ? "✓" : "×"}</span>
          <span>{testResult.message}</span>
          {testResult.latencyMs != null && (
            <span style={{ marginLeft: "auto", opacity: 0.7 }}>
              {testResult.latencyMs}ms
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export default ProviderCard;

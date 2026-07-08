/**
 * AI Engine Center — Apple 风格 Bottom Sheet
 *
 * 点击模型按钮打开底部抽屉。
 * 玻璃质感，圆角，层次清晰。
 * 管理所有 Provider 的独立配置。
 */

import React, { useEffect, useState } from "react";
import { theme, sp, color, radius } from "../core";
import { providerStore } from "../core/ProviderStore";
import { ProviderConfig } from "../types/provider";
import { ProviderCard } from "./ProviderCard";
import { ProviderEditor } from "./ProviderEditor";

interface AIEngineCenterProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AIEngineCenter({ isOpen, onClose }: AIEngineCenterProps) {
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [editingProvider, setEditingProvider] = useState<ProviderConfig | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");

  useEffect(() => {
    providerStore.init();
    setProviders(providerStore.getAll());
    return providerStore.subscribe((p) => setProviders(p));
  }, []);

  if (!isOpen) return null;

  const handleAdd = (config: Omit<ProviderConfig, "id" | "createdAt" | "updatedAt" | "status" | "latencyMs" | "lastTested">) => {
    providerStore.addProvider(config);
    setShowAddForm(false);
    setSaveMessage("✓ 已保存");
    setTimeout(() => setSaveMessage(""), 2000);
  };

  const handleUpdate = (id: string, updates: Partial<ProviderConfig>) => {
    providerStore.updateProvider(id, updates);
    setEditingProvider(null);
    setSaveMessage("✓ 已保存");
    setTimeout(() => setSaveMessage(""), 2000);
  };

  const handleTest = async (id: string) => {
    await providerStore.testConnection(id);
  };

  const handleSetDefault = (id: string) => {
    providerStore.setDefault(id);
  };

  const handleToggle = (id: string) => {
    providerStore.toggleEnabled(id);
  };

  const handleDelete = (id: string) => {
    providerStore.removeProvider(id);
  };

  const handleAutoSave = (id: string, field: string, value: string) => {
    providerStore.updateProvider(id, { [field]: value });
    setSaveMessage("✓ 已保存");
    setTimeout(() => setSaveMessage(""), 2000);
  };

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.5)",
          zIndex: 300,
          transition: "opacity 0.3s",
        }}
      />

      {/* Bottom Sheet */}
      <div
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          maxHeight: "85vh",
          background: `linear-gradient(180deg, ${color("bgSecondary")}, rgba(10,10,15,0.98))`,
          borderTop: `1px solid ${color("border")}`,
          borderRadius: `${sp(radius("modal"))} ${sp(radius("modal"))} 0 0`,
          zIndex: 301,
          display: "flex",
          flexDirection: "column",
          animation: "slideUp 0.35s ease-out",
          boxShadow: "0 -10px 40px rgba(0,0,0,0.4)",
          backdropFilter: "blur(20px)",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: `${sp(theme.spacing.sm)} ${sp(theme.spacing.md)}`,
            borderBottom: `1px solid ${color("border")}`,
            flexShrink: 0,
          }}
        >
          <div>
            <h2
              style={{
                fontSize: sp(theme.fontSize.h2),
                fontWeight: theme.fontWeight.medium,
                color: color("textPrimary"),
                margin: 0,
              }}
            >
              AI Engine Center
            </h2>
            <div
              style={{
                fontSize: sp(theme.fontSize.status),
                color: color("textMuted"),
                marginTop: sp(4),
              }}
            >
              {providers.length} 个引擎
              {saveMessage && (
                <span style={{ color: color("success"), marginLeft: sp(8) }}>
                  {saveMessage}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: color("textMuted"),
              fontSize: sp(20),
              cursor: "pointer",
              padding: sp(4),
            }}
            aria-label="关闭"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: `${sp(theme.spacing.sm)} ${sp(theme.spacing.sm)}`,
            paddingBottom: sp(theme.spacing.xxxl),
          }}
        >
          {/* Add Provider Button */}
          {!showAddForm && (
            <button
              onClick={() => setShowAddForm(true)}
              style={{
                width: "100%",
                background: color("bgCard"),
                border: `1px dashed ${color("border")}`,
                borderRadius: sp(radius("card")),
                padding: `${sp(theme.spacing.sm)}`,
                color: color("textMuted"),
                fontSize: sp(theme.fontSize.caption),
                cursor: "pointer",
                marginBottom: sp(theme.spacing.sm),
                transition: "all 0.2s",
              }}
            >
              ＋ 添加 Provider
            </button>
          )}

          {/* Add Form */}
          {showAddForm && (
            <ProviderEditor
              onSave={handleAdd}
              onCancel={() => setShowAddForm(false)}
            />
          )}

          {/* Provider List */}
          {providers.map((provider) => (
            <ProviderCard
              key={provider.id}
              provider={provider}
              onTest={handleTest}
              onSetDefault={handleSetDefault}
              onToggle={handleToggle}
              onDelete={handleDelete}
              onAutoSave={handleAutoSave}
            />
          ))}
        </div>
      </div>
    </>
  );
}

export default AIEngineCenter;

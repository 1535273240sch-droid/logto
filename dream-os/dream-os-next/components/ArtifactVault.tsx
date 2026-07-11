/**
 * ArtifactVault — 成果中心
 *
 * 右侧滑出（Drawer），不是页面跳转。
 * 关闭后仍回到当前状态。
 * 入口：右上角永久入口 + DeliveryView "查看成果"。
 *
 * 按日期/项目/类型自动分类。
 * 支持：继续编辑、再次执行、下载、删除。
 */

import React, { useState, useEffect } from "react";
import { theme, sp, color, radius } from "../core";
import { artifactStore } from "../core/ArtifactStore";
import { Artifact } from "../types/dream";
import { useDreamContext } from "../context/DreamContext";

const TYPE_LABELS: Record<string, string> = {
  website: "网站",
  ppt: "PPT",
  image: "图片",
  document: "文档",
  code: "代码",
};

const ACTION_LABELS: Record<string, string> = {
  website: "打开网站",
  ppt: "预览",
  image: "下载",
  document: "阅读",
  code: "查看源码",
};

interface ArtifactVaultProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ArtifactVault({ isOpen, onClose }: ArtifactVaultProps) {
  const [artifacts, setArtifacts] = useState<Artifact[]>(artifactStore.getAll());
  const [groupBy, setGroupBy] = useState<"date" | "type">("date");

  useEffect(() => {
    return artifactStore.subscribe(() => {
      setArtifacts(artifactStore.getAll());
    });
  }, []);

  if (!isOpen) return null;

  const grouped = artifactStore.getGrouped(groupBy);
  const isEmpty = artifacts.length === 0;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.4)",
          zIndex: 200,
          transition: "opacity 0.3s",
        }}
      />

      {/* Drawer */}
      <div
        style={{
          position: "fixed",
          right: 0,
          top: 0,
          bottom: 0,
          width: 380,
          maxWidth: "90vw",
          background: color("bgSecondary"),
          borderLeft: `1px solid ${color("border")}`,
          zIndex: 201,
          display: "flex",
          flexDirection: "column",
          animation: "slideInRight 0.3s ease-out",
          boxShadow: "0 0 40px rgba(0,0,0,0.3)",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: `${sp(theme.spacing.md)} ${sp(theme.spacing.sm)}`,
            borderBottom: `1px solid ${color("border")}`,
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
              成果中心
            </h2>
            <div
              style={{
                fontSize: sp(theme.fontSize.status),
                color: color("textMuted"),
                marginTop: sp(4),
              }}
            >
              {artifacts.length} 个成果
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

        {/* Group tabs */}
        {!isEmpty && (
          <div
            style={{
              display: "flex",
              padding: `${sp(theme.spacing.xs)} ${sp(theme.spacing.sm)}`,
              gap: sp(theme.spacing.xs),
              borderBottom: `1px solid ${color("border")}`,
            }}
          >
            {(["date", "type"] as const).map((g) => (
              <button
                key={g}
                onClick={() => setGroupBy(g)}
                style={{
                  background: groupBy === g ? color("accent") : "transparent",
                  color: groupBy === g ? "#fff" : color("textMuted"),
                  border: "none",
                  borderRadius: sp(radius("button")),
                  padding: `${sp(4)} ${sp(12)}`,
                  fontSize: sp(theme.fontSize.status),
                  cursor: "pointer",
                }}
              >
                {g === "date" ? "按日期" : "按类型"}
              </button>
            ))}
          </div>
        )}

        {/* Content */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: `${sp(theme.spacing.xs)} ${sp(theme.spacing.sm)}`,
          }}
        >
          {isEmpty ? (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                height: "100%",
                color: color("textMuted"),
                fontSize: sp(theme.fontSize.caption),
              }}
            >
              <div style={{ fontSize: sp(40), marginBottom: sp(theme.spacing.sm), opacity: 0.3 }}>
                📦
              </div>
              暂无成果
            </div>
          ) : (
            grouped.map((group) => (
              <div key={group.key} style={{ marginBottom: sp(theme.spacing.md) }}>
                <div
                  style={{
                    fontSize: sp(theme.fontSize.status),
                    color: color("textMuted"),
                    fontWeight: theme.fontWeight.medium,
                    marginBottom: sp(theme.spacing.xs),
                    paddingLeft: sp(4),
                  }}
                >
                  {group.label}
                </div>

                {group.artifacts.map((artifact) => (
                  <div
                    key={artifact.id}
                    style={{
                      background: artifact.status === "ready" ? color("bgCard") : "transparent",
                      border: `1px solid ${color("border")}`,
                      borderRadius: sp(radius("card")),
                      padding: sp(theme.spacing.sm),
                      marginBottom: sp(theme.spacing.xs),
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-start",
                        marginBottom: sp(8),
                      }}
                    >
                      <div>
                        <div
                          style={{
                            fontSize: sp(theme.fontSize.caption),
                            fontWeight: theme.fontWeight.medium,
                            color: color("textPrimary"),
                          }}
                        >
                          {artifact.name}
                        </div>
                        <div
                          style={{
                            fontSize: sp(theme.fontSize.status),
                            color: color("textMuted"),
                            marginTop: sp(2),
                          }}
                        >
                          {TYPE_LABELS[artifact.type] || artifact.type}
                          {artifact.files.length > 0 &&
                            ` · ${artifact.files.length} 文件`}
                        </div>
                      </div>
                      <div
                        style={{
                          fontSize: sp(11),
                          color: color("textMuted"),
                        }}
                      >
                        {artifact.created_at.slice(0, 10)}
                      </div>
                    </div>

                    {/* Actions */}
                    <div
                      style={{
                        display: "flex",
                        gap: sp(8),
                        flexWrap: "wrap",
                      }}
                    >
                      {artifact.preview_url && (
                        <button
                          onClick={() => window.open(artifact.preview_url, "_blank")}
                          style={{
                            background: `linear-gradient(135deg, ${color("accent")}, ${color("accentHover")})`,
                            color: "#fff",
                            border: "none",
                            borderRadius: sp(radius("button")),
                            padding: `${sp(4)} ${sp(12)}`,
                            fontSize: sp(12),
                            cursor: "pointer",
                          }}
                        >
                          {ACTION_LABELS[artifact.type] || "打开"}
                        </button>
                      )}
                      <button
                        style={{
                          background: "transparent",
                          color: color("textMuted"),
                          border: `1px solid ${color("border")}`,
                          borderRadius: sp(radius("button")),
                          padding: `${sp(4)} ${sp(12)}`,
                          fontSize: sp(12),
                          cursor: "pointer",
                        }}
                      >
                        下载
                      </button>
                      <button
                        onClick={async () => {
                          try {
                            await fetch(`/api/artifacts/${artifact.id}`, { method: "DELETE" });
                          } catch (e) {
                            console.warn("Delete API failed:", e);
                          }
                          artifactStore.remove(artifact.id);
                        }}
                        style={{
                          background: "transparent",
                          color: color("error"),
                          border: "none",
                          borderRadius: sp(radius("button")),
                          padding: `${sp(4)} ${sp(8)}`,
                          fontSize: sp(12),
                          cursor: "pointer",
                          marginLeft: "auto",
                        }}
                      >
                        删除
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}

export default ArtifactVault;

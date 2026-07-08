/**
 * DreamCanvas — 唯一页面（V2 重构）
 *
 * 双模式：chat（聊天） / dev（开发，8 Agent 工作流）
 * 模式由 InputBar 关键词检测自动切换。
 */

import React, { useEffect, useState, useCallback, useRef } from "react";
import { sp, color } from "../core";
import { useDreamContext } from "../context/DreamContext";
import { DreamStateVariant } from "../types/dream";
import type { DreamStateSnapshot } from "../core/DreamState";
import { adaptToDEP } from "../adapters/DEPAdapter";
import { DEPEventType, DEPPayload } from "../types/dep";
import { IdleView } from "./IdleView";
import { ThinkingView } from "./ThinkingView";
import { WorkingView } from "./WorkingView";
import { DeliveryView } from "./DeliveryView";

export function DreamCanvas() {
  const { dreamState, eventBus } = useDreamContext();
  const [snapshot, setSnapshot] = useState<DreamStateSnapshot>(
    dreamState.getSnapshot()
  );
  const abortControllerRef = useRef<AbortController | null>(null);
  const [checkpoint, setCheckpoint] = useState<{
    type: string; agent: string; name: string; task: string; task_id: string;
  } | null>(null);

  useEffect(() => {
    return dreamState.subscribe((newSnapshot) => {
      setSnapshot(newSnapshot);
    });
  }, [dreamState]);

  const currentState = snapshot.state;

  const handleDEPEvent = useCallback(
    async (event: DEPPayload, taskId: string) => {
      const { type, data } = event;

      switch (type) {
        case DEPEventType.TASK_CREATED:
          dreamState.enterThinking({
            task_id: taskId,
            feature: "chat",
            user_input: data.user_input || "",
            progress_percent: 0,
          }, "正在理解你的目标……");
          break;

        case DEPEventType.TASK_PLANNING:
          dreamState.enterWorking();
          break;

        case DEPEventType.AGENT_STARTED:
          dreamState.updateAgent({
            agent: data.agent,
            role: data.agent_role,
            status: "running",
            progress_percent: 0,
            description: data.description,
          });
          break;

        case DEPEventType.AGENT_FINISHED:
          dreamState.updateAgent({
            agent: data.agent,
            role: data.agent,
            status: data.success ? "done" : "failed",
            progress_percent: 100,
          });
          break;

        case DEPEventType.ARTIFACT_CREATED:
          dreamState.addArtifact({
            id: data.artifact_id,
            task_id: taskId,
            type: data.artifact_type,
            name: data.name,
            description: "",
            status: "ready",
            preview_url: data.preview_url,
            files: data.files || [],
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          });
          break;

        case DEPEventType.DELIVERY_READY:
          dreamState.enterDelivery();
          break;
      }

      await eventBus.publish(event);
    },
    [dreamState, eventBus]
  );

  // ── 统一提交入口，接受 mode 参数 ──
  const handleSubmit = useCallback(
    async (value: string, mode: string = "chat") => {
      const taskId = `task_${Date.now()}`;

      dreamState.enterThinking(
        {
          task_id: taskId,
          feature: mode,
          user_input: value,
          progress_percent: 0,
        },
        mode === "dev" ? "正在启动开发工作流……" : "正在理解你的目标……"
      );

      const controller = new AbortController();
      abortControllerRef.current = controller;

      try {
        const response = await fetch("/api/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: value,
            mode: mode,
            task_id: taskId,
          }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const raw = line.slice(6);
            if (raw.trim() === "[DONE]") continue;

            try {
              const parsed = JSON.parse(raw);

              // ── content 事件：逐 token 增量渲染（打字效果） ──
              if (parsed.type === "content" && parsed.content) {
                dreamState.appendContent(parsed.content);
                // 流式更新：逐 token 渲染
                const text = parsed.content;
                for (let i = 0; i < text.length; i += 3) {
                  await new Promise(r => setTimeout(r, 5));
                }
                continue;
              }

              // ── done 事件 ──
              if (parsed.type === "done") {
                dreamState.enterDelivery();
                continue;
              }

              // ── dev_start 事件：8 Agent 工作流 ──
              if (parsed.type === "dev_start") {
                dreamState.enterWorking();
                if (parsed.agents && Array.isArray(parsed.agents)) {
                  for (const agent of parsed.agents) {
                    dreamState.updateAgent({
                      agent: agent.role,
                      role: agent.name,
                      status: "pending",
                      progress_percent: 0,
                      description: agent.description,
                    });
                  }
                }
                continue;
              }

              // ── agent_start 事件（dev 模式） ──
              if (parsed.type === "agent_start") {
                dreamState.updateAgent({
                  agent: parsed.agent,
                  role: parsed.agent,
                  status: "running",
                  progress_percent: 0,
                  description: parsed.description || "",
                });
                continue;
              }

              // ── agent_complete 事件 ──
              if (parsed.type === "agent_complete") {
                dreamState.updateAgent({
                  agent: parsed.agent,
                  role: parsed.agent,
                  status: "done",
                  progress_percent: 100,
                });
                continue;
              }

              // ── dev_complete 事件 ──
              if (parsed.type === "dev_complete") {
                dreamState.enterDelivery();
                continue;
              }

              // ── tool_start / tool_result ──
              if (parsed.type === "tool_start") {
                dreamState.updateAgent({
                  agent: parsed.tool || "tool",
                  role: parsed.tool || "tool",
                  status: "running",
                  progress_percent: 0,
                  description: parsed.description || "",
                });
                continue;
              }

              // ── human_checkpoint（人机协作关卡）──
              if (parsed.type === "human_checkpoint") {
                setCheckpoint({
                  type: "human_checkpoint",
                  agent: parsed.agent || "",
                  name: parsed.name || parsed.agent || "",
                  task: parsed.task || parsed.description || "",
                  task_id: parsed.task_id || taskId,
                });
                continue;
              }

              // ── confirmation_required（危险操作确认）──
              if (parsed.type === "confirmation_required") {
                setCheckpoint({
                  type: "confirmation_required",
                  agent: parsed.agent || "tool",
                  name: parsed.tool_name || parsed.agent || "工具",
                  task: `命令: ${parsed.command || ""}\n原因: ${parsed.reason || "可能修改系统文件"}`,
                  task_id: parsed.task_id || taskId,
                });
                continue;
              }

              // ── 旧 pipeline 协议 → DEP ──
              const depEvent = adaptToDEP(parsed, taskId, "pipeline");
              if (depEvent) {
                await handleDEPEvent(depEvent, taskId);
              }
            } catch (err) {
              console.warn("[DreamCanvas] Parse error:", err);
            }
          }
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          console.error("[DreamCanvas] Stream error:", err);
          dreamState.updateAgent({
            agent: "system",
            role: "System",
            status: "failed",
            progress_percent: 0,
          });
          await eventBus.publish({
            type: "task_error",
            task_id: taskId,
            timestamp: new Date().toISOString(),
            data: {
              error_code: "STREAM_ERROR",
              message: err.message,
              recoverable: false,
            },
          });
        }
      }
    },
    [dreamState, eventBus, handleDEPEvent]
  );

  const handleCancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    dreamState.enterIdle();
  }, [dreamState]);

  const handleCheckpointAction = useCallback(async (action: string) => {
    if (!checkpoint) return;
    const { task_id } = checkpoint;
    try {
      await fetch(`/api/v3/dev/tasks/${task_id}/human-action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
    } catch (e) {
      console.warn("[DreamCanvas] Checkpoint action failed:", e);
    }
    setCheckpoint(null);
  }, [checkpoint]);

  const renderContent = () => {
    switch (currentState) {
      case DreamStateVariant.IDLE:
        return <IdleView onSubmit={handleSubmit} />;

      case DreamStateVariant.THINKING:
        return (
          <ThinkingView
            message={snapshot.thinkingMessage}
            disabled={true}
            onCancel={handleCancel}
          />
        );

      case DreamStateVariant.WORKING:
        return (
          <WorkingView
            disabled={true}
            onCancel={handleCancel}
          />
        );

      case DreamStateVariant.DELIVERY:
        return <DeliveryView onSubmit={handleSubmit} />;

      default:
        return <IdleView onSubmit={handleSubmit} />;
    }
  };

  return (
    <div
      style={{
        position: "relative",
        width: "100vw",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "relative",
          zIndex: 1,
          flex: 1,
          display: "flex",
          flexDirection: "column",
        }}
      >
        {renderContent()}
      </div>

      {/* ── 人机协作关卡弹窗 ── */}
      {checkpoint && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 100,
          background: "rgba(0,0,0,0.7)", backdropFilter: "blur(6px)",
          display: "flex", alignItems: "center", justifyContent: "center",
          animation: "fadeIn 0.2s ease-out",
        }}>
          <div style={{
            background: "rgba(20,20,30,0.95)", backdropFilter: "blur(20px)",
            borderRadius: 16, border: "1px solid rgba(255,255,255,0.08)",
            padding: "28px 32px", maxWidth: 420, width: "90%",
            textAlign: "center",
          }}>
            <div style={{
              fontSize: 13, color: "rgba(255,255,255,0.4)",
              marginBottom: 8, letterSpacing: 1,
            }}>
              {checkpoint.type === "human_checkpoint" ? "人机协作关卡" : "操作确认"}
            </div>
            <div style={{
              fontSize: 18, fontWeight: 600, color: "#fff",
              marginBottom: 6,
            }}>
              {checkpoint.name}
            </div>
            <div style={{
              fontSize: 13, color: "rgba(255,255,255,0.5)",
              lineHeight: 1.6, marginBottom: 24, whiteSpace: "pre-line",
            }}>
              {checkpoint.task}
            </div>
            <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
              <button
                onClick={() => handleCheckpointAction("skip")}
                style={{
                  padding: "10px 24px", borderRadius: 10,
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  color: "rgba(255,255,255,0.5)", fontSize: 14,
                  cursor: "pointer",
                }}
              >
                跳过
              </button>
              <button
                onClick={() => handleCheckpointAction("proceed")}
                style={{
                  padding: "10px 24px", borderRadius: 10,
                  background: "rgba(108,92,231,0.2)",
                  border: "1px solid rgba(108,92,231,0.3)",
                  color: "#c4b5fd", fontSize: 14, fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                继续执行
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default DreamCanvas;

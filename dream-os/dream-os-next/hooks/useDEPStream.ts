/**
 * useDEPStream — 统一 SSE 事件监听
 *
 * 所有任务，不管是 AgentPipeline 还是 Orchestrator，都通过 DEPStream 监听。
 * Adapter 已经转换为统一 DEP 协议，这里只需要更新 DreamState。
 */

import { useEffect, useRef, useState } from "react";
import { DEPEventType, DEPPayload, parseDEPLine } from "../types/dep";
import { eventBus } from "../core/EventBus";
import { dreamState } from "../core/DreamState";
import { adaptToDEP } from "../adapters/DEPAdapter";
import { config } from "../core/Config";

interface UseDEPStreamOptions {
  taskId: string;
  feature: string;
  userInput: string;
  onDone?: () => void;
}

export function useDEPStream({ taskId, feature, userInput, onDone }: UseDEPStreamOptions) {
  const [connected, setConnected] = useState(false);
  const readerRef = useRef<ReadableStreamDefaultReader | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const connect = async () => {
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const apiBase = config.getString("api_base_url", "/api");
      const url = `${apiBase}/chat/stream`;

      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userInput,
          feature,
          task_id: taskId,
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`);
      }

      setConnected(true);
      const reader = response.body.getReader();
      readerRef.current = reader;

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

          try {
            const raw = JSON.parse(line.slice(6));
            // 旧协议 → 转换为 DEP
            const depEvent = adaptToDEP(raw, taskId, feature === "dev" ? "orchestrator" : "pipeline");
            if (depEvent) {
              await handleDEPEvent(depEvent);
            }
          } catch (err) {
            console.warn("[useDEPStream] Parse error:", err);
          }
        }
      }

      setConnected(false);
      if (onDone) onDone();
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        console.error("[useDEPStream] Stream error:", err);
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
            message: (err as Error).message,
            recoverable: false,
          },
        });
      }
    }
  };

  const handleDEPEvent = async (event: DEPPayload) => {
    const { type, data } = event;

    switch (type) {
      case DEPEventType.TASK_CREATED:
        dreamState.enterThinking({
          task_id: taskId,
          feature,
          user_input: userInput,
          progress_percent: 0,
        }, "正在理解你的目标...");
        break;

      case DEPEventType.TASK_PLANNING:
        dreamState.enterWorking();
        break;

      case DEPEventType.FEATURE_LOADED:
        // feature 加载完成，准备开始 Agent
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

      case DEPEventType.AGENT_PROGRESS:
        dreamState.updateAgent({
          agent: data.agent,
          role: "",
          status: "running",
          progress_percent: data.progress_percent,
          description: data.current_step,
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

      case DEPEventType.TASK_COMPLETED:
        // 任务完成，已经进入 Delivery
        break;

      case DEPEventType.TASK_ERROR:
        console.error("[DEP] Task error:", data.message);
        break;

      case DEPEventType.TASK_RETRY:
        // retry 提示，不改变状态，继续
        break;
    }

    await eventBus.publish(event);
  };

  const disconnect = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (readerRef.current) {
      readerRef.current.cancel().catch(() => {});
    }
    setConnected(false);
  };

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [taskId]);

  return { connected, disconnect };
}

export default useDEPStream;

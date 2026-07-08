/**
 * useProjectBrain — 前端 Project Brain 接入
 *
 * Project Brain 是全局项目状态内核。
 * 所有 Agent 共享同一份项目状态。
 * 前端通过此 hook 监听 Project Brain 状态变化。
 *
 * 职责：
 * 1. 监听 EventBus 中的 agent.* 事件，同步到 Project Brain
 * 2. 任务完成后自动保存项目状态
 * 3. 提供项目状态快照给 Canvas
 */

import { useEffect, useState, useCallback } from "react";
import { eventBus } from "../core/EventBus";
import { DEPEventType } from "../types/dep";

interface ProjectBrainState {
  project_id: string;
  name: string;
  phase: string;
  progress_percent: number;
  completed_tasks: string[];
  pending_tasks: string[];
  bugs: Array<{ file: string; message: string; severity: string }>;
  risks: string[];
  files: string[];
  deploy_status: string;
  last_agent: string;
  last_updated: string;
}

interface WorkLogEntry {
  agent: string;
  action: string;
  timestamp: string;
}

const DEFAULT_BRAIN: ProjectBrainState = {
  project_id: "dream-os-v6",
  name: "Dream OS V6",
  phase: "initialization",
  progress_percent: 0,
  completed_tasks: [],
  pending_tasks: [],
  bugs: [],
  risks: [],
  files: [],
  deploy_status: "not_deployed",
  last_agent: "",
  last_updated: new Date().toISOString(),
};

export function useProjectBrain() {
  const [brain, setBrain] = useState<ProjectBrainState>(DEFAULT_BRAIN);
  const [workLogs, setWorkLogs] = useState<WorkLogEntry[]>([]);
  const [loaded, setLoaded] = useState(false);

  // 加载持久化状态
  const loadState = useCallback(async () => {
    try {
      const res = await fetch("/api/project_brain/state");
      if (res.ok) {
        const data = await res.json();
        setBrain({ ...DEFAULT_BRAIN, ...data.state });
        setWorkLogs(data.work_logs || []);
      }
    } catch {
      // 使用默认状态
    }
    setLoaded(true);
  }, []);

  // 保存状态
  const saveState = useCallback(async () => {
    try {
      await fetch("/api/project_brain/state", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          state: brain,
          work_logs: workLogs,
        }),
      });
    } catch {
      console.warn("[ProjectBrain] Failed to save state");
    }
  }, [brain, workLogs]);

  // 监听 EventBus 事件
  useEffect(() => {
    const subIds: string[] = [];

    // agent.start → 更新 last_agent
    subIds.push(
      eventBus.subscribe("agent_*", async (event) => {
        if (event.type === DEPEventType.AGENT_STARTED) {
          setBrain((prev) => ({
            ...prev,
            last_agent: event.data.agent,
            last_updated: new Date().toISOString(),
          }));
        }

        // agent.complete → 追加 work_log
        if (event.type === DEPEventType.AGENT_FINISHED) {
          setWorkLogs((prev) => [
            ...prev,
            {
              agent: event.data.agent,
              action: "completed",
              timestamp: new Date().toISOString(),
            },
          ].slice(-100));

          setBrain((prev) => ({
            ...prev,
            last_updated: new Date().toISOString(),
          }));
        }
      })
    );

    // task.completed → 自动保存
    subIds.push(
      eventBus.subscribe("task_completed", async () => {
        setBrain((prev) => ({
          ...prev,
          progress_percent: 100,
          last_updated: new Date().toISOString(),
        }));
        await saveState();
      })
    );

    loadState();

    return () => {
      subIds.forEach((id) => eventBus.unsubscribe(id));
    };
  }, [loadState, saveState]);

  // 更新进度
  const updateProgress = useCallback((percent: number) => {
    setBrain((prev) => ({
      ...prev,
      progress_percent: percent,
      last_updated: new Date().toISOString(),
    }));
  }, []);

  // 添加文件
  const addFile = useCallback((filename: string) => {
    setBrain((prev) => ({
      ...prev,
      files: [...prev.files, filename],
      last_updated: new Date().toISOString(),
    }));
  }, []);

  return {
    brain,
    workLogs,
    loaded,
    updateProgress,
    addFile,
    saveState,
    loadState,
  };
}

export default useProjectBrain;

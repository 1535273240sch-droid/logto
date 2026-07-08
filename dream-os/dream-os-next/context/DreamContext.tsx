/**
 * DreamContext — 全局状态上下文
 *
 * 提供 DreamState、EventBus、Registry 到所有组件的统一入口。
 * 所有组件通过 useDreamContext() 获取 Core 实例。
 */

import React, { createContext, useContext } from "react";
import { DreamState, dreamState } from "../core/DreamState";
import { EventBus, eventBus } from "../core/EventBus";
import { Registry, registry } from "../core/Registry";

interface DreamContextValue {
  dreamState: DreamState;
  eventBus: EventBus;
  registry: Registry;
}

const DreamContext = createContext<DreamContextValue>({
  dreamState,
  eventBus,
  registry,
});

export function DreamProvider({ children }: { children: React.ReactNode }) {
  return (
    <DreamContext.Provider value={{ dreamState, eventBus, registry }}>
      {children}
    </DreamContext.Provider>
  );
}

export function useDreamContext(): DreamContextValue {
  return useContext(DreamContext);
}

export default DreamContext;

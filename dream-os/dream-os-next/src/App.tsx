import React, { useEffect, lazy, Suspense } from "react";
import { DreamProvider } from "../context/DreamContext";
import { uiProtector } from "../core/UIProtector";
import snapshot from "../core/ui-snapshot.json";

// Code Splitting: 按面板 lazy 加载
const DreamCanvas = lazy(() => import("../components/DreamCanvas"));
const HeaderControls = lazy(() => import("../components/HeaderControls"));
const AIEngineCenter = lazy(() => import("../components/AIEngineCenter"));
const ArtifactVault = lazy(() => import("../components/ArtifactVault"));

const LoadingFallback = () => (
  <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
    <div style={{ fontSize: 14, color: "#888" }}>加载中...</div>
  </div>
);

export function App() {
  useEffect(() => {
    // 启动时加载快照，锁定 UI 保护
    uiProtector.loadSnapshot(snapshot as Record<string, { sha256: string; size: number }>);
  }, []);

  return (
    <DreamProvider>
      <div style={{ position: "relative", width: "100vw", height: "100vh" }}>
        {/* 右上角固定控制 */}
        <div
          style={{
            position: "fixed",
            top: 24,
            right: 24,
            zIndex: 100,
          }}
        >
          <HeaderControls />
        </div>
        <Suspense fallback={<LoadingFallback />}>
          <DreamCanvas />
        </Suspense>
      </div>
    </DreamProvider>
  );
}

/**
 * HeaderControls — 极简右上角
 *
 * 只有：AI Engine、成果。
 * 玻璃质感，极简图标。
 */

import React, { useState } from "react";
import { theme, sp, color, radius } from "../core";
import ArtifactVault from "./ArtifactVault";
import { AIEngineCenter } from "./AIEngineCenter";

export function HeaderControls() {
  const [artifactOpen, setArtifactOpen] = useState(false);
  const [aiEngineOpen, setAiEngineOpen] = useState(false);

  const btnStyle: React.CSSProperties = {
    background: "rgba(255,255,255,0.03)",
    backdropFilter: "blur(12px)",
    border: "1px solid rgba(255,255,255,0.05)",
    borderRadius: sp(radius("button")),
    padding: `${sp(6)} ${sp(12)}`,
    color: color("textMuted"),
    fontSize: sp(12),
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: sp(6),
    transition: "all 0.3s ease",
    opacity: 0.5,
  };

  return (
    <>
      <div
        style={{
          display: "flex",
          gap: sp(8),
          alignItems: "flex-start",
        }}
      >
        <button onClick={() => setAiEngineOpen(true)} title="AI 引擎" style={btnStyle}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
          <span>AI 引擎</span>
        </button>

        <button onClick={() => setArtifactOpen(true)} title="成果" style={btnStyle}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <span>成果</span>
        </button>
      </div>

      <AIEngineCenter isOpen={aiEngineOpen} onClose={() => setAiEngineOpen(false)} />
      <ArtifactVault isOpen={artifactOpen} onClose={() => setArtifactOpen(false)} />
    </>
  );
}

export default HeaderControls;

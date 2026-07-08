import React, { useState, useCallback } from "react";
import { sp } from "../core";
import { Brand } from "./Brand";
import { InputBar } from "./InputBar";

interface IdleViewProps {
  onSubmit: (value: string, mode?: string) => void;
}

export function IdleView({ onSubmit }: IdleViewProps) {
  const [isTyping, setIsTyping] = useState(false);

  const handleTypingChange = useCallback((typing: boolean) => {
    setIsTyping(typing);
  }, []);

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        paddingBottom: "8vh",
      }}
    >
      <Brand isTyping={isTyping} />
      <div style={{ marginTop: sp(36) }}>
        <InputBar onSubmit={onSubmit} onTypingChange={handleTypingChange} />
      </div>
      <div style={{ flex: 1 }} />
    </div>
  );
}

export default IdleView;

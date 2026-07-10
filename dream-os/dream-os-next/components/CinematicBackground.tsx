/**
 * CinematicBackground — 电影感星云背景（v14 锁定版）
 *
 * - 纯原生 WebGL 着色器（星云：多层视差 + 遮挡暗核 + 胶片色调 + 边缘色散 + 体积光）
 * - 2D 星流拖尾层
 * - 仅在 active=true（非 Idle 工作视图）时初始化 WebGL 并运行；Idle 时完全不占 GPU
 * - active 切换时从纯黑淡入（电影感入场），Idle 时 opacity:0 隐藏，首页原样不动
 */
import React, { useEffect, useRef } from "react";
import VERT from "../shaders/cinematic.vert.glsl?raw";
import FRAG from "../shaders/cinematic.frag.glsl?raw";

const DPR_CAP = 1.5;

const CSS = `
.cb-root{ position:fixed; inset:0; z-index:0; pointer-events:none; transition:opacity .6s ease; }
.cb-gl, .cb-stars{ position:absolute; inset:0; width:100%; height:100%; display:block; }
.cb-bloom{ position:absolute; inset:0; pointer-events:none;
  background:radial-gradient(ellipse 42% 48% at 50% 45%, rgba(150,120,255,0.26), rgba(108,92,231,0.08) 36%, transparent 72%);
  mix-blend-mode:screen; animation:cbBreathe 4.5s ease-in-out infinite; }
@keyframes cbBreathe{ 0%,100%{ opacity:0.5; transform:scale(1);} 50%{ opacity:1; transform:scale(1.08);} }
.cb-vignette{ position:absolute; inset:0; pointer-events:none;
  background:radial-gradient(ellipse 72% 72% at 50% 50%, transparent 48%, rgba(0,0,0,0.92) 100%); }
`;

export interface CinematicBackgroundProps {
  active: boolean;
}

export function CinematicBackground({ active }: CinematicBackgroundProps) {
  const glRef = useRef<HTMLCanvasElement>(null);
  const starRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!active) return;
    const cv = glRef.current;
    const sc = starRef.current;
    if (!cv || !sc) return;
    const gl = cv.getContext("webgl", {
      antialias: false,
      alpha: false,
      powerPreference: "high-performance",
    });
    if (!gl) return;

    const DPR = Math.min(DPR_CAP, window.devicePixelRatio || 1);

    const compile = (type: number, src: string) => {
      const s = gl!.createShader(type)!;
      gl!.shaderSource(s, src);
      gl!.compileShader(s);
      if (!gl!.getShaderParameter(s, gl!.COMPILE_STATUS))
        console.error("[CinematicBackground] shader:", gl!.getShaderInfoLog(s));
      return s;
    };
    const prog = gl!.createProgram()!;
    gl!.attachShader(prog, compile(gl!.VERTEX_SHADER, VERT));
    gl!.attachShader(prog, compile(gl!.FRAGMENT_SHADER, FRAG));
    gl!.linkProgram(prog);
    gl!.useProgram(prog);
    const buf = gl!.createBuffer();
    gl!.bindBuffer(gl!.ARRAY_BUFFER, buf);
    gl!.bufferData(gl!.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl!.STATIC_DRAW);
    const loc = gl!.getAttribLocation(prog, "p");
    gl!.enableVertexAttribArray(loc);
    gl!.vertexAttribPointer(loc, 2, gl!.FLOAT, false, 0, 0);
    const uRes = gl!.getUniformLocation(prog, "u_res");
    const uTime = gl!.getUniformLocation(prog, "u_time");
    const uIntro = gl!.getUniformLocation(prog, "u_intro");

    function resizeGl() {
      const w = Math.floor(window.innerWidth * DPR);
      const h = Math.floor(window.innerHeight * DPR);
      cv!.width = w; cv!.height = h;
      gl!.viewport(0, 0, w, h);
      gl!.uniform2f(uRes, w, h);
    }
    resizeGl();
    window.addEventListener("resize", resizeGl);

    // 星流层
    const sx = sc.getContext("2d")!;
    let stars: any[] = [];
    function initStars() {
      const w = window.innerWidth, h = window.innerHeight;
      sc!.width = w * DPR; sc!.height = h * DPR;
      sx.setTransform(DPR, 0, 0, DPR, 0, 0);
      const count = Math.min(280, Math.floor((w * h) / 7200));
      stars = Array.from({ length: count }, () => ({
        x: Math.random() * w, y: Math.random() * h, px: 0, py: 0,
        z: Math.random() * 0.9 + 0.2, r: Math.random() * 1.4 + 0.3,
        tw: Math.random() * 6.28, sp: Math.random() * 0.6 + 0.2,
      }));
      stars.forEach((s) => { s.px = s.x; s.py = s.y; });
    }
    initStars();
    window.addEventListener("resize", initStars);

    const start = performance.now();
    let raf = 0;
    function frame(ts: number) {
      const t = ts * 0.001;
      const el = (ts - start) / 1000;
      const intro = Math.min(1, el / 2.6);
      const ease = intro * intro * (3 - 2 * intro);
      gl!.uniform1f(uTime, t);
      gl!.uniform1f(uIntro, ease);
      gl!.drawArrays(gl!.TRIANGLES, 0, 3);
      // 星流拖尾
      sx.globalCompositeOperation = "destination-out";
      sx.fillStyle = "rgba(0,0,0,0.14)";
      sx.fillRect(0, 0, window.innerWidth, window.innerHeight);
      sx.globalCompositeOperation = "source-over";
      const drift = t * 26;
      for (const s of stars) {
        s.px = s.x; s.py = s.y;
        s.y = (s.y + drift * s.z) % window.innerHeight;
        if (s.y < s.py) s.y = s.py;
        const a = (0.3 + 0.5 * Math.sin(t * s.sp + s.tw)) * ease;
        sx.strokeStyle = `rgba(225,215,255,${Math.max(0, a)})`;
        sx.lineWidth = s.r; sx.lineCap = "round";
        sx.shadowBlur = 7 * s.z; sx.shadowColor = "rgba(165,130,255,0.85)";
        sx.beginPath(); sx.moveTo(s.px, s.py); sx.lineTo(s.x, s.y); sx.stroke();
      }
      sx.shadowBlur = 0;
      raf = requestAnimationFrame(frame);
    }
    raf = requestAnimationFrame(frame);

    const onVis = () => { if (!document.hidden) raf = requestAnimationFrame(frame); };
    document.addEventListener("visibilitychange", onVis);

    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener("visibilitychange", onVis);
      window.removeEventListener("resize", resizeGl);
      window.removeEventListener("resize", initStars);
      gl!.getExtension("WEBGL_lose_context")?.loseContext();
    };
  }, [active]);

  return (
    <>
      <style>{CSS}</style>
      <div className="cb-root" style={{ opacity: active ? 1 : 0 }}>
        <canvas ref={glRef} className="cb-gl" />
        <canvas ref={starRef} className="cb-stars" />
        <div className="cb-bloom" />
        <div className="cb-vignette" />
      </div>
    </>
  );
}

export default CinematicBackground;

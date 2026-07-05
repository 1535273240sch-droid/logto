"""修复前端 — 在聊天窗口中添加成果物下载按钮

在 status-widget.html 的 done 事件处理中：
- 如果 event.artifacts 存在，渲染下载按钮卡片
- 每个成果物显示：图标 + 标题 + 文件名 + 下载按钮
"""

import os

filepath = os.environ.get("WIDGET_FILE", "/dream-os/frontend/status-widget.html")
with open(filepath, "r") as f:
    content = f.read()

# ── 修复1: 在 finishStream 中添加成果物渲染 ──

old_finish = """  // ── Finish Stream ──
  function finishStream(event) {
    if (event) {
      intentLabel = event.intent || intentLabel;
      toolCount = event.tool_count || toolCount;
      statusTitle.textContent = '已完成';
      statusDot.className = 'pulse done';
    } else {
      statusTitle.textContent = '处理完成';
      statusDot.className = 'pulse done';
    }
    updateSummary();
    sendBtn.textContent = '发送';
    sendBtn.disabled = false;
    sendBtn.classList.remove('sending');
    isRunning = false;

    // Remove cursor blink after a moment
    setTimeout(() => {
      const cursor = responseContent.querySelector('.cursor');
      if (cursor) cursor.remove();
    }, 1500);
  }"""

new_finish = """  // ── Finish Stream ──
  function finishStream(event) {
    if (event) {
      intentLabel = event.intent || intentLabel;
      toolCount = event.tool_count || toolCount;
      statusTitle.textContent = '已完成';
      statusDot.className = 'pulse done';

      // ── 成果物下载按钮 ──
      if (event.artifacts && event.artifacts.length > 0) {
        renderArtifacts(event.artifacts);
      }
    } else {
      statusTitle.textContent = '处理完成';
      statusDot.className = 'pulse done';
    }
    updateSummary();
    sendBtn.textContent = '发送';
    sendBtn.disabled = false;
    sendBtn.classList.remove('sending');
    isRunning = false;

    // Remove cursor blink after a moment
    setTimeout(() => {
      const cursor = responseContent.querySelector('.cursor');
      if (cursor) cursor.remove();
    }, 1500);
  }

  // ── Render Artifacts (成果物下载区) ──
  function renderArtifacts(artifacts) {
    // 创建成果物容器
    let container = document.getElementById('artifactContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'artifactContainer';
      container.className = 'artifact-container';
      // 插入到响应区后面
      responseArea.parentNode.insertBefore(container, responseArea.nextSibling);
    }

    const completed = artifacts.filter(a => a.status === 'completed');
    if (!completed.length) return;

    container.innerHTML = `
      <div class="artifact-header">
        <span class="artifact-title">📦 成果物 (${completed.length})</span>
      </div>
      <div class="artifact-grid">
        ${completed.map(a => `
          <div class="artifact-card" onclick="downloadArtifact('${a.id}', '${a.filename}')">
            <div class="artifact-icon">${getArtifactIcon(a.artifact_type)}</div>
            <div class="artifact-info">
              <div class="artifact-name">${escapeHtml(a.title || a.filename)}</div>
              <div class="artifact-meta">${a.artifact_type.toUpperCase()} · ${formatSize(a.file_size)} · ${a.generation_time_ms}ms</div>
            </div>
            <div class="artifact-download">⬇</div>
          </div>
        `).join('')}
      </div>
    `;
    container.style.display = 'block';
  }

  function getArtifactIcon(type) {
    const icons = {
      markdown: '📝', word: '📁', pdf: '📄', html: '🌐', txt: '📃',
      excel: '📊', csv: '📊', markdown_table: '📋',
      ppt: '📽', speech: '🎤',
      mermaid: '🔀', mindmap: '🧠', flowchart: '🔄', architecture: '🏗',
      er_diagram: '🗃', sequence_diagram: '↔', gantt: '📅', org_chart: '👥',
      bar_chart: '📊', line_chart: '📈', pie_chart: '🥧',
      radar_chart: '🎯', trend_chart: '📉',
      code: '💻', api_doc: '📖',
    };
    return icons[type] || '📦';
  }

  function formatSize(bytes) {
    if (!bytes) return '—';
    if (bytes < 1024) return bytes + 'B';
    if (bytes < 1024*1024) return (bytes/1024).toFixed(1) + 'KB';
    return (bytes/1024/1024).toFixed(1) + 'MB';
  }

  // ── Download Artifact ──
  window.downloadArtifact = async function(id, filename) {
    try {
      const r = await fetch('/api/artifacts/' + id + '/download');
      if (!r.ok) throw new Error('下载失败');
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || 'artifact';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Download error:', e);
      alert('下载失败: ' + e.message);
    }
  };"""

content = content.replace(old_finish, new_finish)

# ── 修复2: 添加成果物 CSS 样式 ──

old_style_end = "</style>"

artifact_css = """
  /* ── Artifact 成果物样式 ── */
  .artifact-container {
    display: none;
    margin-top: 16px;
    padding: 16px;
    background: rgba(26, 26, 46, 0.8);
    border-radius: 12px;
    border: 1px solid rgba(108, 92, 231, 0.3);
  }
  .artifact-header {
    margin-bottom: 12px;
  }
  .artifact-title {
    font-size: 14px;
    font-weight: 600;
    color: #e8e8f0;
  }
  .artifact-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 10px;
  }
  .artifact-card {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    background: rgba(108, 92, 231, 0.1);
    border: 1px solid rgba(108, 92, 231, 0.2);
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .artifact-card:hover {
    background: rgba(108, 92, 231, 0.25);
    border-color: rgba(108, 92, 231, 0.5);
    transform: translateY(-1px);
  }
  .artifact-icon {
    font-size: 24px;
    flex-shrink: 0;
  }
  .artifact-info {
    flex: 1;
    min-width: 0;
  }
  .artifact-name {
    font-size: 13px;
    font-weight: 500;
    color: #e8e8f0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .artifact-meta {
    font-size: 11px;
    color: #808090;
    margin-top: 2px;
  }
  .artifact-download {
    font-size: 18px;
    color: #00cec9;
    flex-shrink: 0;
    opacity: 0.7;
    transition: opacity 0.2s;
  }
  .artifact-card:hover .artifact-download {
    opacity: 1;
  }
</style>"""

# 只替换最后一个 </style>
last_style_pos = content.rfind(old_style_end)
if last_style_pos > 0:
    content = content[:last_style_pos] + artifact_css

with open(filepath, "w") as f:
    f.write(content)

print("✅ status-widget.html 修复完成（成果物下载按钮）")

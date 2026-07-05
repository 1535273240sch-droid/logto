// Artifact Engine — 成果物下载功能
// 自动注入到 Dream OS 前端

(function() {
  // ── 成果物渲染 ──
  window.renderArtifacts = function(artifacts) {
    const completed = artifacts.filter(a => a.status === 'completed');
    if (!completed.length) return;

    let container = document.getElementById('artifactContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'artifactContainer';
      container.className = 'artifact-container';
      const ra = document.getElementById('responseArea');
      if (ra) ra.parentNode.insertBefore(container, ra.nextSibling);
    }

    container.innerHTML = '<div class="artifact-header"><span class="artifact-title">📦 成果物 (' + completed.length + ')</span></div>' +
      '<div class="artifact-grid">' +
      completed.map(a =>
        '<div class="artifact-card" onclick="downloadArtifact(\'' + a.id + '\', \'' + (a.filename||'artifact') + '\')">' +
          '<div class="artifact-icon">' + getArtifactIcon(a.artifact_type) + '</div>' +
          '<div class="artifact-info">' +
            '<div class="artifact-name">' + escapeHtml2(a.title || a.filename) + '</div>' +
            '<div class="artifact-meta">' + a.artifact_type.toUpperCase() + ' · ' + formatSize(a.file_size) + '</div>' +
          '</div>' +
          '<div class="artifact-download">⬇</div>' +
        '</div>'
      ).join('') +
      '</div>';
    container.style.display = 'block';
  };

  // ── 下载成果物 ──
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
  };

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

  function escapeHtml2(text) {
    const d = document.createElement('div');
    d.textContent = text || '';
    return d.innerHTML;
  }

  // ── Hook finishStream ──
  // 等待页面加载完成后，拦截 done 事件
  const origHandleEvent = window.handleEvent;
  if (origHandleEvent) {
    window.handleEvent = function(event) {
      origHandleEvent(event);
      if (event.type === 'done' && event.artifacts && event.artifacts.length > 0) {
        renderArtifacts(event.artifacts);
      }
    };
  }

  // 备选方案：通过 MutationObserver 监听 SSE 内容变化
  const observer = new MutationObserver(function() {
    // 如果检测到 "成果物已生成" 文字，自动拉取
    const rc = document.getElementById('responseContent');
    if (rc && rc.textContent.includes('成果物已生成') && !document.getElementById('artifactContainer')) {
      fetch('/api/artifacts').then(r => r.json()).then(d => {
        if (d.artifacts && d.artifacts.length) renderArtifacts(d.artifacts);
      }).catch(() => {});
    }
  });

  const ra = document.getElementById('responseArea');
  if (ra) {
    observer.observe(ra, { childList: true, subtree: true, characterData: true });
  }
})();

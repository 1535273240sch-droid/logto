#!/bin/bash
# Dream OS V3 — 给服务器上所有前端页面添加 V3 入口
# 用法: 服务器恢复后执行 ./patch_frontend_nav.sh
#
# 功能: 在 status-widget.html / project-workspace.html / tool-center.html
#       的导航栏中加入 "🤖 自主开发" 链接，让用户能从这些页面进入 V3 控制台
set -e

SERVER="1.14.125.204"
USER="root"
PASS="Sch13255884503"
SSH="sshpass -p ${PASS} ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 ${USER}@${SERVER}"

echo "═══════════════════════════════════════════════"
echo "  Dream OS V3 — 前端导航补丁"
echo "═══════════════════════════════════════════════"

${SSH} 'bash -s' <<'REMOTE_EOF'
set -e
cd /dream-os/frontend

# 给每个页面添加 V3 入口 (如果尚未添加)
for page in status-widget.html project-workspace.html tool-center.html; do
    if [ ! -f "$page" ]; then
        echo "⚠️ 跳过 $page (文件不存在)"
        continue
    fi

    if grep -q "v3-dev.html" "$page"; then
        echo "✓ $page 已包含 V3 入口"
        continue
    fi

    # 备份
    cp "$page" "${page}.bak.v3"

    # 在 tool-center.html 链接后插入 v3-dev.html 链接
    # 使用 sed 在最后一个 </nav> 前插入
    if grep -q 'tool-center.html' "$page"; then
        sed -i 's|<a href="tool-center.html"|<a href="v3-dev.html">🤖 自主开发</a>\n    <a href="tool-center.html"|' "$page"
        echo "✅ $page 已添加 V3 入口"
    elif grep -q 'project-workspace.html' "$page"; then
        sed -i 's|<a href="project-workspace.html"|<a href="v3-dev.html">🤖 自主开发</a>\n    <a href="project-workspace.html"|' "$page"
        echo "✅ $page 已添加 V3 入口"
    elif grep -q 'status-widget.html' "$page"; then
        sed -i 's|<a href="status-widget.html"|<a href="v3-dev.html">🤖 自主开发</a>\n    <a href="status-widget.html"|' "$page"
        echo "✅ $page 已添加 V3 入口"
    else
        echo "⚠️ $page 没有找到导航栏，跳过"
    fi
done

echo ""
echo "完成！现在所有页面都可以通过导航栏访问 V3 自主开发控制台"
REMOTE_EOF

echo ""
echo "═══════════════════════════════════════════════"
echo "  前端导航补丁完成"
echo "═══════════════════════════════════════════════"

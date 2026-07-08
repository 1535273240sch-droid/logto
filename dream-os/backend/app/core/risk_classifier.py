"""命令风险分级 — 三级安全体系"""
import re

# 禁止执行的模式（FORBIDDEN）
BLOCKED_PATTERNS = [
    r'rm\s+-rf\s+/\s*$',      # 删除根目录(仅 / 自身)
    r'rm\s+-rf\s+~\s*$',      # 删除用户主目录(仅 ~ 自身)
    r':\(\)\{.*\};:',         # Fork 炸弹
    r'dd\s+.*of=/dev/',       # 写入设备文件
    r'mkfs\.',                 # 格式化文件系统
    r'chmod\s+-R\s+777\s+/',  # 全局权限修改
    r'curl.*\|\s*sh',         # 管道执行远程脚本
    r'wget.*\|\s*bash',       # 管道执行远程脚本
    r'poweroff|shutdown|reboot|init\s+[06]',  # 关机/重启
    r'>\s*/etc/',              # 覆盖系统配置
]

# 安全命令前缀（SAFE）
SAFE_PREFIXES = [
    'echo', 'ls', 'cat', 'head', 'tail', 'wc', 'grep', 'find',
    'df', 'du', 'free', 'uptime', 'uname', 'hostname', 'whoami', 'id',
    'date', 'pwd', 'which', 'whereis',
    'python3', 'python', 'pip', 'pip3',
    'node', 'npm', 'npx', 'pnpm', 'yarn',
    'git', 'docker', 'docker-compose',
    'systemctl', 'journalctl',
    'ps', 'top', 'ss', 'netstat', 'ip',
    'mkdir', 'touch', 'cp', 'mv',
    'tar', 'gzip', 'gunzip', 'unzip', 'zip',
    'chmod', 'chown', 'curl', 'wget',
    'apt-get', 'apt', 'dpkg',
    'kill', 'pkill',
    'sort', 'uniq', 'awk', 'sed', 'cut', 'tr',
    # V3 开发所需的安全命令
    'cd', 'nohup', 'sleep', 'source', 'export',
    'lsof', 'tree', 'stat', 'file', 'wc',
    'virtualenv', 'venv', 'dotenv', 'wait',
    # rm 不在白名单 — 由参数单独判断
]

# 即使命令名 SAFE,如果带这些危险参数也升级为 DANGEROUS
DANGEROUS_FLAGS = [
    (r'rm\s+.*-rf?\b',    "rm 含 -rf/-r 递归删除"),
    (r'rm\s+.*-f\b',      "rm 含 -f 强制删除"),
    (r'>\s*/(etc|boot|bin|sbin|usr|var|root|proc|sys)\b', "输出重定向到系统路径"),
    (r'curl\s+.*\|\s*',   "curl 管道操作"),
    (r'wget\s+.*\|\s*',   "wget 管道操作"),
    (r'chmod\s+777',      "chmod 777 权限"),
    (r'chmod\s+-R',       "chmod 递归"),
    (r'chown\s+-R',       "chown 递归"),
    (r'kill\s+-9',        "kill -9 强制杀进程"),
    (r'systemctl\s+stop', "systemctl stop 停止服务"),
]


class RiskLevel:
    SAFE = "safe"
    DANGEROUS = "dangerous"
    FORBIDDEN = "forbidden"


def classify(command: str) -> tuple[str, str]:
    cmd = command.strip()
    first_word = cmd.split()[0] if cmd else ""
    base_cmd = first_word.split("/")[-1]

    # 第一关：FORBIDDEN 模式
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, cmd):
            return RiskLevel.FORBIDDEN, f"命令匹配禁止模式: {pattern}"

    # 第二关：危险参数（即使命令在白名单里）
    for pattern, reason in DANGEROUS_FLAGS:
        if re.search(pattern, cmd):
            return RiskLevel.DANGEROUS, f"危险参数: {reason}"

    # 第三关：rm 无危险参数 → SAFE（只允许删单个文件）
    if base_cmd == "rm":
        return RiskLevel.SAFE, "rm 无递归/强制参数，安全"

    # 第四关：SAFE 白名单
    if base_cmd in SAFE_PREFIXES:
        return RiskLevel.SAFE, f"命令前缀 '{base_cmd}' 在白名单中"

    # 兜底 → DANGEROUS
    return RiskLevel.DANGEROUS, f"命令 '{base_cmd}' 不在安全白名单中"

import sys, json, re
from pathlib import Path

# 日志写到仓库外（~/.codex/），避免把调用载荷（可能含旧名称等敏感字面量）提交进 git
LOG = Path.home() / ".codex" / "guard_last_payload.json"

DANGEROUS = [
    r"git\s+push\s+.*(-f|--force)", r"git\s+reset\s+--hard",
    r"git\s+filter-branch", r"git\s+rebase", r"git\s+commit\s+--amend",
    r"rm\s+-rf\s+/", r"rmdir\s+/s", r"del\s+/[sq]", r"gh\s+repo\s+delete",
]
# 受保护文件：评测最终产物。会话首次生成不受影响（文件不存在时放行），
# 生成后想重新生成需你在 /hooks 里临时禁用本钩子
PROTECTED = ["eval/results.json", "eval/report.md"]

def strings_of(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings_of(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings_of(v)

def main():
    event = sys.argv[sys.argv.index("--hook") + 1] if "--hook" in sys.argv else "PreToolUse"
    raw = sys.stdin.read() or "{}"
    try:
        payload = json.loads(raw)
    except Exception:
        payload = {"raw": raw}
    try:  # 记录原始 payload，schema 随版本变化时用它排查
        LOG.write_text(raw, encoding="utf-8")
    except Exception:
        pass
    if event != "PreToolUse":
        return
    text = "\n".join(strings_of(payload))
    for pat in DANGEROUS:
        if re.search(pat, text, re.I):
            print(f"[guard] 已拦截高危操作（命中规则: {pat}）。如确有需要，请让用户手动执行。", file=sys.stderr)
            sys.exit(2)
    for s in strings_of(payload):
        norm = s.replace("\\", "/")
        for p in PROTECTED:
            if p in norm and Path(p).exists():
                print(f"[guard] {p} 是评测最终产物，禁止修改。确需重新生成请用户在 /hooks 临时禁用。", file=sys.stderr)
                sys.exit(2)

if __name__ == "__main__":
    main()
"""End-to-end SSE test against the running FastAPI server."""
import httpx

URL = "http://localhost:8000/api/chat"
Q = "帮我查一下上个月华南区的销售总额"

with httpx.stream("POST", URL, json={"question": Q}, timeout=30.0) as r:
    print("status:", r.status_code)
    for line in r.iter_lines():
        if line.startswith("data:"):
            print(line[:160])
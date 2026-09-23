#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对外服务调用示例（第三方程序视角）
====================================
本脚本模拟“外部程序”去调用 app.py 暴露的 HTTP 服务，
证明 Ollama 已被包装成对外的 REST 服务，可被任意程序/设备使用。

运行：
    python test_client.py                # 默认访问 http://127.0.0.1:5000
    python test_client.py --host 192.168.1.10 --port 5000
"""
import argparse
import json
import urllib.request


def chat(host, port, model, prompt):
    url = "http://%s:%d/chat" % (host, port)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST"
    )
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=600) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                c = (obj.get("message") or {}).get("content") or ""
                if c:
                    print(c, end="", flush=True)
            except Exception:
                pass
    print()


def main():
    ap = argparse.ArgumentParser(description="Ollama 对外服务调用示例")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--prompt", default="用一句话介绍你自己。")
    args = ap.parse_args()
    print(">>> 调用 %s:%d 的 /chat 接口，模型 %s" % (args.host, args.port, args.model))
    chat(args.host, args.port, args.model, args.prompt)


if __name__ == "__main__":
    main()

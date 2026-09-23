#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama 模型下载、调用与对外服务 —— 演示项目服务端
==========================================================

零第三方依赖，仅使用 Python 标准库（http.server / urllib / subprocess）。
对应实验要求的三步：
  1) 下载模型   -> POST /pull   (内部调用 `ollama pull`)
  2) 调用模型   -> POST /chat   (内部调用 ollama /api/chat，流式返回)
  3) 对外服务   -> 本程序就是一个 HTTP 服务，对外暴露 REST API + 网页对话界面，
                  其它程序/设备可通过 http://本机IP:端口 调用本地模型。

运行方式：
    python app.py
    python app.py --port 5000 --ollama http://127.0.0.1:11434

浏览器打开 http://127.0.0.1:5000 即可使用网页对话界面。
"""

import argparse
import json
import os
import subprocess
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OLLAMA_HOST = "http://127.0.0.1:11434"


def _read_body(handler):
    """读取请求体并解析为 JSON。"""
    length = int(handler.headers.get("Content-Length", 0) or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        return json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        return {}


def _proxy(method, url, payload=None, stream=False):
    """向 Ollama 服务转发请求，返回 (status, response_or_file)。"""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=600)
    if stream:
        return resp.status, resp
    return resp.status, resp.read().decode("utf-8", "replace")


class Handler(BaseHTTPRequestHandler):
    # 关闭默认日志噪音，保留必要信息
    def log_message(self, fmt, *args):
        print("[server]", fmt % args)

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ---------- 网页对话界面 ----------
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            try:
                with open(os.path.join(BASE_DIR, "static", "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send(404, "前端页面缺失")
            return

        if self.path == "/models":
            try:
                status, text = _proxy("GET", OLLAMA_HOST + "/api/tags")
                self._send(status, text)
            except Exception as e:
                self._send(502, json.dumps({"error": str(e)}, ensure_ascii=False))
            return

        self._send(404, json.dumps({"error": "not found"}, ensure_ascii=False))

    # ---------- 下载 / 调用 等接口 ----------
    def do_POST(self):
        if self.path == "/pull":
            return self._handle_pull()
        if self.path == "/chat":
            return self._handle_chat()
        self._send(404, json.dumps({"error": "not found"}, ensure_ascii=False))

    # 1) 下载模型：调用 `ollama pull`，以 SSE 流式回传进度
    def _handle_pull(self):
        body = _read_body(self)
        model = (body.get("model") or "").strip()
        if not model:
            self._send(400, json.dumps({"error": "缺少 model 参数"}, ensure_ascii=False))
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        proc = subprocess.Popen(
            ["ollama", "pull", model],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        for line in proc.stdout:
            line = line.rstrip("\n")
            self.wfile.write(("data: " + json.dumps({"log": line}, ensure_ascii=False) + "\n\n").encode("utf-8"))
            self.wfile.flush()
        proc.wait()
        done = {"status": "done" if proc.returncode == 0 else "failed", "code": proc.returncode}
        self.wfile.write(("data: " + json.dumps(done, ensure_ascii=False) + "\n\n").encode("utf-8"))
        self.wfile.flush()

    # 2) 调用模型：转发到 ollama /api/chat，SSE 流式回传
    def _handle_chat(self):
        body = _read_body(self)
        model = body.get("model") or "qwen3:8b"
        messages = body.get("messages") or []
        payload = {"model": model, "messages": messages, "stream": True}
        try:
            status, resp = _proxy("POST", OLLAMA_HOST + "/api/chat", payload, stream=True)
        except Exception as e:
            self._send(502, json.dumps({"error": str(e)}, ensure_ascii=False))
            return
        self.send_response(status)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        for raw in resp:
            self.wfile.write(raw if isinstance(raw, bytes) else raw.encode("utf-8"))
            self.wfile.flush()
        resp.close()


def main():
    global OLLAMA_HOST
    ap = argparse.ArgumentParser(description="Ollama 对外服务演示")
    ap.add_argument("--port", type=int, default=5000, help="对外服务端口")
    ap.add_argument("--ollama", default=OLLAMA_HOST, help="Ollama 服务地址")
    ap.add_argument("--host", default="0.0.0.0", help="监听地址，0.0.0.0 可被局域网访问")
    args = ap.parse_args()
    OLLAMA_HOST = args.ollama

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("=" * 50)
    print("Ollama 演示服务已启动")
    print("  本机访问 : http://127.0.0.1:%d" % args.port)
    print("  局域网访问: http://<本机IP>:%d  (需 OLLAMA_HOST=0.0.0.0 启动 ollama)" % args.port)
    print("  模型源   : %s" % OLLAMA_HOST)
    print("=" * 50)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
        server.shutdown()


if __name__ == "__main__":
    main()

# Ollama 模型下载、调用与对外服务 —— 演示项目

> 对应实验要求：**① 下载模型　② 调用模型　③ 对外（HTTP）服务**

零第三方依赖，仅用 Python 标准库实现，便于直接运行与提交。

## 一、环境准备

1. 操作系统：Windows / macOS / Linux
2. Python：3.8 及以上
3. 安装并启动 Ollama：<https://ollama.com>（Windows 双击 `OllamaSetup.exe` 即可）
4. 验证 Ollama 已就绪：浏览器或命令行访问 `http://127.0.0.1:11434` 能返回内容

## 二、目录结构

```
OllamaLab/
├── app.py            # 对外服务主程序（HTTP 服务 + 网页聊天界面）
├── static/
│   └── index.html    # 网页对话界面（下载模型 / 对话调用）
├── test_client.py    # 第三方程序调用示例（演示对外服务）
├── requirements.txt  # 依赖说明（本项目无第三方依赖）
├── 实验报告.md        # 实验目的、步骤与结果（可直接作为实验报告）
└── README.md         # 本文件
```

## 三、运行步骤

```powershell
# 1. 启动对外服务（默认端口 5000）
cd OllamaLab
python app.py

# 2. 浏览器打开网页界面
#    http://127.0.0.1:5000
#    - 在“① 下载模型”框输入 qwen3:8b 并点击“下载/拉取”
#    - 在“② 调用模型对话”框直接对话
```

## 四、对应三项要求

| 要求 | 本项目实现 | 关键接口 |
|------|-----------|----------|
| ① 下载模型 | 调用 `ollama pull`，流式回传进度 | `POST /pull` |
| ② 调用模型 | 转发到 Ollama `/api/chat`，流式对话 | `POST /chat` |
| ③ 对外服务 | 本程序即 HTTP 服务，网页 + REST API | `GET /`、`/models` |

## 五、对外服务（供其它程序/设备调用）

本服务监听 `0.0.0.0:5000`，对外暴露：

- 网页聊天界面：`http://<本机IP>:5000`
- 模型列表：`GET http://<本机IP>:5000/models`
- 对话接口：`POST http://<本机IP>:5000/chat`
  ```json
  { "model": "qwen3:8b", "messages": [{"role":"user","content":"你好"}] }
  ```
- 下载接口：`POST http://<本机IP>:5000/pull` → `{"model":"qwen3:8b"}`

**让局域网内其它设备访问**：先用 `OLLAMA_HOST=0.0.0.0` 启动 Ollama（允许跨机访问），
再运行 `python app.py`，其他机器用 `http://你的IP:5000` 即可调用。

## 六、第三方程序调用示例

```powershell
# 另开一个终端，模拟“外部程序”调用本地模型服务
python test_client.py --prompt "用一句话介绍你自己"
```

输出即为模型返回的流式文本，证明本地模型已作为对外服务被成功调用。

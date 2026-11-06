本项目是一个简单的小说翻译软件。后端用 FastAPI，前端用 React + Vite + Tailwind。含有作品管理和章节管理和修改，以及作品专有名词的记录和修改。

## 安装与运行

```bash
./install.sh   # 创建 .venv，安装后端依赖，npm install 前端依赖
./start.sh     # 后台启动后端 (uvicorn :8000) + 前端 (vite :5173)
./stop.sh      # 停止
```

启动后打开 http://localhost:5173

## 配置

复制 `.env.example` 为 `.env` 并填入你的密钥。`.env` 支持两种 LLM 提供商：

```ini
# 选择使用哪个提供商: "deepseek" 或 "openrouter"
LLM_PROVIDER="deepseek"

# DeepSeek
DEEPSEEK_API_KEY="your_deepseek_key_here"
DEEPSEEK_MODEL="deepseek-reasoner"

# OpenRouter
OPENROUTER_API_KEY="your_openrouter_key_here"
OPENROUTER_MODEL="deepseek/deepseek-r1"
```

把 `LLM_PROVIDER` 设为 `deepseek` 或 `openrouter` 即可切换后端，无需改代码。

## 架构

- `backend/` — FastAPI 应用，直接读写 `works/` 目录下的 JSON 文件（无数据库）。
- `frontend/` — React + Vite + TypeScript + Tailwind 单页应用。
- `works/` — 作品/章节/名词的 JSON 文件存储目录。

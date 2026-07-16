# LabSafe Mom 免费部署指南

推荐组合：后端部署到 Render Free Web Service，前端部署到 Vercel。Cloudflare Pages 可以作为备用，但当前项目是 Next.js 应用，Vercel 对这种结构最省心。

## 0. 先准备 GitHub 仓库

1. 在 GitHub 新建一个仓库。
2. 把整个 `LabSafeMom` 文件夹推送到仓库。
3. 确认不要提交这些文件：
   - `backend/.env`
   - `frontend/.env.local`
   - `frontend/node_modules/`
   - `frontend/.next/`
   - `backend/__pycache__/`

## 1. 部署后端到 Render

Render 可以直接读取根目录的 `render.yaml`。如果你不使用 Blueprint，也可以手动创建 Web Service。

### 方式 A：使用 Blueprint

1. 打开 Render Dashboard。
2. 选择 `New` -> `Blueprint`。
3. 连接 GitHub 仓库。
4. Render 会读取根目录的 `render.yaml` 并创建 `labsafe-mom-api`。
5. 填写环境变量：
   - `OPENAI_API_KEY`: 你的模型 API Key。
   - `OPENAI_BASE_URL`: 如果你使用 DeepSeek 或其他 OpenAI-compatible 服务，填写对应 base URL；如果使用 OpenAI 官方接口，可留空。
6. 首次部署完成后，记录后端地址，例如：
   - `https://labsafe-mom-api.onrender.com`
7. 打开健康检查：
   - `https://labsafe-mom-api.onrender.com/api/v1/health`

### 方式 B：手动创建 Web Service

Render 设置如下：

| 项目 | 值 |
| --- | --- |
| Root Directory | `backend` |
| Runtime | `Python` |
| Build Command | `pip install --upgrade pip && pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/api/v1/health` |
| Plan | `Free` |

环境变量如下：

| Key | Value |
| --- | --- |
| `PYTHON_VERSION` | `3.12.8` |
| `ENVIRONMENT` | `production` |
| `LOG_LEVEL` | `INFO` |
| `LOG_FORMAT` | `json` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./labsafe.db` |
| `DATABASE_URL_SYNC` | `sqlite:///./labsafe.db` |
| `CORS_ORIGINS` | 先填 `["http://localhost:3000"]`，前端上线后改成 Vercel 域名 |
| `AI_MODEL` | `deepseek-v4-pro`，或改成你实际使用的模型 |
| `OPENAI_API_KEY` | 你的模型 API Key |
| `OPENAI_BASE_URL` | OpenAI-compatible 服务的 base URL，可选 |

## 2. 部署前端到 Vercel

1. 打开 Vercel Dashboard。
2. 选择 `Add New` -> `Project`。
3. 导入同一个 GitHub 仓库。
4. 在项目设置里把 `Root Directory` 设为：
   - `frontend`
5. Framework Preset 选择：
   - `Next.js`
6. Build 设置通常保持默认：
   - Install Command: `npm ci`
   - Build Command: `npm run build`
7. 添加环境变量：
   - Key: `NEXT_PUBLIC_API_URL`
   - Value: `https://你的-render后端地址.onrender.com/api/v1`
8. Deploy。
9. Vercel 部署成功后，记录前端地址，例如：
   - `https://labsafe-mom.vercel.app`

## 3. 回到 Render 更新 CORS

前端上线后，回到 Render 后端服务的 Environment 页面，把：

```text
CORS_ORIGINS=["https://labsafe-mom.vercel.app"]
```

如果你还想同时允许本地调试：

```text
CORS_ORIGINS=["https://labsafe-mom.vercel.app","http://localhost:3000","http://127.0.0.1:3000"]
```

保存后让 Render 重新部署一次。

## 4. 验证

按这个顺序检查：

1. 后端健康检查可以打开：
   - `https://你的-render后端地址.onrender.com/api/v1/health`
2. 前端首页可以打开：
   - `https://你的-vercel地址.vercel.app`
3. 在前端粘贴一个中文 protocol，点击分析。
4. 如果前端提示网络错误，优先检查：
   - Vercel 的 `NEXT_PUBLIC_API_URL` 是否包含 `/api/v1`
   - Render 的 `CORS_ORIGINS` 是否包含完整前端域名
   - Render 后端是否因为 Free 计划冷启动还没醒来

## 5. Cloudflare Pages 备用说明

当前项目是 Next.js 应用，优先建议使用 Vercel。如果一定要用 Cloudflare Pages，需要注意：

- Cloudflare Pages 的静态 Next.js 方案要求 Next.js static export。
- 当前项目有 `/report/[id]` 这种动态路由，直接改成 static export 会比较麻烦。
- 如果选择 Cloudflare，建议走 Cloudflare Workers 的 Next.js 路线，而不是普通 Pages 静态导出。

## 6. 免费方案的限制

- Render Free 可能冷启动，第一次请求会慢一些。
- 当前免费配置使用 SQLite，本地文件会随云端实例重建或重新部署而丢失历史报告；知识库会在启动时重新 seed。
- API Key 只能放 Render 后端环境变量，不能放进前端。
- 这个版本适合演示、比赛展示和小范围试用；如果要长期公开给很多用户使用，建议后续升级到稳定数据库和付费实例。

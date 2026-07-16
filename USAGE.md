# LabSafe Mom v2.0 — 使用指南

---

## 前置条件

- **Python 3.11+** （后端）
- **Node.js 18+** （前端）
- **OpenAI 兼容 API Key**（DeepSeek / OpenAI / 其他中转）

---

## 第一步：配置 API Key

编辑 `backend\.env` 文件：

```
OPENAI_API_KEY=sk-你的真实key
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-v4-pro
DATABASE_URL=sqlite:///./labsafe.db
```

> **支持的 API 提供商：**
> - DeepSeek: `OPENAI_BASE_URL=https://api.deepseek.com/v1`
> - OpenAI 官方: 不填 `OPENAI_BASE_URL`，MODEL 填 `gpt-4o`
> - 其他兼容接口: 填对应 base_url 即可

---

## 第二步：安装依赖

### 后端

```bash
cd E:\bme\iGEM\软件\LabSafeMom\backend
pip install -r requirements.txt
```

### 前端

```bash
cd E:\bme\iGEM\软件\LabSafeMom\frontend
npm install
```

---

## 第三步：启动后端

打开 **第一个终端**：

```bash
cd E:\bme\iGEM\软件\LabSafeMom\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

看到以下输出表示成功：

```
INFO     app_main               app_starting
INFO     app_main               database_initialized
Seeded 69 hazardous substances into database.
INFO     Uvicorn running on http://0.0.0.0:8000
```

验证后端：

```bash
curl http://localhost:8000/api/v1/health
```

应返回：

```json
{
  "status": "ok",
  "service": "LabSafe Mom API",
  "version": "2.0.0",
  "database": {"database": "connected"},
  "cache": {"size": 0, "hits": 0, "misses": 0, "enabled": true}
}
```

---

## 第四步：启动前端

打开 **第二个终端**：

```bash
cd E:\bme\iGEM\软件\LabSafeMom\frontend
npm run dev
```

看到输出：

```
  ▲ Next.js 14.x.x
  - Local:        http://localhost:3000
```

---

## 第五步：打开浏览器使用

访问 **http://localhost:3000**

你会看到 LabSafe Mom 的主页，包含：

- 🧬 标题和介绍
- 📁 文件拖拽上传区（支持拖拽时格式校验 + 文件预览）
- 🔬 8 类危险物质说明
- 风险等级颜色图例

### 上传 Protocol 文件

1. **拖拽文件**到上传区，或**点击**选择文件
2. 支持格式：**PDF / DOCX / TXT**
3. 最大文件：50MB
4. TXT 文件会显示内容预览

上传后自动跳转到分析进度页面。

### 等待分析完成

分析过程约 5-30 秒，系统自动：
1. 解析文件内容（PDF/DOCX/TXT）
2. 调用 AI 识别化学物质（结构化 JSON 输出）
3. 匹配风险数据库（本地缓存 → DB 精确匹配 → DB 模糊匹配 → AI 评估）
4. 生成结构化评估报告

进度页显示实时状态和耗时，采用指数退避轮询（2s → 4s → 8s → max 30s）。

### 查看报告

报告页包含：

| 区域 | 内容 |
|------|------|
| 📊 Executive Summary | 总体风险评分 + 物质数量统计 |
| ⚠️ Hazard Table | 所有识别出的危险物质表格（支持点击行展开详情） |
| 🚨 High-Risk Items | 高风险物质红色警告 + 防护建议 |
| 🛡️ Precautions | 针对中高风险物质的防护措施 |
| 📊 Risk By Population | 妊娠期/备孕期/哺乳期风险分布 |
| 📋 Disclaimer | 免责声明 |

### 打印/导出 PDF

点击 **🖨 打印报告** 按钮 → 浏览器打印对话框 → 另存为 PDF。

### 查看历史记录

点击导航栏 **📋 历史** 查看所有分析记录，支持分页浏览和删除。

---

## 第六步：关闭服务

在两个终端分别按 `Ctrl+C` 停止服务。

---

## 生产部署（Docker）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 设置 OPENAI_API_KEY 和 POSTGRES_PASSWORD

# 2. 启动生产环境
docker-compose -f docker-compose.prod.yml up -d

# 3. 查看日志
docker-compose -f docker-compose.prod.yml logs -f

# 4. 停止
docker-compose -f docker-compose.prod.yml down
```

---

## 运行测试

```bash
cd backend
python -m pytest tests/ -v
```

---

## 常见问题

### Q: 提示 "OpenAI API key not valid"

检查 `backend\.env` 中 `OPENAI_API_KEY` 是否正确。确保 `.env` 文件位于 `backend\` 目录下（与 `app\` 同级）。

### Q: 后端启动报错 port 8000 already in use

```bash
# 换端口
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
同时修改 `frontend\.env.local` 中 `NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1`。

### Q: 前端启动报错

```bash
cd frontend
rm -rf node_modules .next
npm install
npm run dev
```

### Q: 支持中文 protocol 吗？

支持。文件解析支持 UTF-8 和 GBK 编码，AI 可中英文混合识别。

### Q: 分析速度慢？

- 已内置 AI 结果缓存，相同物质不会重复调用 API
- 可在 `.env` 中设置 `CACHE_TTL_SECONDS=7200` 延长缓存时间
- 已使用异步并发处理，批量匹配物质

### Q: 如何查看缓存命中率？

访问 `http://localhost:8000/api/v1/health`，返回的 `cache` 字段包含命中率统计。

---

## 项目结构

```
LabSafeMom/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口（lifespan + rate limit + CORS）
│   │   ├── config.py            # 分层配置（AI/Cache/CORS/RateLimit）
│   │   ├── api/
│   │   │   ├── deps.py          # 依赖注入容器
│   │   │   └── routes/          # upload / analyze / report / history / feedback
│   │   ├── core/                # 领域层：enums / exceptions / logging
│   │   ├── services/            # 业务逻辑：extractor / matcher / generator / cache
│   │   ├── models/              # SQLAlchemy 2.0 ORM 模型
│   │   ├── schemas/             # Pydantic v2 数据模型 + AI 结构化输出
│   │   ├── prompts/             # YAML 提示词模板
│   │   └── db/                  # 数据库连接 + 种子数据（69种物质）
│   ├── tests/                   # 单元测试
│   ├── pyproject.toml           # ruff + mypy + pytest 配置
│   ├── Dockerfile.prod          # 生产 Docker 镜像
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── app/                 # 页面：首页 / 分析进度 / 报告 / 历史
│       ├── components/          # 组件：上传 / 表格 / 摘要 / PDF导出
│       ├── lib/                 # API 客户端 / 类型 / i18n
│       └── i18n/                # 中英文翻译
├── docker-compose.yml           # 开发环境
├── docker-compose.prod.yml      # 生产环境
├── .github/workflows/ci.yml     # CI/CD 流水线
└── USAGE.md                     # 本文件
```

---

## 新增功能（v2.0）

| 功能 | 说明 |
|------|------|
| 异步 AI 调用 | 非阻塞 OpenAI API，支持高并发 |
| 结构化 JSON 输出 | 不再解析 Markdown，直接获取严格 JSON |
| AI 缓存 | 相同物质不重复调用 API，节省费用 |
| 批量匹配 | 多种物质并发匹配，分析速度提升 3-5x |
| API 限流 | 防止 API 滥用和费用失控 |
| 结构化日志 | JSON 格式日志，支持 ELK/Grafana 采集 |
| 重试机制 | AI 调用失败自动重试（指数退避） |
| MIME 验证 | 上传文件不仅检查扩展名，还验证魔数 |
| 历史记录 | 查看/删除所有历史分析报告 |
| PDF 导出 | 浏览器打印 → 另存为 PDF |
| i18n 国际化 | 中英文双语支持 |
| 单元测试 | 10 个测试用例，57% 覆盖 |
| Docker 生产部署 | 多阶段构建 + 健康检查 + 资源限制 |
| GitHub Actions CI | Lint → Type Check → Test → Build |

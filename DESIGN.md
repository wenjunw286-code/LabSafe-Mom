# LabSafe Mom — 完整设计文档

---

## 1. 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           用户 (Browser)                                 │
│                    http://localhost:3000                                  │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js + TypeScript)                     │
│                         Port: 3000                                        │
│  ┌───────────┐  ┌───────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Upload    │  │ Analysis  │  │ Report View  │  │  Risk Report     │  │
│  │ Page      │  │ Status    │  │ Page         │  │  Components      │  │
│  └─────┬─────┘  └─────┬─────┘  └──────┬───────┘  └────────┬─────────┘  │
│        │              │               │                    │            │
│        └──────────────┴───────────────┴────────────────────┘            │
│                              │                                           │
│                    REST API Calls (fetch)                                │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Backend (Python FastAPI)                              │
│                         Port: 8000                                        │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                        API Layer                                   │   │
│  │  POST /api/v1/upload     →  文件上传                               │   │
│  │  POST /api/v1/analyze    →  触发分析                               │   │
│  │  GET  /api/v1/report/{id} → 获取报告                               │   │
│  │  GET  /api/v1/substances  → 查询风险数据库                          │   │
│  └──────────────────────────────┬───────────────────────────────────┘   │
│                                 │                                        │
│  ┌──────────────────────────────▼───────────────────────────────────┐   │
│  │                     Service Layer                                  │   │
│  │                                                                    │   │
│  │  ┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐  │   │
│  │  │ File Parser  │   │ Chemical         │   │ Risk Matcher     │  │   │
│  │  │              │   │ Extractor        │   │                  │  │   │
│  │  │ PDF→text     │──▶│ (OpenAI API)     │──▶│ DB lookup +      │  │   │
│  │  │ DOCX→text    │   │                  │   │ AI fallback      │  │   │
│  │  │ TXT→text     │   │ 提取:            │   │                  │  │   │
│  │  └──────────────┘   │ - 化学试剂       │   │ 匹配风险等级     │  │   │
│  │                      │ - 生物试剂       │   └────────┬─────────┘  │   │
│  │                      │ - 染料           │            │            │   │
│  │                      │ - 固定液         │            ▼            │   │
│  │                      │ - 有机溶剂       │   ┌──────────────────┐  │   │
│  │                      │ - 抗生素         │   │ Report           │  │   │
│  │                      │ - 放射性物质     │   │ Generator        │  │   │
│  │                      │ - 麻醉剂         │   │                  │  │   │
│  │                      │ - 危险步骤       │   │ 生成结构化报告   │  │   │
│  │                      └──────────────────┘   └──────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                 │                                        │
│  ┌──────────────────────────────▼───────────────────────────────────┐   │
│  │                     Data Layer                                     │   │
│  │  ┌──────────────────┐         ┌──────────────────────────────┐   │   │
│  │  │ SQLAlchemy ORM   │────────▶│ PostgreSQL                   │   │   │
│  │  └──────────────────┘         │ Port: 5432                   │   │   │
│  │                               │                              │   │   │
│  │                               │ Tables:                      │   │   │
│  │                               │ - hazardous_substances       │   │   │
│  │                               │ - analysis_reports           │   │   │
│  │                               │ - identified_substances      │   │   │
│  │                               └──────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                 │                                        │
│  ┌──────────────────────────────▼───────────────────────────────────┐   │
│  │                     External APIs                                  │   │
│  │  ┌──────────────────┐   (Phase 2)                                 │   │
│  │  │ OpenAI API       │   PubChem / NIOSH / SDS                     │   │
│  │  │ (GPT-4o)         │                                              │   │
│  │  │                  │                                              │   │
│  │  │ 用于:            │                                              │   │
│  │  │ - 化学物质识别   │                                              │   │
│  │  │ - 风险评估       │                                              │   │
│  │  │ - 报告生成       │                                              │   │
│  │  └──────────────────┘                                              │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 数据流

```
用户上传文件 → File Parser（提取纯文本）
                    ↓
            Chemical Extractor（OpenAI API 识别物质 + 分类）
                    ↓
            Risk Matcher（本地DB匹配 + AI补充）
                    ↓
            Report Generator（组装结构化报告）
                    ↓
            返回 JSON → Frontend 渲染报告页面
```

---

## 2. 数据库设计

### 表结构

#### 2.1 `hazardous_substances` — 风险物质数据库

```sql
CREATE TABLE hazardous_substances (
    id              SERIAL PRIMARY KEY,
    chemical_name   VARCHAR(500) NOT NULL,          -- 物质名称
    cas_number      VARCHAR(50),                     -- CAS号
    category        VARCHAR(100) NOT NULL,            -- 类别: 化学试剂/生物试剂/染料/固定液/有机溶剂/抗生素/放射性物质/麻醉剂
    
    -- 风险等级 (Safe, Low Risk, Moderate Risk, High Risk, Unknown)
    pregnancy_risk  VARCHAR(20) NOT NULL DEFAULT 'Unknown',
    fertility_risk  VARCHAR(20) NOT NULL DEFAULT 'Unknown',
    lactation_risk  VARCHAR(20) NOT NULL DEFAULT 'Unknown',
    
    -- GHS 分类
    ghs_classification TEXT,
    
    -- 危害声明
    hazard_statements  TEXT,
    
    -- 暴露途径 (JSON array)
    exposure_routes    JSONB DEFAULT '["吸入","皮肤接触"]',
    
    -- 影响描述
    effects_on_fetus          TEXT,   -- 对胎儿影响
    effects_on_reproduction   TEXT,   -- 对生殖系统影响
    effects_on_breastfeeding  TEXT,   -- 对母乳喂养影响
    
    -- 建议防护措施
    recommended_ppe           TEXT,   -- 推荐个人防护装备
    recommended_precautions   TEXT,   -- 建议预防措施
    
    -- 参考来源
    references       TEXT,
    
    -- 时间戳
    created_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_substances_name ON hazardous_substances(chemical_name);
CREATE INDEX idx_substances_cas ON hazardous_substances(cas_number);
CREATE INDEX idx_substances_category ON hazardous_substances(category);
```

#### 2.2 `analysis_reports` — 分析报告记录

```sql
CREATE TABLE analysis_reports (
    id                SERIAL PRIMARY KEY,
    original_filename VARCHAR(500) NOT NULL,
    file_type         VARCHAR(10) NOT NULL,          -- pdf / docx / txt
    file_size         INTEGER,                        -- 文件大小(bytes)
    extracted_text    TEXT,                           -- 解析后的纯文本
    overall_risk      VARCHAR(20),                    -- Low / Medium / High
    overall_score     INTEGER,                        -- 0-100 风险评分
    report_json       JSONB,                          -- 完整结构化报告
    status            VARCHAR(20) DEFAULT 'pending',   -- pending / processing / completed / failed
    error_message     TEXT,
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW()
);
```

#### 2.3 `identified_substances` — 分析中识别出的物质

```sql
CREATE TABLE identified_substances (
    id              SERIAL PRIMARY KEY,
    report_id       INTEGER REFERENCES analysis_reports(id) ON DELETE CASCADE,
    substance_id    INTEGER REFERENCES hazardous_substances(id) ON DELETE SET NULL,
    
    substance_name  VARCHAR(500) NOT NULL,
    category        VARCHAR(100),
    
    -- 分人群风险等级
    pregnancy_risk  VARCHAR(20),
    fertility_risk  VARCHAR(20),
    lactation_risk  VARCHAR(20),
    
    -- 风险原因
    risk_reason     TEXT,
    
    -- 影响
    effects_on_fetus          TEXT,
    effects_on_reproduction   TEXT,
    effects_on_breastfeeding  TEXT,
    
    -- 暴露途径
    exposure_routes JSONB,
    
    -- 建议防护
    recommended_ppe         TEXT,
    recommended_precautions TEXT,
    
    -- 在原文中发现的位置
    found_in_section TEXT,
    
    -- 是否来自本地数据库
    from_database    BOOLEAN DEFAULT FALSE,
    
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_identified_report ON identified_substances(report_id);
```

### ER 关系图

```
┌──────────────────────┐        ┌──────────────────────────┐
│  analysis_reports    │        │  identified_substances   │
├──────────────────────┤        ├──────────────────────────┤
│ id (PK)              │◄───────│ report_id (FK)           │
│ original_filename    │        │ id (PK)                  │
│ file_type            │        │ substance_id (FK) ───────┐
│ extracted_text       │        │ substance_name           │
│ overall_risk         │        │ category                 │
│ report_json          │        │ pregnancy_risk           │
│ status               │        │ fertility_risk           │
│ created_at           │        │ lactation_risk           │
└──────────────────────┘        │ risk_reason              │
                                │ recommended_precautions  │
                                └──────────────────────────┘
                                           │
                                           │ FK (nullable)
                                           ▼
                                ┌──────────────────────────┐
                                │  hazardous_substances    │
                                ├──────────────────────────┤
                                │ id (PK)                  │
                                │ chemical_name            │
                                │ cas_number               │
                                │ category                 │
                                │ pregnancy_risk           │
                                │ fertility_risk           │
                                │ lactation_risk           │
                                │ ghs_classification       │
                                │ hazard_statements        │
                                │ exposure_routes (JSONB)  │
                                │ effects_on_fetus         │
                                │ effects_on_reproduction  │
                                │ effects_on_breastfeeding │
                                │ recommended_ppe          │
                                │ references               │
                                └──────────────────────────┘
```

---

## 3. API 设计

### Base URL: `http://localhost:8000/api/v1`

### 3.1 文件上传

```
POST /api/v1/upload

Request:
  Content-Type: multipart/form-data
  Body: file (PDF/DOCX/TXT, max 50MB)

Response 201:
{
  "id": 1,
  "original_filename": "protocol_v2.pdf",
  "file_type": "pdf",
  "file_size": 245000,
  "extracted_text": "Materials: ...",
  "status": "pending",
  "created_at": "2026-06-08T12:00:00Z"
}
```

### 3.2 触发分析

```
POST /api/v1/analyze/{report_id}

Response 200:
{
  "id": 1,
  "status": "processing"
}

--- 轮询获取结果 ---

GET /api/v1/analyze/{report_id}/status

Response 200 (处理中):
{
  "status": "processing",
  "progress": "Extracting chemicals..."
}

Response 200 (完成):
{
  "status": "completed"
}
```

### 3.3 获取报告

```
GET /api/v1/report/{report_id}

Response 200:
{
  "id": 1,
  "original_filename": "protocol_v2.pdf",
  "overall_risk": "Medium",
  "overall_score": 55,

  "executive_summary": {
    "total_substances_found": 12,
    "high_risk_count": 2,
    "moderate_risk_count": 5,
    "low_risk_count": 3,
    "safe_count": 2,
    "summary_text": "该protocol包含多个中等风险物质..."
  },

  "identified_hazardous_materials": [
    {
      "id": 1,
      "substance_name": "Formaldehyde",
      "category": "固定液",
      "pregnancy_risk": "High Risk",
      "fertility_risk": "High Risk",
      "lactation_risk": "Moderate Risk",
      "risk_reason": "已知致畸物，可通过皮肤吸收",
      "effects_on_fetus": "可能导致发育异常",
      "effects_on_reproduction": "影响生育能力",
      "effects_on_breastfeeding": "可能通过乳汁传递",
      "exposure_routes": ["吸入", "皮肤接触"],
      "recommended_ppe": "化学通风橱 + 双层手套 + 防护服",
      "recommended_precautions": "必须在通风橱中操作，考虑替代品",
      "found_in_section": "Fixation step: 4% PFA..."
    }
  ],

  "high_risk_items": [
    {
      "substance_name": "Formaldehyde",
      "category": "固定液",
      "pregnancy_risk": "High Risk",
      "recommended_precautions": "✓ Chemical hood\n✓ Double gloves\n✓ Respirator\n✓ Consider substitution"
    }
  ],

  "recommended_precautions": [
    {
      "substance_name": "Formaldehyde",
      "risk": "High Risk",
      "precautions": [
        "Chemical hood",
        "Double gloves",
        "Respirator",
        "Consider substitution"
      ]
    }
  ],

  "risk_by_category": {
    "妊娠期": { "high": 2, "moderate": 4, "low": 6 },
    "备孕期": { "high": 1, "moderate": 3, "low": 8 },
    "哺乳期": { "high": 1, "moderate": 5, "low": 6 }
  },

  "disclaimer": "本报告仅供实验室安全参考，不能替代职业健康专家建议。使用前请咨询您的医生或职业健康顾问。",

  "created_at": "2026-06-08T12:05:00Z"
}
```

### 3.4 查询风险数据库

```
GET /api/v1/substances?search=formaldehyde&category=固定液&risk=High Risk

Response 200:
{
  "total": 1,
  "items": [
    {
      "id": 1,
      "chemical_name": "Formaldehyde",
      "cas_number": "50-00-0",
      "category": "固定液",
      "pregnancy_risk": "High Risk",
      "fertility_risk": "High Risk",
      "lactation_risk": "Moderate Risk"
    }
  ]
}
```

---

## 4. 页面设计

### 4.1 首页 — 上传页面 `/`

```
┌──────────────────────────────────────────────────────────────┐
│                    🧬 LabSafe Mom                              │
│         Laboratory Safety for Expecting Researchers           │
│                                                               │
│   为孕期、备孕、哺乳期科研人员提供实验安全风险评估               │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │                                                      │     │
│  │                  📁 拖拽文件到此处                     │     │
│  │                    或 点击上传                        │     │
│  │                                                      │     │
│  │              支持格式: PDF · DOCX · TXT               │     │
│  │              最大文件: 50MB                           │     │
│  │                                                      │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  📋 支持分析:                                         │     │
│  │  · 化学试剂  · 生物试剂  · 染料  · 固定液             │     │
│  │  · 有机溶剂  · 抗生素   · 放射性物质  · 麻醉剂        │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  👩‍🔬 风险评估维度:                                     │     │
│  │  🟢 孕期    🟡 备孕期    🔵 哺乳期                     │     │
│  └─────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 分析中 — 加载状态 `/analysis/[id]`

```
┌──────────────────────────────────────────────────────────────┐
│                    🔄 Analyzing Protocol...                    │
│                                                               │
│              [████████████░░░░░░░░] 65%                        │
│                                                               │
│          当前: 识别化学物质...                                  │
│                                                               │
│          📄 protocol_v2.pdf                                    │
│          ⏱ 预计剩余: 15秒                                      │
└──────────────────────────────────────────────────────────────┘
```

### 4.3 报告页面 `/report/[id]`

```
┌──────────────────────────────────────────────────────────────┐
│  🧬 LabSafe Mom  │  风险评估报告                                │
│───────────────────────────────────────────────────────────────│
│                                                               │
│  📊 Executive Summary                                         │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  总体风险评分: 55/100  │  风险等级: Medium            │     │
│  │                                                      │     │
│  │  发现物质: 12  │  High: 2  Moderate: 5  Low: 3       │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
│  ⚠️ Identified Hazardous Materials                            │
│  ┌─────────────────────────────────────────────────────┐     │
│  │ Material      │ Category │ 孕期  │ 备孕  │ 哺乳    │     │
│  │───────────────│──────────│───────│───────│─────────│     │
│  │ Formaldehyde  │ 固定液   │ 🔴    │ 🔴    │ 🟡      │     │
│  │ DAPI          │ 染料     │ 🟡    │ 🟢    │ 🟢      │     │
│  │ Ethidium Br.  │ 染料     │ 🔴    │ 🟡    │ 🟡      │     │
│  │ TEMED         │ 化学试剂 │ 🟡    │ 🟡    │ 🟡      │     │
│  │ ...           │ ...      │ ...   │ ...   │ ...     │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
│  🚨 High-Risk Items                                           │
│  ┌─────────────────────────────────────────────────────┐     │
│  │ ⚠ Formaldehyde — High Risk                           │     │
│  │   ✓ Chemical hood    ✓ Double gloves                  │     │
│  │   ✓ Respirator       ✓ Consider substitution          │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                               │
│  🛡️ Recommended Precautions                                   │
│  [按物质列出详细防护建议...]                                     │
│                                                               │
│  📋 Disclaimer                                                │
│  本报告仅供实验室安全参考，不能替代职业健康专家建议。             │
│                                                               │
│  [🖨 打印报告]  [📥 下载PDF]                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. 文件夹结构

```
E:\bme\iGEM\软件\LabSafeMom\
│
├── frontend/                          # Next.js 前端
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx             # 全局布局
│   │   │   ├── page.tsx               # 首页 — 文件上传
│   │   │   ├── globals.css            # 全局样式 + Tailwind
│   │   │   ├── analysis/
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx       # 分析进度页
│   │   │   └── report/
│   │   │       └── [id]/
│   │   │           └── page.tsx       # 报告查看页
│   │   ├── components/
│   │   │   ├── FileUpload.tsx         # 拖拽上传组件
│   │   │   ├── ExecutiveSummary.tsx   # 摘要组件
│   │   │   ├── HazardTable.tsx        # 物质表格组件
│   │   │   ├── HighRiskItems.tsx      # 高风险项目组件
│   │   │   ├── Precautions.tsx        # 防护建议组件
│   │   │   ├── Disclaimer.tsx         # 免责声明组件
│   │   │   ├── RiskBadge.tsx          # 风险徽章组件
│   │   │   ├── LoadingSpinner.tsx     # 加载动画
│   │   │   └── Navbar.tsx             # 导航栏
│   │   ├── lib/
│   │   │   ├── api.ts                 # API 调用封装
│   │   │   └── types.ts               # TypeScript 类型定义
│   │   └── hooks/
│   │       └── useAnalysis.ts         # 分析状态 hook
│   ├── public/
│   │   └── logo.svg
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   └── next.config.js
│
├── backend/                           # Python FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI 入口
│   │   ├── config.py                  # 配置 (DB URL, OpenAI key等)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       ├── upload.py          # 文件上传路由
│   │   │       ├── analyze.py         # 分析路由
│   │   │       └── report.py          # 报告路由
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── file_parser.py         # PDF/DOCX/TXT 解析
│   │   │   ├── chemical_extractor.py  # OpenAI 化学物质提取
│   │   │   ├── risk_matcher.py        # 风险数据库匹配
│   │   │   └── report_generator.py    # 报告生成
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── substance.py           # HazardousSubstance ORM
│   │   │   └── report.py              # AnalysisReport + IdentifiedSubstance ORM
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py              # 上传请求/响应 schema
│   │   │   ├── analysis.py            # 分析请求/响应 schema
│   │   │   └── report.py              # 报告响应 schema
│   │   └── db/
│   │       ├── __init__.py
│   │       ├── database.py            # DB 连接 + session
│   │       └── seed_data.py           # 预置风险数据 (100+常见实验室危险物质)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic.ini
│
├── docker-compose.yml                 # PostgreSQL + Backend + Frontend
├── .env.example                       # 环境变量模板
└── README.md
```

---

## 6. MVP 开发路线图

### Week 1: 基础架构搭建 (Day 1-3)

| 任务 | 说明 |
|------|------|
| 初始化 Next.js 项目 | 配置 TypeScript, Tailwind, App Router |
| 初始化 FastAPI 项目 | 项目结构, 依赖安装 |
| Docker Compose | PostgreSQL 容器配置 |
| 数据库模型 | SQLAlchemy 模型 + Alembic 迁移 |
| 种子数据 | 预置 ~50 种常见实验室危险物质数据 |
| 基础 API 框架 | FastAPI router 结构搭建 |

### Week 1: 核心功能 (Day 4-7)

| 任务 | 说明 |
|------|------|
| 文件解析服务 | PDF (PyMuPDF), DOCX (python-docx), TXT 解析 |
| OpenAI 集成 | Chemical Extractor — 用 GPT-4o 从文本中提取化学物质 |
| 风险匹配 | 本地DB精确匹配 + AI模糊匹配 |
| 报告生成 | 组装结构化 JSON 报告 |
| 上传 API | POST /upload 完整流程 |
| 分析 API | POST /analyze + GET status |
| 报告 API | GET /report/{id} |

### Week 2: 前端 (Day 8-12)

| 任务 | 说明 |
|------|------|
| 首页 UI | 上传页面 + 拖拽上传组件 |
| 分析进度 UI | 轮询状态 + 进度动画 |
| 报告页面 UI | Executive Summary + 表格 + 高风险 + 防护建议 |
| API 对接 | 前后端联调 |
| 响应式适配 | 移动端 + 打印样式 |

### Week 2: 打磨 (Day 13-14)

| 任务 | 说明 |
|------|------|
| 错误处理 | 文件格式校验、大小限制、异常提示 |
| 种子数据扩充 | 扩展到 100+ 物质 |
| 测试 | 基本功能测试 |
| README | 使用文档 |

---

## 7. 数据来源方案

### Phase 1 — MVP 内置数据库

预置 **100+ 常见实验室危险物质**，数据来源于：

| 来源 | 说明 |
|------|------|
| OSHA Laboratory Safety Guidance | 职业安全标准 |
| NIOSH Pocket Guide | 化学危害信息 |
| GHS Classification | 全球化学品统一分类 |
| CDC Reproductive Health | 生殖健康指南 |
| PubChem | 化合物信息 |
| EMBL-EBI ChEMBL | 生物活性分子数据库 |
| 公开 SDS 数据 | 安全数据表 |
| 学术文献 | 生殖毒性研究 |

**预置数据示例 (50+ 种关键物质):**

- 固定液: Formaldehyde, Paraformaldehyde, Glutaraldehyde, Osmium Tetroxide
- 有机溶剂: Methanol, Ethanol, Acetone, Xylene, Toluene, Chloroform, DMSO, DMF, Acetonitrile, Hexane
- 染料: DAPI, Ethidium Bromide, SYBR Safe, Hoechst 33342, Propidium Iodide, Coomassie Blue
- 抗生素: Puromycin, G418 (Geneticin), Hygromycin B, Blasticidin, Penicillin-Streptomycin
- 化学试剂: TEMED, β-Mercaptoethanol, DTT, PMSF, DEPC, SDS, Acrylamide, Bis-acrylamide
- 放射性物质: ³²P, ³⁵S, ³H, ¹²⁵I
- 麻醉剂: Isoflurane, Ketamine, Xylazine, Pentobarbital, Tribromoethanol (Avertin)
- 生物试剂: 慢病毒, 腺病毒, AAV, 细菌毒素

### Phase 2 — RAG + 外部API (后续迭代)

- PubMed / PubChem API 实时查询
- NIOSH Pocket Guide 在线查询
- SDS 自动检索
- RAG 增强 — 使用向量数据库存储研究文献
- 用户反馈系统 — 持续改进数据库准确性

---

## 8. 技术选型说明

| 层级 | 技术 | 选择原因 |
|------|------|----------|
| 前端框架 | Next.js 14 (App Router) | React SSR, 文件路由, 内置优化 |
| 语言 | TypeScript | 类型安全 |
| 样式 | Tailwind CSS | 快速UI开发, 响应式 |
| 后端框架 | FastAPI | 异步支持, 自动API文档, Pydantic验证 |
| AI | OpenAI GPT-4o | 文本理解 + 结构化输出 |
| 数据库 | PostgreSQL 16 | 成熟的关系型DB, JSONB支持 |
| ORM | SQLAlchemy 2.0 | Python最成熟的ORM |
| 文件解析 | PyMuPDF / python-docx | 可靠的PDF和DOCX解析 |
| 容器化 | Docker Compose | 一键启动所有服务 |

---

## ⏭ 下一步

确认以上设计后，我将按以下顺序生成代码：

1. **Docker + 项目初始化** (docker-compose.yml, 项目结构)
2. **后端** (FastAPI + 数据库模型 + 种子数据)
3. **前端** (页面 + 组件)
4. **联调 + 启动说明**

请审阅设计，有任何修改意见请告诉我！

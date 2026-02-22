# API Test Agent 设计文档

> 给定接口文档，自动生成测试用例文档 + pytest + requests 自动化代码。

## 1. 概述

### 1.1 目标

构建一个 CLI 工具，输入 API 文档，输出：
1. 结构化的测试用例文档（Markdown）
2. 可直接运行的 pytest + requests 自动化测试代码

### 1.2 核心原则

- **流水线架构** — 解析 → 生成用例 → 生成代码，每步可独立运行
- **不引入 agent 框架** — 流程固定，不需要 LLM 自主决策循环
- **测试知识驱动** — 用 skills（可插拔知识模块）指导 LLM 生成高质量用例
- **多模型支持** — 通过 litellm 统一调用 Claude/GPT/Gemini 等

### 1.3 技术栈

| 依赖 | 用途 |
|------|------|
| litellm | 多模型统一 API 调用 |
| click | CLI 框架 |
| pydantic | 数据结构定义与校验 |
| pyyaml | OpenAPI YAML 解析 |

---

## 2. 架构设计

### 2.1 数据流

```
输入文档 → [Parser] → ApiEndpoint (统一结构)
                            ↓
ApiEndpoint → [TestCase Generator + Skills] → 测试用例文档 (Markdown)
                            ↓                         ↓
                    (--arch layered)            (--arch flat，默认)
                            ↓                         ↓
              [LayeredCodeGenerator]          [CodeGenerator]
              testcases + endpoints           testcases only
                            ↓                         ↓
              五层架构项目目录                 平铺 pytest 文件
```

### 2.2 模块职责

```
api-test-agent/
├── pyproject.toml
├── README.md
├── src/
│   └── api_test_agent/
│       ├── __init__.py
│       ├── cli.py              # CLI 入口，命令定义
│       ├── parser/             # 文档解析器
│       │   ├── base.py         # ApiEndpoint 等模型定义
│       │   ├── swagger.py      # OpenAPI/Swagger 解析
│       │   ├── postman.py      # Postman Collection 解析
│       │   └── markdown.py     # Markdown 文档 → LLM 提取
│       ├── generator/          # 生成器
│       │   ├── testcase.py     # 测试用例生成（LLM）
│       │   ├── code.py         # 代码生成 - 平铺模式（LLM）
│       │   └── layered.py     # 代码生成 - 分层架构模式（LLM + 模板）
│       ├── skills/             # 可插拔测试知识模块
│       │   ├── loader.py       # skill 加载与选择逻辑
│       │   ├── base.md         # 基础测试规则（始终加载）
│       │   ├── param-validation.md   # 参数验证策略
│       │   ├── auth-testing.md       # 鉴权与权限测试
│       │   ├── pagination.md         # 分页接口专用
│       │   ├── file-upload.md        # 文件上传接口专用
│       │   ├── idempotency.md        # 幂等性测试
│       │   └── business-flow.md      # 业务链路测试
│       ├── prompts/            # prompt 模板
│       │   ├── testcase.md     # 用例生成 prompt 模板
│       │   ├── code.md         # 代码生成 prompt 模板（平铺模式）
│       │   ├── layered_api.md  # 分层 - 接口封装层 prompt
│       │   ├── layered_data.md # 分层 - 数据层 YAML prompt
│       │   ├── layered_services.md  # 分层 - 业务编排层 prompt
│       │   └── layered_tests.md     # 分层 - 用例层 prompt
│       └── llm.py              # litellm 封装（模型调用、重试、错误处理）
├── tests/                      # 项目自身的测试
└── docs/
    ├── design.md               # 本设计文档
    ├── architecture.md         # 架构详解
    ├── development.md          # 开发指南
    └── skills-guide.md         # 如何编写新 skill
```

---

## 3. 模块详细设计

### 3.1 文档解析器（Parser）

#### 统一数据模型

```python
class Param(BaseModel):
    name: str
    location: str          # query / path / header / cookie
    required: bool
    param_type: str        # string / integer / boolean / array / object
    description: str = ""
    constraints: dict = {} # min, max, pattern, enum 等

class ApiEndpoint(BaseModel):
    method: str              # GET / POST / PUT / DELETE / PATCH
    path: str                # /api/users/{id}
    summary: str             # 接口描述
    parameters: list[Param]  # 请求参数
    request_body: dict | None  # 请求体 JSON Schema
    responses: dict          # {200: {schema, description}, 400: ...}
    auth_required: bool      # 是否需要鉴权
    tags: list[str]          # 分组标签
    content_type: str = "application/json"
```

#### 解析策略

| 输入格式 | 检测方式 | 解析方式 |
|----------|---------|---------|
| OpenAPI 3.x / Swagger 2.0 | 文件包含 `openapi` 或 `swagger` 字段 | 代码直接解析 YAML/JSON |
| Postman Collection v2.1 | 文件包含 `info._postman_id` 字段 | 代码直接解析 JSON |
| Markdown / 文本 | 以上都不匹配 | 交给 LLM 提取为 ApiEndpoint 结构 |

格式自动检测（`--format auto`），也支持手动指定。

### 3.2 Skills 体系

#### 设计理念

Skills 是可插拔的测试知识模块，每个 skill 是一个 Markdown 文件，包含：
- 适用场景描述（用于自动匹配）
- 测试策略和用例设计指导
- 示例用例

#### 自动加载逻辑

```python
# loader.py 伪代码
def select_skills(endpoint: ApiEndpoint, depth: str) -> list[str]:
    skills = ["base.md"]  # 始终加载

    if depth == "full":
        skills.append("auth-testing.md")
        skills.append("idempotency.md")

    # 根据接口特征自动匹配
    if has_pagination_params(endpoint):
        skills.append("pagination.md")

    if endpoint.content_type == "multipart/form-data":
        skills.append("file-upload.md")

    if endpoint.parameters:
        skills.append("param-validation.md")

    return skills
```

#### 扩展方式

添加新 skill 只需：
1. 在 `skills/` 目录创建 `.md` 文件
2. 在 `loader.py` 添加匹配规则
3. 详见 `docs/skills-guide.md`

### 3.3 测试用例生成器（TestCase Generator）

#### Prompt 组装

```
system = base.md + 自动选中的 skills + testcase.md（输出格式要求）
user   = ApiEndpoint JSON + 深度级别
```

#### 深度级别

**quick（默认）：**
- 正常请求（必填参数都传，期望成功）
- 必填参数缺失（期望 400）
- 参数类型错误（期望 400）
- 关键边界值（空值、超长）
- 未授权访问（期望 401）

**full：**
- quick 的全部内容
- 完整边界值 + 特殊字符 + SQL 注入 / XSS
- 状态码全量验证
- 响应体结构和数据正确性验证
- 鉴权与权限（水平/垂直越权）
- 幂等性测试
- 性能基础验证（响应时间）

#### 输出格式

每个接口一个章节，Markdown 表格：

```markdown
## POST /api/users

| 编号 | 场景 | 输入 | 预期状态码 | 预期响应 | 优先级 |
|------|------|------|-----------|---------|--------|
| TC-001 | 正常创建用户 | {"name":"test","email":"a@b.com"} | 201 | 返回用户ID | P0 |
| TC-002 | 缺少必填字段 name | {"email":"a@b.com"} | 400 | 错误提示包含 name | P0 |
```

### 3.4 代码生成器（Code Generator）

支持两种架构模式，通过 `--arch` 参数切换。

#### 3.4.1 平铺模式（flat，默认）

```
output/
├── conftest.py            # 公共 fixtures
├── test_create_user.py    # POST /api/users
├── test_get_user.py       # GET /api/users/{id}
└── test_delete_user.py    # DELETE /api/users/{id}
```

#### conftest.py 提供的公共能力

```python
import pytest
import requests
import os

@pytest.fixture
def base_url():
    return os.getenv("API_BASE_URL", "http://localhost:8080")

@pytest.fixture
def session():
    s = requests.Session()
    yield s
    s.close()

@pytest.fixture
def auth_headers():
    token = os.getenv("API_TOKEN")
    return {"Authorization": f"Bearer {token}"}
```

#### 测试文件规范

```python
class TestCreateUser:
    """POST /api/users"""

    def test_create_user_success(self, base_url, auth_headers):
        """TC-001: 正常创建用户"""
        resp = requests.post(
            f"{base_url}/api/users",
            json={"name": "test", "email": "a@b.com"},
            headers=auth_headers
        )
        assert resp.status_code == 201
        assert "id" in resp.json()

    def test_missing_required_field(self, base_url, auth_headers):
        """TC-002: 缺少必填字段 name"""
        resp = requests.post(
            f"{base_url}/api/users",
            json={"email": "a@b.com"},
            headers=auth_headers
        )
        assert resp.status_code == 400
```

代码规范：
- 用例编号写在 docstring，方便与用例文档溯源
- 环境配置全部走环境变量，不硬编码
- 每条用例独立，不依赖执行顺序
- 一个接口一个文件，一个用例一个方法

#### 3.4.2 分层架构模式（layered）

按接口自动化标准分层组织，接口按 tag 分组：

```
output/
├── base/                    # 基础层
│   ├── config.py            # 环境配置（BASE_URL, TOKEN）
│   └── client.py            # HttpClient 轻量封装（requests.Session）
├── data/                    # 数据层（YAML，数据代码分离）
│   └── users.yaml           # 按 tag 一个文件
├── api/                     # 接口封装层
│   └── users_api.py         # 每个 tag 一个类，每个接口一个方法
├── services/                # 业务编排层
│   └── user_flow.py         # LLM 根据 CRUD 语义自动推断业务流程
├── tests/                   # 用例与执行层
│   ├── conftest.py          # fixtures（client + 各 tag 的 api 实例）
│   └── test_users.py        # 测试用例，调用 api 层，数据从 YAML 加载
└── requirements.txt         # 依赖
```

**生成策略：**

| 层 | 生成方式 | LLM 调用 |
|----|---------|---------|
| base/ | 代码模板 | 无 |
| api/ | LLM，按 tag 分组 | 每 tag 1 次 |
| data/ | LLM，基于测试用例 | 每 tag 1 次 |
| services/ | LLM，推断 CRUD 流程 | 每 tag 1 次 |
| tests/ | LLM，引用 api + data | 每 tag 1 次 |
| conftest, requirements | 代码模板 | 无 |

`LayeredCodeGenerator` 需要 `testcases_md` + `endpoints` 两个输入（endpoints 用于按 tag 分组和读取接口签名）。

---

## 4. CLI 设计

### 4.1 命令

```bash
# 全流程：文档 → 用例 → 代码
api-test-agent run api-doc.yaml -o output/

# 只生成测试用例文档
api-test-agent gen-cases api-doc.yaml -o testcases.md

# 从已有用例文档生成代码
api-test-agent gen-code testcases.md -o output/
```

### 4.2 选项

```bash
--depth quick|full                    # 测试深度，默认 quick
--model claude-sonnet                 # 指定模型
--format swagger|postman|markdown|auto  # 文档格式，默认 auto
--filter "POST /api/*"               # 只处理匹配的接口
--append                             # 增量模式
--arch flat|layered                  # 代码架构风格，默认 flat
--doc <file>                         # API 文档路径（gen-code --arch layered 时必填）
```

### 4.3 配置文件

`~/.api-test-agent/config.yaml`：

```yaml
default_model: claude-sonnet-4-20250514
api_keys:
  anthropic: ${ANTHROPIC_API_KEY}
  openai: ${OPENAI_API_KEY}
default_depth: quick
```

---

## 5. 文档交付物

| 文档 | 内容 | 目的 |
|------|------|------|
| README.md | 快速上手、安装、基本用法 | 新用户 5 分钟跑起来 |
| docs/design.md | 本文档 | 理解系统为什么这样设计 |
| docs/architecture.md | 架构图、模块职责、数据流 | 理解系统怎么工作 |
| docs/development.md | 环境搭建、开发流程、如何调试 | 开发者如何参与开发 |
| docs/skills-guide.md | skill 格式、编写规范、示例 | 如何扩展测试知识 |

代码级文档：
- 每个模块有 docstring（职责、输入输出）
- 关键函数有类型注解
- pyproject.toml 完整（依赖、入口、版本）

---

## 6. 未来扩展（不在 v1 范围）

- Web UI 界面
- 自动运行生成的测试并分析失败原因（需要 agent 循环）
- 多接口业务链路测试自动编排
- 测试报告生成（HTML/PDF）
- CI/CD 集成模板

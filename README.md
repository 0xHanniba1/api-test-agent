# API Test Agent

API 文档 → 测试用例 → pytest+requests 自动化代码，一键生成。

## 安装

```bash
git clone <repo-url>
cd api-test-agent
uv sync
```

## 快速上手

### 全流程（推荐）

```bash
# 从 Swagger/OpenAPI 文档生成测试用例 + 代码（平铺模式）
api-test-agent run api-doc.yaml -o output/

# 生成分层架构代码（base/data/api/services/tests 五层）
api-test-agent run api-doc.yaml -o output/ --arch layered
```

### 分步执行

```bash
# 第一步：生成测试用例文档
api-test-agent gen-cases api-doc.yaml -o testcases.md

# 第二步：从测试用例生成代码（平铺模式）
api-test-agent gen-code testcases.md -o output/

# 第二步（分层模式）：需要通过 --doc 指定原始 API 文档
api-test-agent gen-code testcases.md -o output/ --arch layered --doc api-doc.yaml
```

### 运行生成的测试

```bash
cd output/
API_BASE_URL=http://localhost:8080 API_TOKEN=your-token pytest -v
```

## 支持的输入格式

| 格式 | 说明 |
|------|------|
| Swagger / OpenAPI 3.x | YAML 或 JSON，自动检测 |
| Postman Collection v2.1 | JSON 导出文件 |
| Markdown / 文本 | 任意格式的接口文档（通过 LLM 解析） |

## 命令选项

```bash
api-test-agent run <doc> -o <dir> [OPTIONS]
api-test-agent gen-cases <doc> -o <file> [OPTIONS]
api-test-agent gen-code <cases> -o <dir> [OPTIONS]

Options:
  --depth quick|full    测试深度（默认 quick）
  --model <name>        LLM 模型（默认 claude-sonnet）
  --format auto|swagger|postman|markdown  文档格式（默认 auto）
  --filter <pattern>    按接口过滤，支持多次使用（见下方说明）
  --append              增量模式：追加用例 / 跳过已有代码文件
  --arch flat|layered   代码架构风格（默认 flat，见下方说明）
  --doc <file>          API 文档路径（gen-code 使用 --arch layered 时必填）
```

### 增量生成

新增接口时无需重新生成全量，使用 `--filter` 和 `--append` 组合：

```bash
# 只生成 POST /pets 相关的测试，追加到已有输出
api-test-agent run api-doc.yaml -o output/ --filter "POST /pets" --append

# 生成所有 GET 接口的测试
api-test-agent run api-doc.yaml -o output/ --filter "GET *" --append

# 多个 filter 组合
api-test-agent run api-doc.yaml -o output/ --filter "POST /orders*" --filter "PUT /orders*" --append
```

`--filter` 支持的模式：
- `"POST /pets"` — 匹配指定 method + path
- `"/pets/*"` — 任意 method，路径 glob 匹配
- 支持 `*` 和 `?` 通配符

`--append` 行为：
- `gen-cases` / `run`：将新用例追加到已有 Markdown 文件末尾
- `gen-code` / `run`：跳过已存在的代码文件，只写入新文件

### 分层架构模式

使用 `--arch layered` 生成按接口自动化五层架构组织的代码。

#### 架构总览

```
┌─────────────────────────────────────────────────┐
│                 用例与执行层 (tests/)              │
│  pytest 测试用例，调用下层接口，数据从 YAML 加载     │
├─────────────────────────────────────────────────┤
│                 业务编排层 (services/)             │
│  组合多个接口完成业务流程（创建→查询→更新→删除）      │
├─────────────────────────────────────────────────┤
│                 接口封装层 (api/)                  │
│  每个接口封装为方法，屏蔽 HTTP 细节                  │
├─────────────────────────────────────────────────┤
│                 数据层 (data/)                    │
│  YAML 文件管理测试数据，数据与代码分离               │
├─────────────────────────────────────────────────┤
│                 基础层 (base/)                    │
│  HttpClient 封装、环境配置、公共能力                │
└─────────────────────────────────────────────────┘
```

#### 各层职责

| 层 | 目录 | 职责 | 示例 |
|----|------|------|------|
| **基础层** | `base/` | 统一的 HTTP 客户端封装，环境配置（BASE_URL、TOKEN）通过环境变量注入 | `HttpClient` 封装 `requests.Session`，提供 get/post/put/delete 方法 |
| **数据层** | `data/` | YAML 文件管理测试数据，实现数据与代码分离，便于维护和批量修改 | `users.yaml` 按操作和场景组织：`create_user.valid`、`create_user.missing_name` |
| **接口封装层** | `api/` | 每个资源一个类，每个接口一个方法，屏蔽路径拼接和参数传递细节 | `UsersApi.create_user(body)` 内部调用 `self.client.post("/api/users", json=body)` |
| **业务编排层** | `services/` | 组合多个接口调用完成端到端业务流程，通过响应数据串联各步骤 | `UserFlow.full_lifecycle()`: 创建 → 查询 → 更新 → 删除 → 验证删除 |
| **用例与执行层** | `tests/` | pytest 测试用例，通过 fixture 获取 api 实例，从 YAML 加载数据，不直接调用 requests | `test_users.py` 中 `users_api.create_user(d["body"])` + `assert resp.status_code == d["expected_status"]` |

#### 调用关系

```
tests/test_users.py
    │
    ├── 读取 data/users.yaml（测试数据）
    │
    ├── 通过 fixture 获取 api/users_api.py（接口封装）
    │        │
    │        └── 调用 base/client.py（HTTP 客户端）
    │                │
    │                └── 读取 base/config.py（环境配置）
    │
    └── 可选：调用 services/user_flow.py（业务编排）
             │
             └── 内部调用 api/users_api.py
```

#### 生成的目录结构

```
output/
├── base/              # 基础层
│   ├── config.py      #   环境变量配置（API_BASE_URL, API_TOKEN）
│   └── client.py      #   HttpClient 封装
├── data/              # 数据层
│   └── users.yaml     #   按资源/tag 一个 YAML 文件
├── api/               # 接口封装层
│   └── users_api.py   #   按资源/tag 一个类
├── services/          # 业务编排层
│   └── user_flow.py   #   CRUD 业务流程
├── tests/             # 用例与执行层
│   ├── conftest.py    #   fixtures（client + api 实例）
│   └── test_users.py  #   测试用例
├── Jenkinsfile        # Jenkins Pipeline
└── requirements.txt   # 依赖
```

接口按 API 文档中的 tag 分组，每个 tag 在各层生成对应文件。

#### Jenkins CI 集成

生成的 `Jenkinsfile` 开箱即用，支持：
- **参数化构建**：通过 `ENV` 参数选择 dev/staging/prod 环境
- **Token 安全管理**：通过 Jenkins Credentials 注入 `api-token`
- **JUnit 报告**：自动收集 `reports/*.xml` 展示测试结果

## 配置

设置环境变量：

```bash
export ANTHROPIC_API_KEY=your-key    # 使用 Claude
export OPENAI_API_KEY=your-key       # 使用 GPT
```

## 项目文档

- [设计文档](docs/design.md) — 为什么这样设计
- [开发指南](docs/development.md) — 如何参与开发
- [Skills 编写指南](docs/skills-guide.md) — 如何扩展测试知识

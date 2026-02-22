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

使用 `--arch layered` 生成按接口自动化标准分层组织的代码：

```
output/
├── base/              # 基础层：HttpClient 封装 + 环境配置
│   ├── config.py
│   └── client.py
├── data/              # 数据层：YAML 测试数据（数据代码分离）
│   └── users.yaml
├── api/               # 接口封装层：每个资源一个类
│   └── users_api.py
├── services/          # 业务编排层：CRUD 业务流程组合
│   └── user_flow.py
├── tests/             # 用例与执行层
│   ├── conftest.py
│   └── test_users.py
└── requirements.txt
```

接口按 tag 分组，每个 tag 在各层生成对应文件。测试代码通过 api 层调用接口，从 YAML 文件加载测试数据，不直接使用 requests。

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

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
# 从 Swagger/OpenAPI 文档生成测试用例 + 代码
api-test-agent run api-doc.yaml -o output/
```

### 分步执行

```bash
# 第一步：生成测试用例文档
api-test-agent gen-cases api-doc.yaml -o testcases.md

# 第二步：从测试用例生成代码
api-test-agent gen-code testcases.md -o output/
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
```

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

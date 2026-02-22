# 开发指南

## 环境要求

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) 包管理器

## 环境搭建

```bash
git clone <repo-url>
cd api-test-agent
uv sync           # 安装所有依赖（包括开发依赖）
```

## 运行测试

```bash
uv run pytest -v           # 运行所有测试
uv run pytest tests/test_swagger_parser.py -v   # 运行单个测试文件
```

## 项目结构

```
src/api_test_agent/
├── cli.py              # CLI 入口（Click）
├── llm.py              # LLM 调用封装（litellm）
├── parser/             # 文档解析器
│   ├── base.py         # 数据模型（ApiEndpoint, Param）
│   ├── detect.py       # 格式自动检测
│   ├── swagger.py      # OpenAPI/Swagger 解析
│   ├── postman.py      # Postman Collection 解析
│   └── markdown.py     # Markdown 文档解析（LLM）
├── generator/          # 生成器
│   ├── testcase.py     # 测试用例生成（LLM + Skills）
│   ├── code.py         # pytest 代码生成 - 平铺模式（LLM）
│   └── layered.py     # pytest 代码生成 - 分层架构模式（LLM + 模板）
├── skills/             # 可插拔测试知识模块
│   ├── loader.py       # Skill 选择与加载
│   ├── base.md         # 基础测试规则
│   └── *.md            # 各类测试策略
└── prompts/            # Prompt 模板
    ├── testcase.md     # 用例生成 prompt
    ├── code.md         # 代码生成 prompt（平铺模式）
    ├── layered_api.md  # 分层 - 接口封装层 prompt
    ├── layered_data.md # 分层 - 数据层 prompt
    ├── layered_services.md  # 分层 - 业务编排层 prompt
    └── layered_tests.md     # 分层 - 用例层 prompt
```

## 数据流

```
输入文档 → [Parser] → ApiEndpoint → [TestCaseGenerator + Skills] → Markdown
                                                                       ↓
                                    --arch flat:  [CodeGenerator]     → 平铺 pytest 文件
                                    --arch layered: [LayeredCodeGenerator] → 五层架构项目
```

## 如何添加新的解析器

1. 在 `parser/` 目录创建新文件（如 `har.py`）
2. 实现 `parse_xxx(file_path: Path) -> list[ApiEndpoint]` 函数
3. 在 `detect.py` 添加格式检测逻辑
4. 在 `cli.py` 的 `_parse_doc()` 添加分支
5. 写测试

## 如何添加新的代码架构模式

1. 在 `generator/` 创建新文件（如 `custom.py`）
2. 实现生成器类，`generate()` 方法返回 `dict[str, str]`（文件路径 → 内容）
3. 在 `prompts/` 添加对应的 LLM prompt 模板
4. 在 `cli.py` 的 `--arch` 选项中添加新值，并在 `gen_code` 和 `run` 中接入
5. 写测试

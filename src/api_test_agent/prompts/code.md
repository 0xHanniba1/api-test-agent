# 代码生成要求

请根据测试用例文档生成 pytest + requests 自动化测试代码。

## 规则
- 每个接口生成一个独立的测试文件
- 文件名格式：test_{operation}.py（如 test_create_user.py）
- 使用 class 组织测试，class 名格式：Test{Operation}
- 每个测试方法对应一条用例，docstring 包含用例编号
- 使用 fixtures：base_url, auth_headers（从 conftest.py 获取）
- 环境变量：API_BASE_URL, API_TOKEN
- 不硬编码任何 URL 或凭证
- assert 使用 resp.status_code 和 resp.json()

## conftest.py 模板

import pytest
import requests
import os

@pytest.fixture
def base_url():
    return os.getenv("API_BASE_URL", "http://localhost:8080")

@pytest.fixture
def auth_headers():
    token = os.getenv("API_TOKEN", "")
    return {"Authorization": f"Bearer {token}"} if token else {}

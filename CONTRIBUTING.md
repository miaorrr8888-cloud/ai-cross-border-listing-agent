# Contributing to Jumia AI Listing Agent

感谢你参与贡献！本项目是一个**默认安全（dry-run）**的跨境商品上架助手，请在提交前仔细阅读以下规范。

## 项目结构说明

```
jumia-ai-listing-agent/
├── config/                  # 配置文件（config.example.yaml，不含真实密钥）
├── examples/                # Demo 数据（sample_product.json / full_demo.json / batch_sample.csv）
├── src/
│   ├── main.py              # CLI 入口：demo / validate / health（+ 兼容旧参数）
│   ├── pipeline.py          # 核心流水线编排：采集 → AI → 类目 → 定价 → Payload
│   ├── models/              # Product Schema（统一数据模型）
│   ├── collector/           # 输入层：URL 解析 / JSON / CSV / Excel / 浏览器采集
│   │   └── browser/         # 浏览器采集（Playwright 可选，HtmlDoc 标准库解析）
│   ├── ai/                  # AI 提供商（mock/openai/deepseek/kimi）+ 标题优化 + 翻译
│   ├── jumia/
│   │   ├── api/             # Jumia Seller API 层：auth / payload / http_client / uploader
│   │   │                    #   / upload_guard / health / retry / response_parser
│   │   └── category/        # 类目树 + 两阶段类目匹配 + 属性 Schema
│   ├── pricing/             # 利润定价（逆推公式）
│   ├── validator/           # 上架前检查（listing_check）
│   └── utils/               # 通用工具（配置加载等）
├── tests/                   # 全部测试（199 项，全部不联网）
├── Dockerfile / Makefile    # 生产运行文件
└── SKILL.md                 # 能力全景说明
```

## 开发规范

- **Python 3.12+**，核心逻辑只用标准库（yaml/openpyxl/playwright 均为可选依赖，缺失时优雅降级）。
- 新模块放 `src/<模块名>/`，模块对外接口集中在 `__init__.py` 导出。
- 数据模型统一使用 `dataclasses`，序列化实现 `to_dict()` / `from_dict()`（忽略未知字段）。
- 外部依赖（AI Provider、浏览器、HTTP transport）一律通过**依赖注入**，便于测试 mock、保证测试不联网。
- 无法真实获取数据时**如实返回** `NEEDS_BROWSER` / `unsupported` / `None`，绝不伪造数据。

## 安全规则（红线，违反将被拒绝合并）

**禁止提交以下任何内容：**

- ❌ API key / API token
- ❌ 账号密码、Cookie、Session
- ❌ 私钥文件（`*.pem` / `*.key`）
- ❌ 任何真实账号信息（哪怕是测试账号）

**代码层面的安全要求：**

1. 默认 `dry_run=true`，任何改动不得改变默认值。
2. 默认 `upload.enabled=false`，真实上传必须通过 `UploadGuard` 三重校验。
3. Token 只能从环境变量（`JUMIA_API_KEY` / `JUMIA_API_TOKEN`）或本地配置读取，**绝不硬编码、绝不写入仓库**。
4. 所有测试必须使用 mock transport / mock provider，**禁止在测试中访问真实 API**。
5. 新增配置项必须在 `config/config.example.yaml` 中留空示例值。

提交前自查：

```bash
grep -rn -i -E "(api_key|secret|password|private_key|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]" \
  --include="*.py" --include="*.yaml" --include="*.json" src/ config/ examples/
```

（仅允许测试 fixture 中的明显占位符，如 `"test-key"`。）

## 代码规则

- **新增平台必须使用 Adapter 模式**：实现 `src/collector/base_collector.py` 的 `BaseCollector`（或平台专属 Adapter），并注册到 `PLATFORM_MAP`。禁止在流水线里写平台特判。
- **新增 AI Provider 必须实现 `BaseAIProvider`**，并通过 `get_provider()` 工厂注册。
- **新增功能必须增加测试**：每个新功能至少配套覆盖正常路径 + 失败路径的测试用例。
- 修复 Bug 必须先写一个能复现该 Bug 的测试。

## 测试要求

全部测试通过是合并的最低门槛：

```bash
python -m unittest discover -s tests -p "test_*.py"
```

也可使用 Makefile：

```bash
make test        # 运行全部测试
make validate    # 配置/目录/依赖/安全自检
make demo        # 完整演示流程
```

要求：

- 全部测试**不联网**（AI 用 mock provider，HTTP 用 mock transport，浏览器用 mock HTML）。
- 新增测试文件命名 `tests/test_<模块名>.py`。
- 测试不能依赖执行顺序，不能产生垃圾文件（临时产物放 `tempfile` 或 `setUp` 清理）。

## 提交流程

1. Fork & 创建分支：`git checkout -b feat/your-feature`
2. 提交前运行 `make test && make validate`，确保全绿。
3. PR 描述包含：改动内容、测试结果（`Ran N tests ... OK`）、是否涉及安全相关配置。
4. CI（GitHub Actions）通过后等待 review。

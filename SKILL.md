---
name: Jumia AI Listing Agent
description: >-
  AI 跨境商品生产助手 —— 把任意来源的商品（1688 / 淘宝 / Amazon / 独立站 / 本地表格 …）
  转化为符合 Jumia 上架规范的多语言 Listing，并做上架前质量检查与利润测算。
  默认 dry-run，支持浏览器真实采集（Playwright）、可插拔 AI Provider
  （mock/openai/deepseek/kimi）、Jumia 类目树两阶段匹配与属性自动补全、
  Jumia Seller API Payload 层（认证 + Product/Offer/Inventory + 校验）、
  API 连接健康检查层、真实 HTTP Client 层（请求构建 + 指数退避重试 + 响应解析）、
  单 SKU 真实上传闭环（UploadGuard + JumiaUploader）；批量处理、利润定价；
  统一 CLI（demo / validate / health）+ Docker + Makefile；
  默认禁止上传，不预置任何假 API Token。
version: 1.0.0
tags: [jumia, cross-border, listing, ecommerce, ai, dry-run, browser, playwright, category, pricing, api, payload, health, http-client, retry, upload-guard, uploader, cli, docker]
---

# Jumia AI Listing Agent (v1.0.0 MVP)

## 定位

**AI 跨境商品生产助手**：把任意平台 / 任意来源的商品，经过「采集 → AI 优化 → 多语言生成 →
Jumia Listing 映射 → 类目匹配 → 利润定价 → 上架前检查」，产出一份可直接复核/后续上架的
`product.json`（批量模式逐个 SKU 写入 `output/products/`）。

v1.0.0 为可公开发布的 MVP：零配置跑通 demo、199 项测试全绿、Docker/Makefile 就绪、
统一 CLI；真实上传代码闭环已就绪但**默认双重锁定**（`dry_run=true` + `upload.enabled=false`）。

## 架构

```
输入(URL / JSON / CSV / Excel)
  -> collector（浏览器真实采集 browser/ + 诚实 NEEDS_BROWSER / UNSUPPORTED）
  -> ai.providers（mock / openai / deepseek / kimi 可插拔）
  -> ai（标题优化 / 多语言翻译）
  -> jumia.category（类目树 + 两阶段匹配 + 属性 Schema）
  -> jumia.api（认证 + Payload 构建 + 校验 + HTTP Client + UploadGuard + Uploader）
  -> pricing（利润定价：成本反推建议售价）
  -> validator（上架前检查：类目/属性完整度 + 评分）
  -> output/product.json 或 output/products/<SKU>.json
```

平台适配视角：

```
Product Engine（采集/AI/类目/定价）
        |
Platform Adapter（统一 Payload 规范）
        |
--------------------------------
Jumia(✅) | Noon(规划) | Ozon(规划) | Wildberries(规划)
```

## 能力总览

- **商品采集**：平台识别（通用，不限制 1688）+ Playwright 浏览器真实采集（标题/价格/图片/
  变体/属性）；无法采集时如实返回，绝不伪造数据。
- **AI 优化**：标题清洗与优化、英文标题生成；可插拔 Provider（默认 mock 零网络零 token）。
- **多语言生成**：zh-CN / en / fr / ar 四语。
- **类目匹配**：两阶段（AI 商品理解 → Jumia 类目树映射），输出 category_id + 置信度 + 理由。
- **属性补全**：按类目 required/optional 属性 Schema 检测缺失项并提示。
- **利润计算**：采购价 + 运费 + 佣金率 + 目标毛利率 → 反推建议售价（PricePlan）。
- **Jumia Listing/Payload 生成**：Product / Offer / Inventory 三段 payload + 必填校验。
- **API 上传框架**：认证（env/config）→ HTTP Client（重试/解析）→ Health Check →
  UploadGuard → JumiaUploader（单 SKU 五步上传闭环）；默认禁止上传。

## 使用方式

```bash
# 0) 安装依赖（推荐虚拟环境）
pip install -r requirements.txt

# 1) 完整演示（dry-run，无需任何 token）
python src/main.py demo          # 或 make demo

# 2) 发布前自检：配置 / 目录 / 依赖 / 安全状态
python src/main.py validate      # 或 make validate

# 3) Jumia 健康检查（不上传、不联网）
python src/main.py health        # 或 make health

# 4) 商品 URL / 本地文件（兼容旧参数）
python src/main.py --url https://www.1688.com/offer/xxx.html
python src/main.py --input examples/full_demo.json
python src/main.py --input examples/batch_sample.csv --batch

# 5) 运行测试（199 项，全部不联网）
python -m unittest discover -s tests -p "test_*.py"   # 或 make test

# 6) Docker
docker build -t jumia-agent . && docker run --rm jumia-agent
```

### 配置（config/config.example.yaml 复制为 config.yaml）

```yaml
app:
  dry_run: true           # 默认 dry-run，绝不发起真实上传
http:
  timeout: 30
  retry_count: 3          # 对 429/500/502/503 指数退避重试
  dry_run: true
upload:
  enabled: false          # 上传开关，默认禁止
  max_products: 1         # 第一次真实模式最多 1 个 SKU
ai:
  provider: mock          # mock | openai | deepseek | kimi
  api_key: ""             # 留空；真实 provider 必填，切勿提交假 token
pricing:
  default_commission_rate: 0.15
  default_target_margin: 0.30
  currency: RMB
jumia:
  api_base_url: ""        # 真实接入时填写
  api_key: ""             # 留空；优先用环境变量 JUMIA_API_KEY / JUMIA_API_TOKEN
```

> 真实凭据一律通过环境变量 / 密钥管理器注入，不要硬编码进仓库。

## 模块明细

### 采集层（`src/collector/`）
- **真实输入层**（`base_collector.py` + `url_parser.py`）：`BaseCollector` 抽象 +
  `ParseResult(status, platform, product, message)`；诚实策略：无法抓取返回
  `NEEDS_BROWSER` 且 `product=None`。
- **浏览器采集**（`browser/`）：`BrowserClient` 统一接口（`StaticHtmlClient` 离线 /
  `PlaywrightBrowserClient` 真实）；`extractors/` 标题/价格/图片/变体/属性提取器，
  识别不到返回 `None` 不造假；`browser_collector.py`：URL → Product。
- **表格输入**（`excel_collector.py`）：JSON / CSV / Excel 读取 + 批量生成。

### AI 层（`src/ai/`）
- **Provider 架构**（`providers/`）：统一 `generate_text/translate/optimize_title`；
  `get_provider()` 工厂；OpenAI 兼容协议（openai/deepseek/kimi），无 api_key 一律抛错。
- **标题优化 / 翻译**：`title_optimizer.py` + `translator.py`（四语）。
- **类目匹配**（`category_matcher.py`）：两阶段包装层，`match()` 旧签名兼容 +
  `match_detail()` 完整结构。

### Jumia 层（`src/jumia/`）
- **类目智能**（`category/`）：`category_tree.py` 类目树、`category_matcher.py` 两阶段匹配、
  `attribute_schema.py` 属性 Schema + 缺失检测。
- **API 层**（`api/`）：
  - `auth.py`：`JumiaAuth`（env/config 读 token，缺失抛 `MissingCredential`）
  - `http_client.py`：`JumiaHttpClient`（GET/POST/PUT 统一 `request()`，可注入 transport）
  - `request_builder.py` / `retry.py` / `response_parser.py`：请求构建 / 指数退避 / 响应解析
  - `payload_validator.py` + `product_create.py` / `product_update.py` / `offer.py` / `inventory.py`
  - `health.py`：`JumiaHealthReport` + `check_health()`（不联网）
  - `upload_guard.py`：`UploadGuard`（默认禁止 + 数量上限）
  - `uploader.py`：`JumiaUploader`（校验 → guard → product → offer → inventory 五步）
  - `client.py`：`JumiaClient`（dry-run 预览 / `live_upload()` 真实入口）
  - `errors.py`：认证/权限/限流/类目/上传错误类型 + `map_http_error()`

### 定价与校验（`src/pricing/` + `src/validator/`）
- `recommend_price()`：`售价 = 总成本 / (1 - 佣金率 - 目标毛利率)`。
- `listing_check.py`：标题/描述/图片/属性/类目/多语言/价格 → Listing Score（0–100）。

## 安全规则（本项目红线）

1. 默认 `dry_run=true` + `upload.enabled=false`；CLI 永远 dry-run，不支持真实上传。
2. 真实上传必须同时满足：`dry_run=false` + `upload.enabled=true` + 有效 token +
   Health Check 通过 + UploadGuard 放行；第一次真实模式最多 1 个 SKU，不允许批量。
3. 不填写任何假 API Token（密钥一律留空，由环境变量/密钥管理器注入）；缺失抛 `MissingCredential`。
4. 无法真实抓取/识别时如实返回 `NEEDS_BROWSER` / `unsupported` / `None`，绝不伪造数据。
5. 所有测试不联网（mock transport），不访问真实 Jumia。
6. 架构必须支持未来接入 Jumia API 与任意 LLM Provider；平台适配器可扩展（Noon/Ozon/Wildberries 预留）。

## 开发路线

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| MVP | 统一商品模型 + dry-run 流水线 + 多语言 + 评分 | ✅ |
| P1 | 真实输入层 + 可插拔 AI Provider + 定价 + 批量 | ✅ |
| P2-1 | Playwright 浏览器真实采集层 | ✅ |
| P2-2 | Jumia 类目树两阶段匹配 + 属性 Schema | ✅ |
| P3-1 | Jumia Seller API Payload 层（dry-run） | ✅ |
| P3-2-A | API 连接健康检查层 | ✅ |
| P3-2-B-1 | 真实 HTTP Client 层（构建/重试/解析） | ✅ |
| P3-2-B-2 | 单 SKU 真实上传闭环（Guard + Uploader） | ✅ |
| P4-0 | 发布准备（CLI / Docker / Makefile / 安全扫描 / 文档） | ✅ |
| P4+ | 真实类目 API / 真实上传联调 / 图片合规 / 多平台（Noon/Ozon/WB）/ Web 复核 | 规划中 |

## 真实 Jumia 账号接入清单（发布后）

1. `JUMIA_API_KEY`（或 `JUMIA_API_TOKEN`）环境变量，或 `config.jumia.api_key`。
2. `config.jumia.api_base_url`：Jumia SellerCenter API 真实端点。
3. 认证方式确认：当前为 `Authorization: Bearer <token>`；若 SellerCenter 用 HMAC 签名需调整
   `RequestBuilder._build_headers()`。
4. 端点确认：当前预设 `POST /products`、`POST /offers`、`PUT /inventory`，需与官方文档核对。
5. 启用顺序：先用非上传端点（如 `GET /categories`）验证认证 → 再 `upload.enabled=true`
   测试第一个 SKU。

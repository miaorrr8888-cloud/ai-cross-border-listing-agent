# Jumia AI Listing Agent

> AI 跨境商品生产助手 —— 把任意平台的商品，一键转化为符合 Jumia 上架规范的多语言 Listing。

[![CI](https://github.com/OWNER/jumia-ai-listing-agent/actions/workflows/test.yml/badge.svg)](https://github.com/OWNER/jumia-ai-listing-agent/actions/workflows/test.yml)
[![v1.0.0](https://img.shields.io/badge/version-1.0.0-blue)](RELEASE_NOTES.md)
[![tests](https://img.shields.io/badge/tests-199%20passing-green)](#)
[![dry-run](https://img.shields.io/badge/mode-dry--run-green)](#)
[![upload](https://img.shields.io/badge/upload-disabled-red)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

> CI badge 中的 `OWNER` 请在发布到 GitHub 后替换为实际用户名/组织名。

## 1. 项目介绍

本项目旨在降低跨境卖家在 **Jumia**（非洲领先电商平台）上架商品的成本：你只需要提供一个
商品链接或一份商品 JSON，Agent 就会自动完成「采集 → AI 优化 → 多语言生成 → 类目匹配 →
利润测算 → Jumia Listing/Payload 生成 → 上架前检查」，产出一份结构完整、可直接复核的
`product.json`。

**v1.0.0 MVP 默认 dry-run：不联网上传、不预置任何假 API Token。** 所有 AI 能力与 Jumia
上传能力均通过配置预留接口，接入真实服务即可平滑升级。

### 设计原则

1. 第一版只做 Jumia 单平台闭环，架构预留多平台适配器。
2. 默认 `dry_run=true`、`upload.enabled=false`。
3. 不填写、不伪造任何 API Token。
4. 无法真实采集的数据如实标记（`NEEDS_BROWSER` / `unsupported` / `None`），绝不造假。
5. 输入不限制 1688，设计为通用商品输入（1688 / 淘宝 / Amazon / 独立站 / 表格 …）。

## 2. 核心能力

| 能力 | 说明 | 状态 |
| --- | --- | --- |
| URL 商品采集 | 平台识别 + Playwright 浏览器采集（标题/价格/图片/变体/属性）；无法采集时如实提示 | ✅ |
| AI 标题优化 | 清洗 + 英文标题生成；可插拔 Provider（mock / openai / deepseek / kimi） | ✅ |
| 多语言生成 | zh-CN / en / fr / ar 四语版本 | ✅ |
| 类目匹配 | 两阶段：AI 商品理解 → Jumia 类目树映射（category_id + 置信度） | ✅ |
| 属性补全 | 按类目 required/optional 属性 Schema 检测并提示缺失项 | ✅ |
| 利润计算 | 采购价 + 运费 + 佣金率 + 目标毛利率 → 反推建议售价 | ✅ |
| Jumia Listing 生成 | Product/Offer/Inventory Payload 构建 + 必填校验 | ✅ |
| API 上传框架 | 认证 + HTTP Client（重试/解析）+ Health Check + UploadGuard + 单 SKU 上传闭环 | ✅ 代码就绪，默认禁用 |

## 3. 快速开始

```bash
# 1) 安装依赖（推荐虚拟环境）
pip install -r requirements.txt

# 2) 运行完整 demo（dry-run，无需任何 token）
make demo            # 等价于：python src/main.py demo

# 3) 运行全部测试（199 项，全部不联网）
make test            # 等价于：python -m unittest discover -s tests -p "test_*.py"

# 4) 发布前自检（配置 / 目录 / 依赖 / 安全状态）
make validate        # 等价于：python src/main.py validate

# 5) Jumia 健康检查（不上传、不联网）
make health          # 等价于：python src/main.py health
```

其他用法：

```bash
# 任意商品 URL（真实采集需安装 Playwright）
python src/main.py --url https://www.1688.com/offer/xxx.html

# 本地商品文件（JSON / CSV / Excel）
python src/main.py --input examples/full_demo.json
python src/main.py --input examples/batch_sample.csv --batch   # 批量 -> output/products/

# 真实采集（需安装：pip install playwright && playwright install chromium）
python -c "from src.collector.url_parser import collect_url; r = collect_url('https://detail.1688.com/offer/123.html'); print(r.product)"
```

Docker：

```bash
docker build -t jumia-agent .
docker run --rm jumia-agent            # 默认 demo
docker run --rm jumia-agent validate   # 发布前自检
```

## 4. 架构图

```
                       ┌──────────────────┐
                       │   Product Engine  │
                       │  采集/AI/类目/定价  │
                       └────────┬─────────┘
                                │
                       ┌────────▼─────────┐
                       │ Platform Adapter  │
                       │  统一 Payload 规范  │
                       └────────┬─────────┘
                                │
        ┌───────────┬───────────┼───────────┬───────────┐
        ▼           ▼           ▼           ▼           ▼
    ┌───────┐   ┌───────┐   ┌───────┐   ┌───────┐   ┌───────┐
    │ Jumia │   │ Noon  │   │ Ozon  │   │Wild-  │   │  ...  │
    │  ✅   │   │(规划) │   │(规划) │   │berries│   │(规划) │
    └───────┘   └───────┘   └───────┘   │(规划) │   └───────┘
                                      └───────┘
```

当前 v1.0.0 只实现 Jumia 适配器；其余平台为架构预留（见 Roadmap）。

数据流：

```
输入(URL / JSON / CSV / Excel)
  -> collector（浏览器真实采集，诚实返回 NEEDS_BROWSER / unsupported）
  -> ai.providers（mock / openai / deepseek / kimi 可插拔）
  -> ai（标题优化 / 多语言翻译）
  -> jumia.category（类目树两阶段匹配 + 属性 Schema）
  -> jumia.api（认证 + Payload 构建 + 校验 + HTTP Client + UploadGuard + Uploader）
  -> pricing（利润定价）
  -> validator（上架前检查：类目/属性完整度 + 评分）
  -> output/product.json 或 output/products/<SKU>.json
```

## 5. 安全说明

| 机制 | 说明 |
| --- | --- |
| **dry-run 默认** | `app.dry_run=true`、`http.dry_run=true`：CLI 永远只生成 Listing/Payload/请求预览，不发送 HTTP、不上传 |
| **Token 保护** | Token 只从环境变量（`JUMIA_API_KEY` / `JUMIA_API_TOKEN`）或配置读取；缺失抛 `MissingCredential`；绝不硬编码、绝不生成假 token |
| **上传保护** | `upload.enabled=false` 默认禁止；即使关闭 dry-run，也必须同时启用 upload、配置有效 token、通过 Health Check 与 UploadGuard 三道闸门 |
| **单 SKU 限制** | 第一次真实模式最多 1 个 SKU（`upload.max_products=1`），不允许批量上传 |
| **诚实数据** | 无法采集/识别的字段如实返回 `None` 并给出原因，绝不伪造商品数据 |
| **测试隔离** | 199 项测试全部使用 mock transport，不联网、不访问真实 Jumia |

## 6. Roadmap

- [x] MVP：统一商品模型 + dry-run 流水线 + 多语言 + 评分
- [x] P1：真实输入层 + 可插拔 AI Provider + 利润定价 + 批量处理
- [x] P2-1：Playwright 浏览器真实采集层
- [x] P2-2：Jumia 类目树两阶段匹配 + 属性 Schema
- [x] P3-1：Jumia Seller API Payload 层（dry-run）
- [x] P3-2-A：API 连接健康检查层
- [x] P3-2-B-1：真实 HTTP Client 层（请求构建 + 重试 + 响应解析）
- [x] P3-2-B-2：单 SKU 真实上传闭环（UploadGuard + JumiaUploader）
- [x] P4-0：发布准备（CLI 统一命令 / Docker / Makefile / 安全扫描 / 文档）
- [x] P4-1：开源发布整理（CONTRIBUTING / GitHub Actions CI / Release Notes）
- [ ] 真实 Jumia 类目树/属性 API：用官方 CategoryTree / Attribute API 替换内置参考数据
- [ ] 真实上传联调：接入 Jumia SellerCenter 凭据，验证认证方式与端点后开放第一个 SKU
- [ ] 图片下载与合规：抓取图片、压缩、校验尺寸/水印
- [ ] 多平台适配器：Noon / Ozon / Wildberries
- [ ] 交互式复核：Web UI / 在线文档审阅与编辑
- [ ] 运费/税费精细化：按目的国区分物流与平台费用

## 附录：模块索引

| 层 | 目录 | 关键文件 |
| --- | --- | --- |
| 商品模型 | `src/models/` | `product.py`（统一 Product Schema） |
| 采集 | `src/collector/` | `url_parser.py`、`browser/`（Playwright 采集 + 字段提取器）、`excel_collector.py` |
| AI | `src/ai/` | `providers/`（mock/openai/deepseek/kimi）、`title_optimizer.py`、`translator.py`、`category_matcher.py` |
| Jumia 类目 | `src/jumia/category/` | `category_tree.py`、`category_matcher.py`、`attribute_schema.py` |
| Jumia API | `src/jumia/api/` | `auth.py`、`http_client.py`、`client.py`、`upload_guard.py`、`uploader.py`、payload 构建器 |
| 定价 | `src/pricing/` | `calculator.py`（成本反推建议售价） |
| 校验 | `src/validator/` | `listing_check.py`（评分 + 问题清单） |
| 流水线 | `src/` | `pipeline.py`、`main.py`（CLI） |
| 测试 | `tests/` | 10 个测试文件，199 项，全部不联网 |

## 许可证

[MIT](LICENSE)

## 贡献与发布

- 贡献指南：[CONTRIBUTING.md](CONTRIBUTING.md)
- 版本说明：[RELEASE_NOTES.md](RELEASE_NOTES.md)

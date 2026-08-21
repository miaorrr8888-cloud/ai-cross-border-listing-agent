# Release Notes

## v1.0.0 — 首个公开发布（MVP）

**发布日期**：2026-08-21
**状态**：Stable · dry-run 默认 · upload 禁用

---

### 项目介绍

**Jumia AI Listing Agent** 是一个面向跨境新手的 AI 商品上架助手：你只需要提供一个商品链接或一份商品 JSON，Agent 自动完成「采集 → AI 优化 → 多语言生成 → 类目匹配 → 利润测算 → Jumia Listing/Payload 生成 → 上架前检查」，产出一份结构完整、可直接复核的 `product.json`。

核心设计：**所有危险操作默认关闭**。不联网上传、不预置任何假 API Token，接入真实凭据即可平滑升级到真实上传。

### 核心能力

| 能力 | 说明 |
|---|---|
| URL 商品采集 | 1688 / 淘宝 / Amazon / AliExpress，Playwright 浏览器采集 + 标准库 HTML 解析双通道 |
| AI 标题优化 | mock / OpenAI / DeepSeek / Kimi 可插拔 Provider，mock 输出带 `[*-draft]` 标记 |
| 多语言生成 | 英 / 法 / 阿（Jumia 三大市场语言）+ 中文原文 |
| 类目匹配 | 两阶段匹配（AI 产品理解 → Jumia 类目树映射），输出 category_id + 置信度 |
| 属性补全 | 按类目 Required/Optional 属性 Schema 校验，缺项如实列出 |
| 利润计算 | 逆推公式 `sale = total_cost / (1 - commission - margin)`，佣金/汇率/目标利润率可配 |
| Jumia Payload | Product / Offer / Inventory 三段式 payload + 统一校验器 |
| API 上传框架 | HTTP Client（重试/退避/响应解析）+ UploadGuard 安全阀 + 单 SKU 上传闭环（默认禁用） |

### 安全设计

1. **dry-run 默认开启** —— 所有流程只生成计划与 payload，不发送真实请求。
2. **上传默认禁用** —— `upload.enabled=false`；启用后仍受 `UploadGuard` 限制：单次最多 1 个 SKU（`max_products: 1`），不支持批量。
3. **Token 保护** —— 凭据只从环境变量（`JUMIA_API_KEY` / `JUMIA_API_TOKEN`）或本地配置读取；缺失时抛 `MissingCredential`，绝不生成假凭证。
4. **诚实失败** —— 无法真实采集/识别时如实返回 `NEEDS_BROWSER` / `unsupported` / `None`，绝不伪造数据。
5. **测试不联网** —— 199 项测试全部使用 mock transport / mock provider，CI 中同样零真实网络调用。

### 测试结果

```
Ran 199 tests in ~0.1s — OK（全部通过，全部不联网）

tests/test_ai_provider.py        10  AI Provider 架构与 mock 标记
tests/test_batch.py               7  批量处理（JSON/CSV/Excel）
tests/test_browser_collector.py  14  URL 解析 + 浏览器采集（mock HTML）
tests/test_category.py           16  类目树 + 两阶段匹配 + 属性 Schema
tests/test_http_client.py        62  HTTP Client（请求构造/重试/解析/dry-run）
tests/test_jumia_api.py          18  Payload 构建 + 校验 + 认证
tests/test_jumia_health.py       13  健康检查 + 错误映射
tests/test_mvp.py                14  端到端 dry-run 流程
tests/test_pricing.py             6  利润定价公式
tests/test_uploader.py           39  UploadGuard + 上传闭环（mock transport）
```

CI：GitHub Actions 在 ubuntu-latest + Python 3.12 上执行「安装依赖 → 全部测试 → `validate` 自检 → `health` 检查」。

### Roadmap

| 阶段 | 内容 | 状态 |
|---|---|---|
| P1 | 真实输入层 + AI Provider 架构 + 定价 | ✅ |
| P2 | 浏览器采集 + 类目/属性智能匹配 | ✅ |
| P3 | Jumia API 层（Payload/Health/HTTP Client/Upload Guard/单 SKU 闭环） | ✅ |
| **P4.0** | **v1.0.0 MVP 发布准备** | ✅ 本版本 |
| P4.1+ | 真实 Jumia 凭据接入：先验证认证（非上传端点），再开放第一个 SKU | 🔜 |
| P5 | 多平台 Adapter：Noon / Ozon / Wildberries | 🔜 |
| P6 | 批量上传（需先通过真实单 SKU 验证并放宽 max_products） | 🔜 |

### 升级说明

- 首次使用请复制 `config/config.example.yaml` 为 `config.yaml`（已加入 `.gitignore`）。
- 真实 AI 能力：配置 `ai.provider` + 环境变量 `OPENAI_API_KEY` / `DEEPSEEK_API_KEY` / `MOONSHOT_API_KEY`。
- 真实上传：需 Jumia SellerCenter API 凭据，详见 SKILL.md「真实账号接入清单」。

---

**License**: MIT

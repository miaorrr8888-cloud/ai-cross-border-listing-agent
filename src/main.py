"""Jumia AI Listing Agent — 统一 CLI 入口（v1.0.0，默认 dry-run，不联网、不填假 token）。

统一命令（推荐）：
  python src/main.py demo            # 运行完整演示流程（examples/full_demo.json）
  python src/main.py validate        # 发布前自检：配置 / 目录 / 依赖 / 安全状态
  python src/main.py health          # Jumia Health Check（不上传、不联网）

兼容旧参数（P1 时代用法，继续支持）：
  python src/main.py --url <商品URL>             # 真实输入层；无法抓取时提示需要浏览器插件
  python src/main.py --input examples/sample_product.json
  python src/main.py --input examples/batch_sample.csv --batch
  python src/main.py --demo                       # 等价于 demo 子命令

安全红线：
  - CLI 永远 dry-run：只生成 Listing / Payload / 请求预览，不上传。
  - 真实上传必须走代码层 JumiaClient.live_upload()（upload.enabled=false 默认禁止）。
  - 不读取、不写入、不伪造任何 token。

输出：output/product.json（单商品）/ output/products/（批量）
"""
from __future__ import annotations

import argparse
import os
import sys

# 把项目根目录加入导入路径，使 `src.*` 可用
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.collector.excel_collector import batch_generate, read_products
from src.collector.url_parser import parse_url
from src.models.product import Product
from src.pipeline import run
from src.utils.common import load_config, save_json

CONFIG_PATH = os.path.join(ROOT, "config", "config.example.yaml")
OUT_PATH = os.path.join(ROOT, "output", "product.json")
BATCH_DIR = os.path.join(ROOT, "output", "products")
FULL_DEMO_PATH = os.path.join(ROOT, "examples", "full_demo.json")
SAMPLE_PATH = os.path.join(ROOT, "examples", "sample_product.json")

REQUIRED_DIRS = ["config", "examples", "src", "tests", "output"]


# ── demo：完整演示流程 ─────────────────────────────────────────


def cmd_demo() -> int:
    """运行完整 dry-run 演示：采集输入 → AI 优化 → 类目匹配 → 定价 → Payload。"""
    cfg = load_config(CONFIG_PATH)

    demo_path = FULL_DEMO_PATH if os.path.exists(FULL_DEMO_PATH) else SAMPLE_PATH
    if not os.path.exists(demo_path):
        print("[FAIL] 未找到示例数据：examples/full_demo.json")
        return 1

    print(f"[demo] 使用示例：{os.path.relpath(demo_path, ROOT)}")
    products = read_products(demo_path)
    if not products:
        print("[FAIL] 示例数据为空")
        return 1
    product = products[0]

    print("[demo] 运行 dry-run 流程（AI 优化 → 类目匹配 → 定价 → Jumia Payload）...")
    output = run(product, cfg)
    _print_single(output, OUT_PATH)
    return 0


# ── validate：发布前自检 ───────────────────────────────────────


def cmd_validate() -> int:
    """检查：配置 / 目录 / 依赖 / 安全状态。全部通过返回 0。"""
    ok = True
    warn = []

    print("=" * 60)
    print("Jumia AI Listing Agent — 发布前自检（validate）")
    print("=" * 60)

    # 1) 配置检查
    print("\n[1/4] 配置检查")
    cfg = load_config(CONFIG_PATH)
    if not cfg:
        print("  [FAIL] 无法加载 config/config.example.yaml（缺少 pyyaml 或文件不存在）")
        ok = False
    else:
        checks = [
            ("app.dry_run == true", cfg.get("app", {}).get("dry_run") is True),
            ("upload.enabled == false", cfg.get("upload", {}).get("enabled") is False),
            ("http.dry_run == true", cfg.get("http", {}).get("dry_run") is True),
            ("ai.api_key 为空", not cfg.get("ai", {}).get("api_key")),
            ("jumia.api_key 为空", not cfg.get("jumia", {}).get("api_key")),
        ]
        for name, passed in checks:
            print(f"  [{'OK' if passed else 'FAIL'}] {name}")
            if not passed:
                ok = False

    # 2) 目录检查
    print("\n[2/4] 目录检查")
    for d in REQUIRED_DIRS:
        exists = os.path.isdir(os.path.join(ROOT, d))
        print(f"  [{'OK' if exists else 'FAIL'}] {d}/")
        if not exists:
            ok = False

    # 3) 依赖检查（可选依赖只提示，不算失败）
    print("\n[3/4] 依赖检查")
    try:
        import yaml  # noqa: F401
        print("  [OK] pyyaml（必选）")
    except ImportError:
        print("  [FAIL] pyyaml 缺失（必选）：pip install pyyaml")
        ok = False
    try:
        import openpyxl  # noqa: F401
        print("  [OK] openpyxl（可选：Excel 批量）")
    except ImportError:
        warn.append("openpyxl 未安装（Excel 批量不可用）：pip install openpyxl")
        print("  [WARN] openpyxl 未安装（可选，Excel 批量不可用）")
    try:
        import playwright  # noqa: F401
        print("  [OK] playwright（可选：浏览器真实采集）")
    except ImportError:
        warn.append("playwright 未安装（浏览器采集不可用，dry-run 不受影响）")
        print("  [WARN] playwright 未安装（可选，浏览器采集不可用）")

    # 4) 安全状态检查
    print("\n[4/4] 安全状态检查")
    env_set = []
    for var in ("JUMIA_API_KEY", "JUMIA_API_TOKEN"):
        if os.environ.get(var):
            env_set.append(var)
    if env_set:
        warn.append(f"环境变量 {', '.join(env_set)} 已设置（本机真实凭据，仅运行时使用，不进入代码库）")
        print(f"  [INFO] 环境变量已设置：{', '.join(env_set)}（仅运行时使用）")
    else:
        print("  [OK] 未检测到 JUMIA_API_KEY / JUMIA_API_TOKEN（dry-run 无需凭据）")

    # 汇总
    print("\n" + "=" * 60)
    if ok:
        print(f"[PASS] 自检通过{'; ' + str(len(warn)) + ' 条提示' if warn else ''}")
        for w in warn:
            print(f"  - 提示：{w}")
        return 0
    print("[FAIL] 自检未通过，请修复上述 FAIL 项后重试")
    return 1


# ── health：Jumia 健康检查（不上传、不联网） ────────────────────


def cmd_health() -> int:
    """运行 Jumia Health Check：仅校验凭据存在性与配置状态，不联网、不上传。"""
    from src.jumia.api.auth import JumiaAuth
    from src.jumia.api.health import check_health

    cfg = load_config(CONFIG_PATH)
    auth = JumiaAuth.from_config(cfg)
    report = check_health(auth, dry_run=True, config=cfg)

    print("=" * 60)
    print("Jumia API Health Check（dry-run，不上传、不联网）")
    print("=" * 60)
    d = report.to_dict()
    print(f"  auth_status     : {d['auth_status']}")
    print(f"  api_status      : {d['api_status']}")
    print(f"  category_status : {d['category_status']}")
    print(f"  upload_enabled  : {d['upload_enabled']}")
    if d.get("message"):
        print(f"  message         : {d['message']}")
    print("-" * 60)
    if d["auth_status"] == "ok":
        print("[OK] 凭据存在（仅表示已配置；未发起任何真实请求）")
    else:
        print("[INFO] 未配置凭据（dry-run 模式无需凭据；真实上传前需配置）")
    print("[OK] upload_enabled=false：真实上传默认禁止")
    return 0


# ── 旧参数兼容 ─────────────────────────────────────────────────


def _run_legacy(args) -> int:
    cfg = load_config(CONFIG_PATH)

    if args.url:
        # 真实输入层：能抓取则返回 Product，否则明确提示「需要浏览器采集插件」
        res = parse_url(args.url)
        if res.status == "needs_browser_plugin":
            print(f"[!] {res.message}")
            return 1
        product = res.product or Product()
        _print_single(run(product, cfg), OUT_PATH)
        return 0

    if args.input:
        products = read_products(args.input)
        if args.batch or len(products) > 1:
            summary = batch_generate(products, cfg, out_dir=BATCH_DIR)
            print(f"[OK] 批量 dry-run 完成，共 {len(summary)} 条，写入：{BATCH_DIR}")
            for s in summary:
                print(f"     {s['sku']}: 评分 {s['score']} -> {s['path']}")
            return 0
        product = products[0] if products else Product()
        _print_single(run(product, cfg), OUT_PATH)
        return 0

    # 默认：demo
    return cmd_demo()


def _print_single(output: dict, out_path: str) -> None:
    save_json(output, out_path)
    print(f"[OK] dry-run 完成，结果已写入：{out_path}")
    print(f"     评分：{output['listing_check']['score']} | "
          f"类目：{output['category_suggestion']['category']} "
          f"({output['category_suggestion']['confidence']})")
    if output.get("price_plan"):
        pp = output["price_plan"]
        print(f"     建议售价：{pp['sale_price']} {pp['currency']} "
              f"(利润 {pp['profit']}，利润率 {pp['actual_margin']:.0%})")
    print(f"     英文标题：{output['ai_optimized']['title_en']}")
    print(f"     法语标题：{output['ai_optimized']['title_fr']}")
    print(f"     阿拉伯标题：{output['ai_optimized']['title_ar']}")


# ── 入口 ───────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="jumia-agent",
        description="Jumia AI Listing Agent (v1.0.0, dry-run 优先)",
    )
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="dry-run 模式（默认开启；CLI 永远 dry-run，不支持真实上传）")
    parser.add_argument("--url", help="任意商品 URL（兼容旧参数）")
    parser.add_argument("--input", help="商品 JSON / CSV / Excel 路径（兼容旧参数）")
    parser.add_argument("--batch", action="store_true",
                        help="批量模式：把 --input 的多条商品写入 output/products/（兼容旧参数）")
    parser.add_argument("--demo", action="store_true", help="等价于 demo 子命令（兼容旧参数）")
    args, unknown = parser.parse_known_args()

    # 统一子命令优先：demo / validate / health
    command = unknown[0] if unknown else None
    if command in ("demo", "validate", "health"):
        return {"demo": cmd_demo, "validate": cmd_validate, "health": cmd_health}[command]()

    if command is not None:
        print(f"[FAIL] 未知命令：{command}（可用：demo / validate / health）")
        return 1

    if args.demo:
        return cmd_demo()
    if args.url or args.input:
        return _run_legacy(args)
    # 无参数：默认 demo
    return cmd_demo()


if __name__ == "__main__":
    sys.exit(main())

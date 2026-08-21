# jumia-ai-listing-agent — 演示镜像（v1.0.0）
#
# 用途：运行完整 dry-run 演示流程（不联网、不上传、无需任何 API token）。
# 构建：docker build -t jumia-agent .
# 运行：docker run --rm jumia-agent            # 默认 demo
#       docker run --rm jumia-agent validate   # 发布前自检
#
# 安全说明：
# - 镜像内不包含任何密钥；token 一律通过运行时环境变量注入。
# - 默认 dry_run=true、upload.enabled=false。

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# 1) 先装依赖（利用 Docker 层缓存）
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 2) 复制项目
COPY . .

# 3) 默认运行 demo（完整 dry-run 演示流程）
CMD ["python", "src/main.py", "demo"]

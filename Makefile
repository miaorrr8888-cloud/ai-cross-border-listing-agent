# jumia-ai-listing-agent — Makefile（v1.0.0）
#
# 常用命令：
#   make test      运行全部测试（不联网）
#   make demo      运行完整 dry-run 演示流程
#   make validate  发布前自检（配置 / 目录 / 依赖 / 安全状态）
#   make health    Jumia 健康检查（不上传、不联网）
#   make docker    构建演示镜像
#   make clean     清理 Python 缓存

PY ?= python3

.PHONY: test demo validate health docker clean help

help:
	@echo "可用目标："
	@echo "  make test      运行全部测试（不联网）"
	@echo "  make demo      运行完整 dry-run 演示流程"
	@echo "  make validate  发布前自检（配置 / 目录 / 依赖 / 安全状态）"
	@echo "  make health    Jumia 健康检查（不上传、不联网）"
	@echo "  make docker    构建演示镜像"
	@echo "  make clean     清理 Python 缓存"

test:
	$(PY) -m unittest discover -s tests -p "test_*.py"

demo:
	$(PY) src/main.py demo

validate:
	$(PY) src/main.py validate

health:
	$(PY) src/main.py health

docker:
	docker build -t jumia-agent .

clean:
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null; true
	rm -rf .pytest_cache .coverage htmlcov 2>/dev/null; true

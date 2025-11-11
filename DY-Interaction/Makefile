.PHONY: help install test lint format check clean

help:
	@echo "DY-Interaction 项目命令"
	@echo ""
	@echo "使用方法: make [命令]"
	@echo ""
	@echo "命令列表:"
	@echo "  install     - 安装项目依赖"
	@echo "  test        - 运行测试"
	@echo "  lint        - 代码质量检查"
	@echo "  format      - 自动格式化代码"
	@echo "  check       - 完整检查（lint + test）"
	@echo "  clean       - 清理缓存文件"
	@echo "  security    - 安全扫描"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=src --cov-report=term-missing

lint:
	@echo "==> Running flake8..."
	flake8 src/ programs/ scripts/ --exclude=archive
	@echo "==> Running mypy..."
	mypy src/ --exclude archive
	@echo "==> Checking import order..."
	isort src/ programs/ scripts/ --check-only --skip archive

format:
	@echo "==> Formatting with black..."
	black src/ programs/ scripts/ --exclude archive
	@echo "==> Sorting imports..."
	isort src/ programs/ scripts/ --skip archive

check: lint test
	@echo "==> All checks passed!"

security:
	@echo "==> Running security scan with bandit..."
	bandit -r src/ -f json -o bandit-report.json
	@echo "==> Security scan complete. Check bandit-report.json"

clean:
	@echo "==> Cleaning cache files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "==> Cache cleaned!"

.PHONY: help install fmt format run dev clean test

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python
CONDA_ENV := gptAutoCrawling
HOST := 0.0.0.0
PORT := 8083

help: ## Show this help message
	@echo "GPT Auto Crawling - Makefile Commands"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies using conda environment
	@echo "Installing dependencies..."
	conda env update -f environment.yml --prune
	conda run -n $(CONDA_ENV) playwright install chromium
	@echo "✅ Dependencies installed successfully"

fmt: ## Format and lint code with ruff
	@echo "Formatting and checking code..."
	@conda run -n $(CONDA_ENV) ruff format . || true
	@conda run -n $(CONDA_ENV) ruff check . --fix || true
	@echo "✅ Code formatted and checked successfully"

format: fmt ## Alias for fmt

run: ## Run the FastAPI server locally
	@echo "Starting GPT Auto Crawling server on http://$(HOST):$(PORT)"
	conda run -n $(CONDA_ENV) uvicorn main:app --host $(HOST) --port $(PORT)

dev: ## Run the FastAPI server in development mode with auto-reload
	@echo "Starting development server with auto-reload on http://$(HOST):$(PORT)"
	conda run -n $(CONDA_ENV) uvicorn main:app --host $(HOST) --port $(PORT) --reload

test: ## Run tests
	@echo "Running tests..."
	conda run -n $(CONDA_ENV) $(PYTHON) test.py
	@echo "✅ Tests complete"

clean: ## Clean up Python cache files and logs
	@echo "Cleaning up cache files and logs..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	@echo "✅ Cleanup complete"

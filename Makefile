.PHONY: help setup dev install lint test run clean email certs contacts images blog all-automations

# Default target
.DEFAULT_GOAL := help

# Colors for terminal output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

help:  ## Show this help message
	@echo "$(BLUE)Automation Toolkit - Available Commands:$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Quick Start:$(RESET)"
	@echo "  1. Run 'make setup' for initial project setup"
	@echo "  2. Edit workspace/.env with your credentials"
	@echo "  3. Run any automation (e.g., 'make email', 'make certs')"

setup:  ## One-time project setup (creates workspace, installs deps)
	@echo "$(BLUE)🚀 Setting up Automation Toolkit...$(RESET)"
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		uv venv; \
	fi
	@echo "Installing dependencies..."
	@uv pip install -e .
	@echo "Setting up workspace..."
	@uv run python scripts/setup.py --init
	@echo ""
	@echo "$(GREEN)✅ Setup complete!$(RESET)"
	@echo "$(YELLOW)Next steps:$(RESET)"
	@echo "  1. Edit workspace/.env with your credentials"
	@echo "  2. Run 'make help' to see available commands"

dev:  ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(RESET)"
	@uv pip install -e ".[dev]"
	@echo "$(GREEN)✅ Dev environment ready!$(RESET)"

install:  ## Install/update dependencies
	@echo "$(BLUE)Syncing dependencies...$(RESET)"
	@uv pip sync
	@echo "$(GREEN)✅ Dependencies updated!$(RESET)"

lint:  ## Run code linting and formatting
	@echo "$(BLUE)Running linting checks...$(RESET)"
	@uv run ruff check src/ tests/ --fix
	@uv run ruff format src/ tests/
	@echo "$(GREEN)✅ Code formatted and linted!$(RESET)"

test:  ## Run all tests
	@echo "$(BLUE)Running tests...$(RESET)"
	@uv run pytest

clean:  ## Clean temporary files and caches
	@echo "$(BLUE)Cleaning temporary files...$(RESET)"
	@rm -rf workspace/cache/* 2>/dev/null || true
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@echo "$(GREEN)✅ Cleaned!$(RESET)"

# ============ AUTOMATION COMMANDS ============

email:  ## Send bulk emails interactively
	@echo "$(BLUE)📧 Email Automation$(RESET)"
	@uv run python -m src.cli email --interactive

certs:  ## Generate certificates interactively
	@echo "$(BLUE)📜 Certificate Generation$(RESET)"
	@uv run python -m src.cli certificates --interactive

contacts:  ## Generate VCF contacts interactively
	@echo "$(BLUE)📱 Contact Generation$(RESET)"
	@uv run python -m src.cli contacts --interactive

images:  ## Optimize images interactively
	@echo "$(BLUE)🖼️  Image Optimization$(RESET)"
	@uv run python -m src.cli images --interactive

blog:  ## Generate blog MDX interactively
	@echo "$(BLUE)✍️  Blog Generation$(RESET)"
	@uv run python -m src.cli blog --interactive

all-automations:  ## Show all available automations
	@echo "$(BLUE)Available Automations:$(RESET)"
	@echo ""
	@echo "  $(GREEN)make email$(RESET)    - Send bulk emails with templates"
	@echo "  $(GREEN)make certs$(RESET)    - Generate personalized PDF certificates"
	@echo "  $(GREEN)make contacts$(RESET) - Create VCF contact cards from phone numbers"
	@echo "  $(GREEN)make images$(RESET)   - Optimize and convert images to WebP"
	@echo "  $(GREEN)make blog$(RESET)     - Generate MDX blog posts with AI proofreading"

# ============ QUICK RUN COMMANDS ============

run-email-bulk:  ## Run bulk email with default settings
	@uv run python -m src.cli email --config workspace/configs/email.json --recipients workspace/inputs/email/recipients.csv

run-certs-batch:  ## Run certificate generation with default settings
	@uv run python -m src.cli certificates --config workspace/configs/certificates.json --recipients workspace/inputs/certificates/recipients.txt

run-contacts-batch:  ## Run contact generation with default settings
	@uv run python -m src.cli contacts --input workspace/inputs/contacts/numbers.txt --prefix "Contact"

run-images-batch:  ## Run image optimization with default settings
	@uv run python -m src.cli images --input workspace/inputs/images --output workspace/outputs/images

# ============ UTILITY COMMANDS ============

migrate:  ## Migrate data from old structure to new workspace
	@echo "$(BLUE)Running data migration tool...$(RESET)"
	@uv run python scripts/migrate.py

migrate-dry:  ## Preview migration without making changes
	@echo "$(BLUE)Running migration preview...$(RESET)"
	@uv run python scripts/migrate.py --dry-run

check-env:  ## Check if environment is properly configured
	@echo "$(BLUE)Checking environment configuration...$(RESET)"
	@uv run python scripts/check_env.py

update:  ## Update all dependencies to latest versions
	@echo "$(BLUE)Updating dependencies...$(RESET)"
	@uv pip install --upgrade -e .
	@echo "$(GREEN)✅ Dependencies updated!$(RESET)"

version:  ## Show project version
	@echo "Automation Toolkit v2.0.0"
	@echo "Python: $$(uv run python --version)"
	@echo "UV: $$(uv --version)"

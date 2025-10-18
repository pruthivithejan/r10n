#!/bin/bash

# r10n - Setup and automation script
# Cross-platform alternative to Makefile

set -e  # Exit on any error

# Colors for terminal output
BLUE='\033[36m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
RESET='\033[0m'

# Helper function to print colored output
print_info() {
    echo -e "${BLUE}$1${RESET}"
}

print_success() {
    echo -e "${GREEN}$1${RESET}"
}

print_warning() {
    echo -e "${YELLOW}$1${RESET}"
}

print_error() {
    echo -e "${RED}$1${RESET}"
}

# Show help message
show_help() {
    print_info "r10n - Available Commands:"
    echo ""
    echo "  setup                   One-time project setup (creates workspace, installs deps)"
    echo "  dev                     Install development dependencies"
    echo "  install                 Install/update dependencies"
    echo "  lint                    Run code linting and formatting"
    echo "  test                    Run all tests"
    echo "  clean                   Clean temporary files and caches"
    echo ""
    print_info "Automation Commands:"
    echo "  email                   Send bulk emails interactively"
    echo "  certs                   Generate certificates interactively"
    echo "  contacts                Generate VCF contacts interactively"
    echo "  images                  Optimize images interactively"
    echo "  blog                    Generate blog MDX interactively"
    echo "  all-automations         Show all available automations"
    echo ""
    print_info "Quick Run Commands:"
    echo "  run-email-bulk          Run bulk email with default settings"
    echo "  run-certs-batch         Run certificate generation with default settings"
    echo "  run-contacts-batch      Run contact generation with default settings"
    echo "  run-images-batch        Run image optimization with default settings"
    echo ""
    print_info "Utility Commands:"
    echo "  migrate                 Migrate data from old structure to new workspace"
    echo "  migrate-dry             Preview migration without making changes"
    echo "  check-env               Check if environment is properly configured"
    echo "  update                  Update all dependencies to latest versions"
    echo "  version                 Show project version"
    echo "  help                    Show this help message"
    echo ""
    print_warning "Quick Start:"
    echo "  1. Run './setup.sh setup' for initial project setup"
    echo "  2. Edit workspace/.env with your credentials"
    echo "  3. Run any automation (e.g., './setup.sh email', './setup.sh certs')"
}

# One-time project setup
setup() {
    print_info "🚀 Setting up r10n..."
    
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        uv venv
    fi
    
    echo "Installing dependencies..."
    uv pip install -e .
    
    echo "Setting up workspace..."
    uv run python scripts/setup.py --init
    
    echo ""
    print_success "✅ Setup complete!"
    print_warning "Next steps:"
    echo "  1. Edit workspace/.env with your credentials"
    echo "  2. Run './setup.sh help' to see available commands"
}

# Install development dependencies
dev() {
    print_info "Installing development dependencies..."
    uv pip install -e ".[dev]"
    print_success "✅ Dev environment ready!"
}

# Install/update dependencies
install() {
    print_info "Syncing dependencies..."
    uv pip sync
    print_success "✅ Dependencies updated!"
}

# Run code linting and formatting
lint() {
    print_info "Running linting checks..."
    uv run ruff check src/ tests/ --fix
    uv run ruff format src/ tests/
    print_success "✅ Code formatted and linted!"
}

# Run all tests
test() {
    print_info "Running tests..."
    uv run pytest
}

# Clean temporary files and caches
clean() {
    print_info "Cleaning temporary files..."
    rm -rf workspace/cache/* 2>/dev/null || true
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name ".DS_Store" -delete 2>/dev/null || true
    print_success "✅ Cleaned!"
}

# Automation commands
email() {
    print_info "📧 Email Automation"
    uv run python -m src.cli email --interactive
}

certs() {
    print_info "📜 Certificate Generation"
    uv run python -m src.cli certificates --interactive
}

contacts() {
    print_info "📱 Contact Generation"
    uv run python -m src.cli contacts --interactive
}

images() {
    print_info "🖼️  Image Optimization"
    uv run python -m src.cli images --interactive
}

blog() {
    print_info "✍️  Blog Generation"
    uv run python -m src.cli blog --interactive
}

all_automations() {
    print_info "Available Automations:"
    echo ""
    echo "  ./setup.sh email     - Send bulk emails with templates"
    echo "  ./setup.sh certs     - Generate personalized PDF certificates"
    echo "  ./setup.sh contacts  - Create VCF contact cards from phone numbers"
    echo "  ./setup.sh images    - Optimize and convert images to WebP"
    echo "  ./setup.sh blog      - Generate MDX blog posts with AI proofreading"
}

# Quick run commands
run_email_bulk() {
    uv run python -m src.cli email --config workspace/configs/email.json --recipients workspace/inputs/email/recipients.csv
}

run_certs_batch() {
    uv run python -m src.cli certificates --config workspace/configs/certificates.json --recipients workspace/inputs/certificates/recipients.txt
}

run_contacts_batch() {
    uv run python -m src.cli contacts --input workspace/inputs/contacts/numbers.txt --prefix "Contact"
}

run_images_batch() {
    uv run python -m src.cli images --input workspace/inputs/images --output workspace/outputs/images
}

# Utility commands
migrate() {
    print_info "Running data migration tool..."
    uv run python scripts/migrate.py
}

migrate_dry() {
    print_info "Running migration preview..."
    uv run python scripts/migrate.py --dry-run
}

check_env() {
    print_info "Checking environment configuration..."
    uv run python scripts/check_env.py
}

update() {
    print_info "Updating dependencies..."
    uv pip install --upgrade -e .
    print_success "✅ Dependencies updated!"
}

version() {
    echo "r10n v2.0.0"
    echo "Python: $(uv run python --version)"
    echo "UV: $(uv --version)"
}

# Main script logic
case "${1:-help}" in
    "setup")
        setup
        ;;
    "dev")
        dev
        ;;
    "install")
        install
        ;;
    "lint")
        lint
        ;;
    "test")
        test
        ;;
    "clean")
        clean
        ;;
    "email")
        email
        ;;
    "certs")
        certs
        ;;
    "contacts")
        contacts
        ;;
    "images")
        images
        ;;
    "blog")
        blog
        ;;
    "all-automations")
        all_automations
        ;;
    "run-email-bulk")
        run_email_bulk
        ;;
    "run-certs-batch")
        run_certs_batch
        ;;
    "run-contacts-batch")
        run_contacts_batch
        ;;
    "run-images-batch")
        run_images_batch
        ;;
    "migrate")
        migrate
        ;;
    "migrate-dry")
        migrate_dry
        ;;
    "check-env")
        check_env
        ;;
    "update")
        update
        ;;
    "version")
        version
        ;;
    "help"|*)
        show_help
        ;;
esac
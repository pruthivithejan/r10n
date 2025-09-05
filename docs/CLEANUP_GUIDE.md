# 🧹 Cleanup Guide - Files and Folders to Remove

After successfully migrating to the new structure and verifying everything works, you can safely remove these old files and folders:

## ⚠️ **IMPORTANT: Before Removing Anything**

1. **Verify Migration**: Run `make migrate` and ensure all data is copied to `workspace/`
2. **Test Automations**: Run at least one automation (e.g., `make contacts`) to confirm it works
3. **Backup Important Data**: Make sure you have backups of any critical data

## 📁 **Folders to Remove**

### **1. Old Data Directory** (MOST IMPORTANT)
```bash
data/                    # The entire old data directory
├── emails/              # Old email files
├── certificates/        # Old certificate files  
├── phone_numbers/       # Old contact files
├── outlook/             # Old Outlook email files
├── blog/                # Old blog files (if any)
└── images/              # Old image files (if any)
```

**Remove with:**
```bash
# After verifying migration is successful
rm -rf data/
```

### **2. Old Documentation** (Now Outdated)
```bash
docs/generate_contact.py     # Old example script
docs/numbers.txt             # Old example data
docs/run_generate_contacts.cmd  # Windows-specific old runner
```

**Remove with:**
```bash
rm docs/generate_contact.py docs/numbers.txt docs/run_generate_contacts.cmd
```

### **3. Old Example Files** (Replaced by New Structure)
```bash
examples/certificates/    # Old certificate examples
examples/emails/         # Old email examples
examples/outlook/        # Old Outlook examples
examples/phone_numbers/  # Old phone number examples
```

**Remove with:**
```bash
rm -rf examples/certificates/ examples/emails/ examples/outlook/ examples/phone_numbers/
```

## 📄 **Files to Remove**

### **1. Old Setup Scripts** (Replaced by `make setup`)
```bash
setup.bat               # Old Windows setup script
setup.sh                # Old Unix setup script
```

**Remove with:**
```bash
rm setup.bat setup.sh
```

### **2. Old Requirements File** (Replaced by pyproject.toml)
```bash
requirements.txt        # Old pip requirements
```

**Remove with:**
```bash
rm requirements.txt
```

### **3. Old Main Entry Point** (Replaced by new CLI)
```bash
src/main.py            # Old command router
```

**Remove with:**
```bash
rm src/main.py
```

### **4. Old Test Files** (Need Rewriting for New Structure)
```bash
tests/test_main.py     # Tests for old main.py
```

**Remove with:**
```bash
rm tests/test_main.py
```

## 📋 **Complete Cleanup Commands**

Run these commands **AFTER** verifying migration and testing:

```bash
# Step 1: Remove old data directory (MOST IMPORTANT)
rm -rf data/

# Step 2: Remove old setup scripts
rm setup.bat setup.sh requirements.txt

# Step 3: Remove old examples (if they exist)
rm -rf examples/certificates/ examples/emails/ examples/outlook/ examples/phone_numbers/

# Step 4: Remove old documentation files
rm -f docs/generate_contact.py docs/numbers.txt docs/run_generate_contacts.cmd

# Step 5: Remove old main.py
rm src/main.py

# Step 6: Remove old tests
rm tests/test_main.py

# Step 7: Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
```

## ✅ **What to Keep**

These files/folders are part of the NEW structure and should NOT be removed:

```
✅ workspace/           # New data directory
✅ configs/             # Default configurations  
✅ templates/           # Template files
✅ scripts/             # Utility scripts (setup.py, migrate.py)
✅ src/cli.py          # New CLI
✅ src/automations/    # Automation modules
✅ Makefile            # Task runner
✅ pyproject.toml      # Modern Python config
✅ .env.example        # Environment template
✅ MIGRATION_*.md      # Migration documentation
✅ QUICK_START.md      # New documentation
✅ uv.lock             # UV lock file
```

## 🎯 **Quick Cleanup Script**

Save this as `cleanup.sh` and run it after verification:

```bash
#!/bin/bash
echo "⚠️  This will remove old files and folders!"
echo "Have you:"
echo "  1. Run 'make migrate' successfully?"
echo "  2. Tested at least one automation?"
echo "  3. Backed up important data?"
read -p "Continue? (y/N): " confirm

if [[ $confirm == "y" || $confirm == "Y" ]]; then
    echo "🧹 Cleaning up old structure..."
    
    # Remove old directories
    rm -rf data/ 2>/dev/null && echo "✓ Removed data/"
    rm -rf examples/certificates/ examples/emails/ examples/outlook/ examples/phone_numbers/ 2>/dev/null && echo "✓ Removed old examples"
    
    # Remove old files
    rm -f setup.bat setup.sh requirements.txt 2>/dev/null && echo "✓ Removed old setup files"
    rm -f src/main.py 2>/dev/null && echo "✓ Removed old main.py"
    rm -f tests/test_main.py 2>/dev/null && echo "✓ Removed old tests"
    rm -f docs/generate_contact.py docs/numbers.txt docs/run_generate_contacts.cmd 2>/dev/null && echo "✓ Removed old docs"
    
    # Clean cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    find . -type f -name "*.pyc" -delete 2>/dev/null
    echo "✓ Cleaned Python cache"
    
    echo "✅ Cleanup complete!"
else
    echo "❌ Cleanup cancelled"
fi
```

## 📊 **Storage Savings**

After cleanup, you'll typically save:
- **data/** directory: Usually the largest (all your data files)
- **Python cache**: Several MB of `__pycache__` files
- **Old scripts**: A few KB of outdated scripts

## ⚡ **Final Verification**

After cleanup, run these commands to ensure everything still works:

```bash
# Check status
uv run python -m src.cli status

# Test an automation
make contacts

# View available commands
make help
```

If everything works, congratulations! Your project is now fully migrated and cleaned up! 🎉

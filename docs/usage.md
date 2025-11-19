## 📖 Step-by-Step Usage Guide

### Step 1: Configure Your Environment

After setup, edit your credentials:

```bash
# Edit the environment file
nano workspace/.env

# Update these values:
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-password  # Use app-specific password
OPENAI_API_KEY=sk-your-api-key    # For blog generation (optional)
```

### Step 2: Check Your Setup

Verify everything is configured correctly:

```bash
# Check status
uv run python -m src.cli status

# See all available commands
make help
```

### Step 3: Run Your First Automation

Let's start with the simplest - generating contacts:

```bash
# Run interactively (recommended for beginners)
make contacts
```

The interactive mode will guide you through:
1. Selecting input file
2. Setting contact prefix
3. Choosing output location
4. Confirming generation

## 🎯 Available Automations

### 📧 Email Automation

Send bulk emails with personalization:

```bash
# Interactive mode
make email

# Or direct command
uv run python -m src.cli email \
  --recipients workspace/inputs/email/recipients.csv \
  --body workspace/inputs/email/template.txt \
  --config workspace/configs/email.json
```

**Input Format** (`recipients.csv`):
```csv
name,email
John Doe,john@example.com
Jane Smith,jane@example.com
```

**Template** (`template.txt`):
```
Dear {name},

Your personalized message here.

Best regards,
{sender_name}
```

### 📜 Certificate Generation

Create personalized PDF certificates:

```bash
# Interactive mode
make certs

# Direct command
uv run python -m src.cli certificates \
  --recipients workspace/inputs/certificates/recipients.txt \
  --template templates/certificates/template.pdf
```

**Recipients Format** (`recipients.txt`):
```
John Doe,Python Mastery,2024-01-15,Excellence
Jane Smith,Data Science,2024-01-16,Outstanding
```

### 📱 Contact Generation

Convert phone numbers to VCF contact cards:

```bash
# Interactive mode
make contacts

# Direct command
uv run python -m src.cli contacts \
  --input workspace/inputs/contacts/numbers.txt \
  --prefix "Customer"
```

**Input Format** (`numbers.txt`):
```
0771234567
0712345678
+94771234567
```

### 🖼️ Image Optimization

Optimize and convert images to WebP:

```bash
# Interactive mode
make images

# Direct command
uv run python -m src.cli images \
  --input workspace/inputs/images \
  --quality 85 \
  --max-size 1.0
```

### ✍️ Blog MDX Generation

Generate SEO-optimized blog posts:

```bash
# Interactive mode
make blog

# Direct command
uv run python -m src.cli blog \
  --input workspace/inputs/blog/post.txt \
  --title "My Blog Title" \
  --author "Your Name"
```
#!/bin/bash

# Automation Setup Script
# This script helps you set up the data folder structure and copy example files

echo "🚀 Setting up Automation Data Folder Structure..."

# Create data folder structure
echo "📁 Creating data directories..."
mkdir -p data/{emails,outlook,certificates/{templates,output},phone_numbers}
mkdir -p data/emails/attachments
mkdir -p data/outlook/certificates

# Check if examples exist
if [ ! -d "examples" ]; then
    echo "❌ Examples folder not found. Please run this script from the project root."
    exit 1
fi

echo "📋 Copying example files..."

# Copy example files to data folder
cp examples/emails/email_config.json.example data/emails/email_config.json
cp examples/emails/email_list.txt.example data/emails/email_list.txt
cp examples/emails/email.txt.example data/emails/email.txt

cp examples/outlook/email_config.json.example data/outlook/email_config.json
cp examples/outlook/recipients.txt.example data/outlook/recipients.txt
cp examples/outlook/email.txt.example data/outlook/email.txt

cp examples/certificates/config.json.example data/certificates/config.json
cp examples/certificates/recipients.txt.example data/certificates/recipients.txt

cp examples/phone_numbers/numbers.txt.example data/phone_numbers/numbers.txt

echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit the configuration files in data/ folders with your actual information"
echo "2. Replace placeholder email addresses with real recipients"
echo "3. Add your certificate template to data/certificates/templates/"
echo "4. Follow the examples/SETUP_GUIDE.md for detailed instructions"
echo ""
echo "⚠️  Important: Never commit files in the data/ folder - they contain sensitive information"
echo ""
echo "🎉 Ready to start automating!"

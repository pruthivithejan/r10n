@echo off
REM Automation Setup Script for Windows
REM This script helps you set up the data folder structure and copy example files

echo 🚀 Setting up Automation Data Folder Structure...

REM Create data folder structure
echo 📁 Creating data directories...
mkdir data\emails\attachments 2>nul
mkdir data\outlook\certificates 2>nul
mkdir data\certificates\templates 2>nul
mkdir data\certificates\output 2>nul
mkdir data\phone_numbers 2>nul

REM Check if examples exist
if not exist "examples" (
    echo ❌ Examples folder not found. Please run this script from the project root.
    pause
    exit /b 1
)

echo 📋 Copying example files...

REM Copy example files to data folder
copy examples\emails\email_config.json.example data\emails\email_config.json >nul
copy examples\emails\email_list.txt.example data\emails\email_list.txt >nul
copy examples\emails\email.txt.example data\emails\email.txt >nul

copy examples\outlook\email_config.json.example data\outlook\email_config.json >nul
copy examples\outlook\recipients.txt.example data\outlook\recipients.txt >nul
copy examples\outlook\email.txt.example data\outlook\email.txt >nul

copy examples\certificates\config.json.example data\certificates\config.json >nul
copy examples\certificates\recipients.txt.example data\certificates\recipients.txt >nul

copy examples\phone_numbers\numbers.txt.example data\phone_numbers\numbers.txt >nul

echo ✅ Setup complete!
echo.
echo 📝 Next steps:
echo 1. Edit the configuration files in data\ folders with your actual information
echo 2. Replace placeholder email addresses with real recipients
echo 3. Add your certificate template to data\certificates\templates\
echo 4. Follow the examples\SETUP_GUIDE.md for detailed instructions
echo.
echo ⚠️  Important: Never commit files in the data\ folder - they contain sensitive information
echo.
echo 🎉 Ready to start automating!
pause

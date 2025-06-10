# Automations

This is a basic Python project with a virtual environment setup.

## Setup

1. The virtual environment is already created in the `.venv` directory
2. To activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Project Structure

- `src/`: Source code directory
- `tests/`: Test files directory
- `requirements.txt`: Project dependencies

## Running Automations

This project contains various automation scripts that can be run from the command line. To see all available automations:
```bash
python src/main.py
```

### Contact Card Generator
Converts a list of phone numbers into a VCF file that can be imported into your contacts.

1. Create a text file with phone numbers (one per line)
2. Run the command:
```bash
python src/main.py generate_contacts <input_file> [options]
```

Options:
- `--output`, `-o`: Output VCF file name (default: contacts.vcf)
- `--prefix`, `-p`: Prefix for contact names (default: Contact)

Example:
```bash
python src/main.py generate_contacts numbers.txt --output my_contacts.vcf --prefix "Friend"
```

## Running Tests

To run tests:
```bash
pytest tests/
```

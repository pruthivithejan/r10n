# 📞 Phone Numbers for Contact Generation

## How to Use:
1. **Paste your phone numbers** into `numbers.txt` (one per line)
2. **Run the automation**: `python src/main.py generate_contacts`
3. **Find your VCF file** generated in this directory

## Supported Formats:
```
0729553860
+94785952202
071 533 5421
076-321-3985
775581028
```

## Example Usage:
```bash
# Generate contacts with default names
python src/main.py generate_contacts

# Generate with custom prefix
python src/main.py generate_contacts --prefix "Workshop Participant"
```

## Output:
- VCF files are saved in this directory
- Duplicate numbers are automatically removed
- Invalid numbers are reported and excluded
- Statistics are displayed after generation

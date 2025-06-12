# Phone Numbers

This directory contains phone number lists for generating contact cards.

## Format:
Create a text file with one phone number per line:

```
0729553860
0785952202
0715132486
+94714707197
071 5335421
076 321 3985
```

## Supported Formats:
- Sri Lankan numbers starting with 0 (e.g., 0712345678)
- International format with +94 (e.g., +94712345678)
- Numbers with spaces or dashes (automatically cleaned)
- Numbers without leading 0 (automatically prefixed)

## Example Usage:
```bash
python src/main.py generate_contacts data/phone_numbers/my_contacts.txt --prefix "Friend"
```

## Output:
- VCF files are automatically saved to the `data/` directory
- Duplicate numbers are automatically removed
- Invalid numbers are reported and excluded

"""VCF contact card generation automation."""

import re
from pathlib import Path


def clean_number(number: str) -> str | None:
    """Clean and validate a phone number (Sri Lankan format).

    Handles comma-separated or space-separated numbers by taking the first valid one.
    Removes all non-digit characters before validation.

    Args:
        number: Raw phone number string

    Returns:
        Cleaned number in +94XXXXXXXXX format, or None if invalid
    """
    number = number.strip()

    if "," in number:
        parts = [p.strip() for p in number.split(",")]
        for part in parts:
            if part:
                result = clean_number(part)
                if result:
                    return result
        return None

    number = re.sub(r"\D", "", number)

    number = number.lstrip("0")

    if number.startswith("94") and len(number) == 11:
        number = "+" + number
    else:
        number = "+94" + number

    return number if re.fullmatch(r"\+94\d{9}", number) else None


def generate_vcf_from_file(
    input_file: str, output_name: str = "contacts.vcf", prefix: str = "Contact"
):
    """
    Generate a VCF file from a text file containing phone numbers.

    Args:
        input_file (str): Path to text file containing phone numbers (one per line)
        output_name (str): Path/name of the output VCF file
        prefix (str): Prefix to use for contact names

    Returns:
        dict: Results dictionary with statistics and output file path
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    with open(input_path) as f:
        raw_numbers = f.read()

    return generate_vcf(raw_numbers, output_name, prefix)


def generate_vcf(raw_numbers: str, output_name: str = "contacts.vcf", prefix: str = "Contact"):
    """
    Generate a VCF file from a string containing phone numbers.

    Args:
        raw_numbers (str): Multi-line string containing phone numbers
        output_name (str): Name of the output VCF file
        prefix (str): Prefix to use for contact names

    Returns:
        dict: Results dictionary with statistics and output file path
    """
    lines = []
    for line in raw_numbers.strip().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            lines.append(line)

    total_numbers = len(lines)
    cleaned_numbers = set()
    duplicate_count = 0
    invalid_count = 0

    for num in lines:
        cleaned = clean_number(num)
        if cleaned:
            if cleaned in cleaned_numbers:
                duplicate_count += 1
            else:
                cleaned_numbers.add(cleaned)
        else:
            invalid_count += 1

    cleaned_numbers = sorted(cleaned_numbers)

    output_path = Path(output_name)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for idx, number in enumerate(cleaned_numbers, start=1):
            f.write("BEGIN:VCARD\n")
            f.write("VERSION:3.0\n")
            f.write(f"FN:{prefix} {idx}\n")
            f.write(f"TEL;TYPE=CELL:{number}\n")
            f.write("END:VCARD\n")

    return {
        "total": total_numbers,
        "valid": len(cleaned_numbers),
        "duplicates": duplicate_count,
        "invalid": invalid_count,
        "output_file": str(output_path),
    }


if __name__ == "__main__":
    sample_numbers = """
    0729553860
    0785952202
    0715132486
    """

    results = generate_vcf(sample_numbers, "sample_contacts.vcf", "Test Contact")
    print(f"Total numbers in array: {results['total']}")
    print(f"Numbers added to VCF: {results['valid']}")
    print(f"Numbers removed: {results['duplicates'] + results['invalid']}")
    print(f"- Duplicate numbers: {results['duplicates']}")
    print(f"- Invalid numbers: {results['invalid']}")
    print(f"Output file: {results['output_file']}")

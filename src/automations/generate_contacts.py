import re
from pathlib import Path

def clean_number(number):
    number = re.sub(r'\D', '', number)  # remove non-digits
    if number.startswith('0'):
        number = '+94' + number[1:]
    elif not number.startswith('+94'):
        number = '+94' + number
    return number if re.fullmatch(r'\+94\d{9}', number) else None

def generate_vcf_from_file(input_file: str, output_name: str = None, prefix: str = "Contact"):
    """
    Generate a VCF file from a text file containing phone numbers.
    
    Args:
        input_file (str): Path to text file containing phone numbers (one per line)
        output_name (str): Name of the output VCF file (optional, auto-generated if not provided)
        prefix (str): Prefix to use for contact names
    
    Returns:
        dict: Results dictionary with statistics and output file path
    """
    # Read numbers from file
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    with open(input_path, 'r') as f:
        raw_numbers = f.read()
    
    numbers = raw_numbers.strip().splitlines()
    total_numbers = len(numbers)
    cleaned_numbers = set()
    duplicate_count = 0
    invalid_count = 0

    for num in numbers:
        cleaned = clean_number(num)
        if cleaned:
            if cleaned in cleaned_numbers:
                duplicate_count += 1
            else:
                cleaned_numbers.add(cleaned)
        else:
            invalid_count += 1

    cleaned_numbers = sorted(cleaned_numbers)

    # Generate output filename if not provided
    if output_name is None:
        base_name = input_path.stem
        output_name = f"{base_name}_contacts.vcf"
    
    # Ensure output goes to phone_numbers directory
    if not output_name.startswith('data/phone_numbers/'):
        output_path = Path("data/phone_numbers") / output_name
    else:
        output_path = Path(output_name)
    
    # Create data directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate VCF file
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
        "output_file": str(output_path)
    }

def generate_vcf(raw_numbers: str, output_name: str = "contacts.vcf", prefix: str = "Contact"):
    """
    Legacy function for backward compatibility.
    Generate a VCF file from a string containing phone numbers.
    
    Args:
        raw_numbers (str): Multi-line string containing phone numbers
        output_name (str): Name of the output VCF file
        prefix (str): Prefix to use for contact names
    
    Returns:
        dict: Results dictionary with statistics and output file path
    """
    numbers = raw_numbers.strip().splitlines()
    total_numbers = len(numbers)
    cleaned_numbers = set()
    duplicate_count = 0
    invalid_count = 0

    for num in numbers:
        cleaned = clean_number(num)
        if cleaned:
            if cleaned in cleaned_numbers:
                duplicate_count += 1
            else:
                cleaned_numbers.add(cleaned)
        else:
            invalid_count += 1

    cleaned_numbers = sorted(cleaned_numbers)

    # Ensure output goes to phone_numbers directory
    if not output_name.startswith('data/phone_numbers/'):
        output_path = Path("data/phone_numbers") / output_name
    else:
        output_path = Path(output_name)
    
    # Create data directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate VCF file
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
        "output_file": str(output_path)
    }

if __name__ == "__main__":
    # Example usage
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

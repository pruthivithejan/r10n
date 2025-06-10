import argparse
from pathlib import Path
import importlib
import sys

def list_automations():
    """List all available automation scripts"""
    automations_dir = Path(__file__).parent / 'automations'
    automation_files = [f.stem for f in automations_dir.glob('*.py') 
                       if f.stem != '__init__' and not f.stem.startswith('_')]
    return automation_files

def main():
    parser = argparse.ArgumentParser(description='Run various automation tasks')
    subparsers = parser.add_subparsers(dest='automation', help='Available automations')

    # Generate Contacts Parser
    contacts_parser = subparsers.add_parser('generate_contacts', help='Generate VCF contact cards')
    contacts_parser.add_argument('input_file', type=str, help='File containing phone numbers (one per line)')
    contacts_parser.add_argument('--output', '-o', type=str, default='contacts.vcf', 
                               help='Output VCF file name')
    contacts_parser.add_argument('--prefix', '-p', type=str, default='Contact',
                               help='Prefix for contact names')

    # Add more automation parsers here as needed

    args = parser.parse_args()

    if not args.automation:
        print("Available automations:")
        for automation in list_automations():
            print(f"  - {automation}")
        sys.exit(1)

    try:
        # Import and run the selected automation
        if args.automation == 'generate_contacts':
            from automations.generate_contacts import generate_vcf
            
            # Read input file
            with open(args.input_file, 'r') as f:
                numbers = f.read()
            
            # Run the automation
            results = generate_vcf(numbers, args.output, args.prefix)
            
            # Print results
            print(f"Total numbers in array: {results['total']}")
            print(f"Numbers added to VCF: {results['valid']}")
            print(f"Numbers removed: {results['duplicates'] + results['invalid']}")
            print(f"- Duplicate numbers: {results['duplicates']}")
            print(f"- Invalid numbers: {results['invalid']}")
            print(f"Output file: {results['output_file']}")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()

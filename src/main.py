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
    contacts_parser = subparsers.add_parser('generate_contacts', help='Generate VCF contact cards from phone numbers')
    contacts_parser.add_argument('input_file', type=str, help='Text file containing phone numbers (one per line)')
    contacts_parser.add_argument('--output', '-o', type=str, default=None, 
                               help='Output VCF file name (default: auto-generated based on input filename)')
    contacts_parser.add_argument('--prefix', '-p', type=str, default='Contact',
                               help='Prefix for contact names (default: Contact)')

    # Send Bulk Emails Parser (with enhanced deliverability)
    emails_parser = subparsers.add_parser('send_bulk_emails', help='Send emails with enhanced deliverability features')
    emails_parser.add_argument('emails_file', type=str, help='Text file containing email addresses (one per line)')
    emails_parser.add_argument('subject', type=str, help='Email subject')
    emails_parser.add_argument('body_file', type=str, help='Text file containing email body')
    emails_parser.add_argument('--config', '-c', type=str, default='data/email_config_enhanced.json',
                              help='Enhanced email configuration JSON file')

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
            from automations.generate_contacts import generate_vcf_from_file
            
            # Run the automation using file input
            results = generate_vcf_from_file(args.input_file, args.output, args.prefix)
            
            # Print results
            print(f"Total numbers in input file: {results['total']}")
            print(f"Numbers added to VCF: {results['valid']}")
            print(f"Numbers removed: {results['duplicates'] + results['invalid']}")
            print(f"- Duplicate numbers: {results['duplicates']}")
            print(f"- Invalid numbers: {results['invalid']}")
            print(f"Output file: {results['output_file']}")
        
        elif args.automation == 'send_bulk_emails':
            from automations.send_enhanced_emails import send_same_email_enhanced
            
            # Run the enhanced email automation
            results = send_same_email_enhanced(args.emails_file, args.subject, args.body_file, args.config)
            
            if results['total'] == 0:
                sys.exit(1)

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()

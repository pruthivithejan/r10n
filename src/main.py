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
    contacts_parser.add_argument('--input', '-i', type=str, default='data/phone_numbers/numbers.txt',
                               help='Text file containing phone numbers (default: data/phone_numbers/numbers.txt)')
    contacts_parser.add_argument('--output', '-o', type=str, default=None, 
                               help='Output VCF file name (default: auto-generated in data/phone_numbers/)')
    contacts_parser.add_argument('--prefix', '-p', type=str, default='Contact',
                               help='Prefix for contact names (default: Contact)')

    # Send Bulk Emails Parser
    emails_parser = subparsers.add_parser('send_bulk_emails', help='Send the same email to multiple recipients')
    emails_parser.add_argument('--emails', '-e', type=str, default='data/emails/email_list.csv',
                              help='CSV file containing email addresses (default: data/emails/email_list.csv)')
    emails_parser.add_argument('--body', '-b', type=str, default='data/emails/email.txt',
                              help='Text file containing email body (default: data/emails/email.txt)')
    emails_parser.add_argument('--config', '-c', type=str, default='data/emails/email_config.json',
                              help='Email configuration JSON file (default: data/emails/email_config.json)')
    emails_parser.add_argument('--certificates', '-cert', type=str, default='data/certificates/output',
                              help='Directory containing certificate files (default: data/certificates/output)')

    # Send Outlook Emails with Attachments Parser
    outlook_parser = subparsers.add_parser('send_outlook_emails', help='Send personalized emails with individual attachments via Outlook')
    outlook_parser.add_argument('--recipients', '-r', type=str, default='data/outlook/recipients.txt',
                               help='CSV file with recipients and their certificate filenames (default: data/outlook/recipients.txt)')
    outlook_parser.add_argument('--body', '-b', type=str, default='data/outlook/email.txt',
                               help='Text file containing email body template (default: data/outlook/email.txt)')
    outlook_parser.add_argument('--config', '-c', type=str, default='data/outlook/email_config.json',
                               help='Email configuration JSON file (default: data/outlook/email_config.json)')
    outlook_parser.add_argument('--certificates', '-cert', type=str, default='data/outlook/certificates',
                               help='Directory containing certificate files (default: data/outlook/certificates)')

    # Fill Certificates Parser
    certs_parser = subparsers.add_parser('fill_certificates', help='Generate personalized certificates from PDF template')
    certs_parser.add_argument('--recipients', '-r', type=str, default='recipients.txt',
                             help='CSV file with recipient data (default: data/certificates/recipients.txt)')
    certs_parser.add_argument('--config', '-c', type=str, default='config.json',
                             help='Certificate configuration JSON file (default: data/certificates/config.json)')
    certs_parser.add_argument('--base-dir', '-d', type=str, default='data/certificates',
                             help='Base directory for certificate files (default: data/certificates)')

    # Generate Blog MDX Parser
    blog_parser = subparsers.add_parser('generate_blog_mdx', help='Generate well-structured MDX blog files with AI proofreading')
    blog_parser.add_argument('--input', '-i', type=str, required=True,
                           help='Input text file containing blog content')
    blog_parser.add_argument('--config', '-c', type=str, default='data/blog_config.json',
                           help='Blog configuration JSON file (default: data/blog_config.json)')
    blog_parser.add_argument('--title', '-t', type=str, default=None,
                           help='Override blog title')
    blog_parser.add_argument('--author', '-a', type=str, default=None,
                           help='Override blog author')
    blog_parser.add_argument('--tags', type=str, nargs='+', default=None,
                           help='Blog tags (space-separated)')
    blog_parser.add_argument('--description', '-d', type=str, default=None,
                           help='Blog description')

    # Optimize Images Parser
    images_parser = subparsers.add_parser('optimize_images', help='Optimize and rename images for web use')
    images_parser.add_argument('--input', '-i', type=str, required=True,
                             help='Input directory containing images')
    images_parser.add_argument('--output', '-o', type=str, default=None,
                             help='Output directory for optimized images (default: input_dir/optimized)')
    images_parser.add_argument('--prefix', '-p', type=str, default='img',
                             help='Prefix for renamed files (default: img)')
    images_parser.add_argument('--max-size', '-s', type=float, default=1.0,
                             help='Maximum file size in MB (default: 1.0)')
    images_parser.add_argument('--quality', '-q', type=int, default=85,
                             help='Image quality percentage (default: 85)')
    images_parser.add_argument('--max-width', type=int, default=1920,
                             help='Maximum image width (default: 1920)')
    images_parser.add_argument('--max-height', type=int, default=1080,
                             help='Maximum image height (default: 1080)')
    images_parser.add_argument('--config', '-c', type=str, default=None,
                             help='Image optimization configuration JSON file')
    images_parser.add_argument('--preserve-filename', action='store_true',
                             help='Preserve original filenames instead of using prefix+number naming')

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
            results = generate_vcf_from_file(args.input, args.output, args.prefix)
            
            # Print results
            print(f"Total numbers in input file: {results['total']}")
            print(f"Numbers added to VCF: {results['valid']}")
            print(f"Numbers removed: {results['duplicates'] + results['invalid']}")
            print(f"- Duplicate numbers: {results['duplicates']}")
            print(f"- Invalid numbers: {results['invalid']}")
            print(f"Output file: {results['output_file']}")
        
        elif args.automation == 'send_bulk_emails':
            from automations.send_same_email import send_from_file
            
            # Run the simple email automation
            results = send_from_file(args.emails, args.body, args.config, args.certificates)
            
            if results['total'] == 0:
                sys.exit(1)
        
        elif args.automation == 'send_outlook_emails':
            from automations.send_emails_outlook import send_from_file
            
            # Run the Outlook email automation with attachments
            results = send_from_file(args.recipients, args.body, args.config, args.certificates)
            
            print(f"\nCompleted: {results['sent']}/{results['total']} emails sent successfully")
            if results['failed'] > 0:
                print(f"Failed: {results['failed']} emails")
                sys.exit(1)
        
        elif args.automation == 'fill_certificates':
            from automations.fill_certificates import fill_certificates_from_file
            
            # Run the certificate filling automation
            results = fill_certificates_from_file(args.recipients, args.config, args.base_dir)
            
            print(f"\nCompleted: {results['generated']}/{results['total']} certificates generated successfully")
            if results['failed'] > 0:
                print(f"Failed: {results['failed']} certificates")
                sys.exit(1)
        
        elif args.automation == 'generate_blog_mdx':
            from automations.generate_blog_mdx import generate_blog_mdx
            
            # Run the blog MDX generation automation
            results = generate_blog_mdx(
                input_file=args.input,
                config_file=args.config,
                title=args.title,
                author=args.author,
                tags=args.tags,
                description=args.description
            )
            
            if results['success']:
                print(f"\n🎉 Blog MDX generated successfully!")
                print(f"📄 Title: {results['metadata']['title']}")
                print(f"👤 Author: {results['metadata']['author']}")
                print(f"📅 Date: {results['metadata']['date']}")
                print(f"🏷️  Tags: {', '.join(results['metadata']['tags'])}")
                print(f"📁 Output: {results['output_path']}")
            else:
                print(f"\n❌ Failed to generate blog MDX: {results['error']}")
                sys.exit(1)
        
        elif args.automation == 'optimize_images':
            from automations.optimize_images import optimize_images
            
            # Run the image optimization automation
            results = optimize_images(
                input_dir=args.input,
                output_dir=args.output,
                prefix=args.prefix,
                max_size_mb=args.max_size,
                quality=args.quality,
                max_width=args.max_width,
                max_height=args.max_height,
                preserve_filename=args.preserve_filename,
                config_file=args.config
            )
            
            if results.get('error'):
                print(f"\n❌ Image optimization failed: {results['error']}")
                sys.exit(1)
            elif results['processed'] == 0 and results['skipped'] == 0:
                print(f"\n⚠️  No images were processed")
                sys.exit(1)
            else:
                print(f"\n🎉 Image optimization completed!")
                print(f"✅ Processed: {results['processed']} images")
                if results['skipped'] > 0:
                    print(f"⏭️  Skipped: {results['skipped']} images")
                if results['failed'] > 0:
                    print(f"❌ Failed: {results['failed']} images")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Cloudinary Logs Analyzer
Analyzes worker logs from the cloudinary-logs S3 bucket
"""

import argparse
import gzip
import subprocess
import sys
import os
import re
from datetime import datetime
from collections import Counter
from typing import Dict, List, Tuple


BUCKET_NAME = "cloudinary-logs"
AWS_PROFILE = "production-readonly"
AWS_REGION = "us-east-1"
LOG_DIR = "/tmp/cloudinary-logs"


def run_aws_command(command: List[str]) -> str:
    """Run an AWS CLI command with the production profile"""
    cmd = ["aws"] + command + ["--profile", AWS_PROFILE, "--region", AWS_REGION]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running AWS command: {e.stderr}", file=sys.stderr)
        sys.exit(1)


def list_services() -> List[str]:
    """List all available services/systems in the bucket"""
    output = run_aws_command(["s3", "ls", f"s3://{BUCKET_NAME}/"])
    services = []
    for line in output.strip().split('\n'):
        if 'PRE' in line:
            service = line.split()[-1].rstrip('/')
            services.append(service)
    return sorted(services)


def list_dates(service: str) -> List[str]:
    """List all available dates for a service"""
    output = run_aws_command(["s3", "ls", f"s3://{BUCKET_NAME}/{service}/"])
    dates = []
    for line in output.strip().split('\n'):
        if 'PRE' in line:
            date = line.split()[-1].rstrip('/')
            dates.append(date)
    return sorted(dates)


def list_instances(service: str, date: str) -> List[str]:
    """List all instances for a service on a specific date"""
    output = run_aws_command(["s3", "ls", f"s3://{BUCKET_NAME}/{service}/{date}/"])
    instances = []
    for line in output.strip().split('\n'):
        if 'PRE' in line:
            instance = line.split()[-1].rstrip('/')
            instances.append(instance)
    return sorted(instances)


def list_files(service: str, date: str, instance: str) -> List[Tuple[str, str, str]]:
    """List all log files for an instance. Returns [(filename, size, date), ...]"""
    output = run_aws_command(["s3", "ls", f"s3://{BUCKET_NAME}/{service}/{date}/{instance}/"])
    files = []
    for line in output.strip().split('\n'):
        if line.strip():
            parts = line.split()
            if len(parts) >= 4:
                date_str = parts[0]
                time_str = parts[1]
                size = parts[2]
                filename = ' '.join(parts[3:])
                files.append((filename, size, f"{date_str} {time_str}"))
    return files


def download_file(service: str, date: str, instance: str, filename: str, output_path: str = None):
    """Download a specific log file from S3"""
    s3_path = f"s3://{BUCKET_NAME}/{service}/{date}/{instance}/{filename}"
    if output_path:
        local_path = output_path
    else:
        dest_dir = os.path.join(LOG_DIR, service, date, instance)
        os.makedirs(dest_dir, exist_ok=True)
        local_path = os.path.join(dest_dir, filename)

    print(f"Downloading {filename}...")
    cmd = ["s3", "cp", s3_path, local_path]
    run_aws_command(cmd)
    print(f"Downloaded to {local_path}")
    return local_path


def decompress_file(filepath: str) -> str:
    """Decompress a .gz file if needed"""
    if filepath.endswith('.gz'):
        output_path = filepath[:-3]  # Remove .gz extension
        print(f"Decompressing {filepath}...")
        with gzip.open(filepath, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                f_out.write(f_in.read())
        print(f"Decompressed to {output_path}")
        return output_path
    return filepath


def analyze_log_file(filepath: str) -> Dict:
    """Analyze a single log file and return statistics"""
    print(f"\nAnalyzing {filepath}...")

    stats = {
        'total_lines': 0,
        'errors': 0,
        'warnings': 0,
        'info': 0,
        'error_messages': [],
        'warning_patterns': Counter(),
        'hourly_breakdown': Counter(),
    }

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                stats['total_lines'] += 1

                # Count log levels
                if '[ERROR]' in line:
                    stats['errors'] += 1
                    # Store first 20 error messages
                    if len(stats['error_messages']) < 20:
                        stats['error_messages'].append(line.strip()[:500])
                elif '[WARN]' in line:
                    stats['warnings'] += 1
                    # Extract warning pattern
                    match = re.search(r'\[WARN\].*?(?:\{|$)', line)
                    if match:
                        pattern = match.group(0)[:100]
                        stats['warning_patterns'][pattern] += 1
                elif '[INFO]' in line:
                    stats['info'] += 1

                # Extract hour for hourly breakdown
                time_match = re.search(r'2026-\d{2}-\d{2}T(\d{2}):', line)
                if time_match:
                    hour = time_match.group(1)
                    stats['hourly_breakdown'][hour] += 1

    except Exception as e:
        print(f"Error analyzing file: {e}", file=sys.stderr)
        return stats

    return stats


def print_analysis(stats: Dict, filename: str):
    """Print formatted analysis results"""
    print(f"\n{'='*80}")
    print(f"ANALYSIS RESULTS: {filename}")
    print(f"{'='*80}\n")

    print(f"Total log lines: {stats['total_lines']:,}")
    print(f"Errors: {stats['errors']:,} ({stats['errors']/stats['total_lines']*100:.4f}%)")
    print(f"Warnings: {stats['warnings']:,} ({stats['warnings']/stats['total_lines']*100:.2f}%)")
    print(f"Info: {stats['info']:,} ({stats['info']/stats['total_lines']*100:.2f}%)")

    if stats['hourly_breakdown']:
        print(f"\n--- Hourly Breakdown ---")
        for hour in sorted(stats['hourly_breakdown'].keys()):
            count = stats['hourly_breakdown'][hour]
            print(f"Hour {hour}: {count:,} lines")

    if stats['error_messages']:
        print(f"\n--- Top Error Messages (first {len(stats['error_messages'])}) ---")
        for i, error in enumerate(stats['error_messages'][:10], 1):
            print(f"\n{i}. {error[:200]}...")

    if stats['warning_patterns']:
        print(f"\n--- Top Warning Patterns ---")
        for pattern, count in stats['warning_patterns'].most_common(10):
            print(f"{count:>6}x  {pattern}")

    print(f"\n{'='*80}\n")


def analyze_production_logs(service: str, date: str, instance: str, hours: List[str] = None):
    """Download and analyze production logs for specific hours"""
    if hours is None:
        # Default to all available hours
        files = list_files(service, date, instance)
        production_files = [f[0] for f in files if f[0].startswith('production.') and f[0].endswith('.log.gz')]
        hours = []
        for pf in production_files:
            match = re.search(r'production\.\d{8}-(\d{2})\.log\.gz', pf)
            if match:
                hours.append(match.group(1))

    all_stats = {
        'total_lines': 0,
        'errors': 0,
        'warnings': 0,
        'info': 0,
        'error_messages': [],
        'warning_patterns': Counter(),
        'hourly_breakdown': Counter(),
    }

    for hour in hours:
        filename = f"production.{date}-{hour}.log.gz"
        print(f"\n{'='*80}")
        print(f"Processing hour {hour}")
        print(f"{'='*80}")

        # Download
        local_path = download_file(service, date, instance, filename)

        # Decompress
        decompressed_path = decompress_file(local_path)

        # Analyze
        stats = analyze_log_file(decompressed_path)

        # Aggregate stats
        all_stats['total_lines'] += stats['total_lines']
        all_stats['errors'] += stats['errors']
        all_stats['warnings'] += stats['warnings']
        all_stats['info'] += stats['info']
        all_stats['error_messages'].extend(stats['error_messages'])
        all_stats['warning_patterns'].update(stats['warning_patterns'])
        all_stats['hourly_breakdown'].update(stats['hourly_breakdown'])

    # Print aggregate analysis
    print_analysis(all_stats, f"{service}/{date}/{instance} - All Hours")


def main():
    parser = argparse.ArgumentParser(description='Analyze Cloudinary worker logs from S3')

    # Actions
    parser.add_argument('--list-services', action='store_true', help='List all available services')
    parser.add_argument('--list-dates', action='store_true', help='List dates for a service')
    parser.add_argument('--list-instances', action='store_true', help='List instances for a service on a date')
    parser.add_argument('--list-files', action='store_true', help='List files for an instance')
    parser.add_argument('--download', metavar='FILENAME', help='Download a specific file')
    parser.add_argument('--analyze', action='store_true', help='Analyze logs')
    parser.add_argument('--analyze-production', action='store_true', help='Download and analyze production logs')

    # Parameters
    parser.add_argument('--service', help='Service name (e.g., rails)')
    parser.add_argument('--date', help='Date in YYYYMMDD format (e.g., 20260223)')
    parser.add_argument('--instance', help='Instance ID (e.g., i-0b6bc08c6df232bf4)')
    parser.add_argument('--local-file', help='Local file to analyze')
    parser.add_argument('--hours', nargs='+', help='Specific hours to analyze (e.g., 14 15 16)')
    parser.add_argument('--log-type', default='production', help='Log type (default: production)')

    args = parser.parse_args()

    # List services
    if args.list_services:
        services = list_services()
        print("\nAvailable services:")
        for service in services:
            print(f"  - {service}")
        return

    # List dates
    if args.list_dates:
        if not args.service:
            print("Error: --service required", file=sys.stderr)
            sys.exit(1)
        dates = list_dates(args.service)
        print(f"\nAvailable dates for {args.service}:")
        for date in dates[-20:]:  # Show last 20 dates
            print(f"  - {date}")
        return

    # List instances
    if args.list_instances:
        if not args.service or not args.date:
            print("Error: --service and --date required", file=sys.stderr)
            sys.exit(1)
        instances = list_instances(args.service, args.date)
        print(f"\nInstances for {args.service} on {args.date}:")
        for instance in instances:
            print(f"  - {instance}")
        return

    # List files
    if args.list_files:
        if not args.service or not args.date or not args.instance:
            print("Error: --service, --date, and --instance required", file=sys.stderr)
            sys.exit(1)
        files = list_files(args.service, args.date, args.instance)
        print(f"\nLog files for {args.instance}:")
        for filename, size, date in files:
            print(f"  {date:20} {size:>12}  {filename}")
        return

    # Download file
    if args.download:
        if not args.service or not args.date or not args.instance:
            print("Error: --service, --date, and --instance required", file=sys.stderr)
            sys.exit(1)
        download_file(args.service, args.date, args.instance, args.download)
        return

    # Analyze production logs
    if args.analyze_production:
        if not args.service or not args.date or not args.instance:
            print("Error: --service, --date, and --instance required", file=sys.stderr)
            sys.exit(1)
        analyze_production_logs(args.service, args.date, args.instance, args.hours)
        return

    # Analyze local file
    if args.analyze:
        if args.local_file:
            # Decompress if needed
            filepath = decompress_file(args.local_file) if args.local_file.endswith('.gz') else args.local_file
            stats = analyze_log_file(filepath)
            print_analysis(stats, args.local_file)
        else:
            print("Error: --local-file required for --analyze", file=sys.stderr)
            sys.exit(1)
        return

    # No action specified
    parser.print_help()


if __name__ == '__main__':
    main()

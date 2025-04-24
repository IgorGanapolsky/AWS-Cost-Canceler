#!/usr/bin/env python3
"""
Command-line interface for Nova Cost - AWS Cost Analysis Tool
"""
import argparse
import sys
from typing import List, Optional

from nova_cost.api import generate_report, analyze_costs


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the AWS Cost Analysis CLI.
    """
    parser = argparse.ArgumentParser(description="AWS Cost Analysis Tool")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate cost report")
    report_parser.add_argument("--days", type=int, default=30, help="Days of data to analyze")
    report_parser.add_argument("--output", help="Output file path for the report")
    report_parser.add_argument("--open", action="store_true", help="Open the report after generation")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze costs")
    analyze_parser.add_argument("--threshold", type=float, default=10.0, help="Cost threshold")
    analyze_parser.add_argument("--days", type=int, default=30, help="Days of data to analyze")
    
    args = parser.parse_args(argv)
    
    if args.command == "report":
        report_path = generate_report(
            days_back=args.days,
            output_path=args.output,
            open_report=args.open
        )
        print(f"Report generated: {report_path}")
        return 0
    elif args.command == "analyze":
        result = analyze_costs(threshold=args.threshold, days_back=args.days)
        return 0 if result else 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

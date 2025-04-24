#!/usr/bin/env python3
"""
AWS Cost Report Handler - Processes action requests from the HTML report.
"""

import sys
import os
import argparse
from urllib.parse import parse_qs, urlparse
import webbrowser
from pathlib import Path

# Add parent directory to path so we can import aws_master_controller
sys.path.append(str(Path(__file__).resolve().parent.parent))
from aws_master_controller import AWSMasterController

def parse_url_params(url):
    """Parse URL parameters."""
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    return params

def handle_cancel_all():
    """Handle cancel_all action by calling the AWS Master Controller."""
    print("Initializing AWS Master Controller to cancel all services...")
    controller = AWSMasterController()
    controller.cancel_all_services()
    print("\nAll services have been canceled or scheduled for deletion.")
    print("You may close this window and check the AWS Console for confirmation.")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="AWS Cost Report Handler")
    parser.add_argument("url", help="URL with parameters to process")
    args = parser.parse_args()
    
    params = parse_url_params(args.url)
    
    if params.get('cancel_all', ['false'])[0].lower() in ('true', '1', 'yes'):
        handle_cancel_all()

if __name__ == "__main__":
    main()

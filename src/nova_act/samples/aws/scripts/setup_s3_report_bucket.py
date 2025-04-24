#!/usr/bin/env python3
"""
S3 Report Bucket Setup Script

This script uses the Nova Act browser automation tool to:
1. Log into the AWS console
2. Create an S3 bucket for hosting AWS cost reports
3. Configure the bucket with appropriate public read permissions
4. Update the .env file with the bucket name

Usage:
    python setup_s3_report_bucket.py --bucket_name="my-reports-bucket" [--region="us-east-1"]
"""

import os
import sys
import re
import time
import random
import string
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from nova_act import NovaAct

# Load environment variables
dotenv_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path)

# Get AWS credentials from environment variables
AWS_ACCOUNT = os.getenv('AWS_ACCOUNT')
AWS_PASSWORD = os.getenv('AWS_PASSWORD')


def generate_bucket_name(base_name=None):
    """Generate a unique S3 bucket name with a timestamp and random suffix."""
    # Use provided base name or default to 'aws-cost-reports'
    if not base_name:
        base_name = 'aws-cost-reports'
    
    # Clean the base name to conform to S3 bucket naming rules
    base_name = re.sub(r'[^a-z0-9-]', '-', base_name.lower())
    
    # Add timestamp and random suffix for uniqueness
    timestamp = datetime.now().strftime('%Y%m%d')
    rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    
    # Combine to create unique bucket name (limited to 63 characters)
    bucket_name = f"{base_name}-{timestamp}-{rand_suffix}"
    return bucket_name[:63]


def update_env_file(bucket_name):
    """Update the .env file with the S3 bucket name."""
    env_path = Path(__file__).parent / '.env'
    
    if not env_path.exists():
        print(f"Error: .env file not found at {env_path}")
        return False
    
    # Read the current content
    with open(env_path, 'r') as f:
        content = f.read()
    
    # Check if AWS_REPORT_BUCKET already exists
    if 'AWS_REPORT_BUCKET=' in content:
        # Replace the existing value
        content = re.sub(
            r'AWS_REPORT_BUCKET=.*',
            f'AWS_REPORT_BUCKET={bucket_name}  # S3 bucket for hosting cost reports',
            content
        )
    else:
        # Add the new variable
        content += f'\n# S3 bucket for hosting cost reports\nAWS_REPORT_BUCKET={bucket_name}\n'
    
    # Write the updated content
    with open(env_path, 'w') as f:
        f.write(content)
    
    print(f"Updated .env file with bucket name: {bucket_name}")
    return True


def setup_s3_bucket(bucket_name=None, region="us-east-1"):
    """Set up an S3 bucket for AWS cost reports using Nova Act."""
    if not bucket_name:
        bucket_name = generate_bucket_name()
    
    print(f"Setting up S3 bucket: {bucket_name} in region {region}")
    
    # Initialize Nova Act
    print("Starting browser automation with Nova Act...")
    n = NovaAct(starting_page="https://console.aws.amazon.com/console/home")
    
    try:
        # Start the browser
        n.start()
        print("Browser started successfully")
        
        # Log in to AWS Console
        print("Logging into AWS Console...")
        n.act("Input my AWS account email")
        time.sleep(1)
        n.act(f"Type {AWS_ACCOUNT}")
        time.sleep(1)
        n.act("Click Next")
        time.sleep(2)
        n.act("Input my AWS password")
        time.sleep(1)
        n.act(f"Type {AWS_PASSWORD}")
        time.sleep(1)
        n.act("Click Sign in")
        time.sleep(5)
        
        # Navigate to S3
        print("Navigating to S3 service...")
        n.act("Search for S3 in the AWS console search bar")
        time.sleep(2)
        n.act("Click on S3 in the search results")
        time.sleep(5)
        
        # Create a new bucket
        print(f"Creating new bucket: {bucket_name}...")
        n.act("Click Create bucket")
        time.sleep(2)
        n.act(f"Type {bucket_name} in the bucket name field")
        time.sleep(1)
        
        # Set region
        n.act(f"Select {region} as the AWS Region")
        time.sleep(1)
        
        # Configure bucket settings for report hosting
        n.act("Scroll down to 'Block Public Access settings for this bucket'")
        time.sleep(1)
        n.act("Uncheck 'Block all public access' to allow public read of reports")
        time.sleep(1)
        n.act("Check the acknowledgment checkbox for public access")
        time.sleep(1)
        
        # Complete bucket creation
        n.act("Scroll to the bottom and click Create bucket")
        time.sleep(5)
        
        # Verify bucket creation
        n.act(f"Search for {bucket_name} in the bucket list")
        time.sleep(3)
        
        # Configure bucket for static website hosting
        print("Configuring bucket for static website hosting...")
        n.act(f"Click on the bucket named {bucket_name}")
        time.sleep(2)
        n.act("Click on the Properties tab")
        time.sleep(2)
        n.act("Scroll down to Static website hosting")
        time.sleep(1)
        n.act("Click Edit")
        time.sleep(1)
        n.act("Select 'Enable' for Static website hosting")
        time.sleep(1)
        n.act("Type index.html for both the index and error document")
        time.sleep(1)
        n.act("Click Save changes")
        time.sleep(3)
        
        # Set bucket policy for public read
        print("Setting bucket policy for public read access...")
        n.act("Go to the Permissions tab")
        time.sleep(2)
        n.act("Scroll down to Bucket policy and click Edit")
        time.sleep(2)
        
        bucket_policy = """
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": "arn:aws:s3:::%s/*"
                }
            ]
        }
        """ % bucket_name
        
        n.act(f"In the policy editor, type or paste the following policy: {bucket_policy}")
        time.sleep(2)
        n.act("Click Save changes")
        time.sleep(3)
        
        # Get the website endpoint
        n.act("Go back to the Properties tab")
        time.sleep(2)
        n.act("Scroll down to Static website hosting")
        time.sleep(1)
        n.act("Copy the bucket website endpoint")
        
        # The endpoint follows the format: http://bucket-name.s3-website-region.amazonaws.com
        bucket_endpoint = f"http://{bucket_name}.s3-website-{region}.amazonaws.com"
        print(f"Bucket website endpoint: {bucket_endpoint}")
        
        # Success
        print(f"S3 bucket '{bucket_name}' created successfully")
        print(f"Reports will be accessible at: {bucket_endpoint}/cost_reports/")
        
        # Update .env file
        update_env_file(bucket_name)
        
        return {
            "success": True,
            "bucket_name": bucket_name,
            "region": region,
            "endpoint": bucket_endpoint
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
    finally:
        # Clean up
        try:
            n.stop()
            print("Browser closed")
        except:
            pass


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Set up S3 bucket for AWS cost reports")
    
    parser.add_argument(
        "--bucket_name",
        type=str,
        default=None,
        help="Name for the S3 bucket (default: auto-generated)"
    )
    
    parser.add_argument(
        "--region",
        type=str,
        default="us-east-1",
        help="AWS region for the bucket (default: us-east-1)"
    )
    
    return parser.parse_args()


def main():
    """Main function to run the script."""
    args = parse_arguments()
    
    result = setup_s3_bucket(
        bucket_name=args.bucket_name,
        region=args.region
    )
    
    if result["success"]:
        print("\nS3 bucket setup completed successfully!")
        print(f"Bucket name: {result['bucket_name']}")
        print(f"Region: {result['region']}")
        print(f"Website endpoint: {result['endpoint']}")
        print("\nYour .env file has been updated with the bucket name.")
        print("You can now use the aws_master_controller.py script with --upload_to_s3=True")
    else:
        print("\nS3 bucket setup failed.")
        print(f"Error: {result.get('error', 'Unknown error')}")
        print("\nPlease try again or set up the bucket manually.")


if __name__ == "__main__":
    main()

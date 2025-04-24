#!/usr/bin/env python3
"""
S3 Report Hosting for AWS Cost Monitor

This module handles uploading HTML reports to S3 and generating
shareable URLs with auto-expiration after 7 days.
"""

import os
import uuid
import boto3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional


class S3ReportHosting:
    """Host HTML reports on S3 with auto-expiration."""
    
    def __init__(self, bucket_name: Optional[str] = None, region: str = 'us-east-1'):
        """Initialize the S3 report hosting.
        
        Args:
            bucket_name: The name of the S3 bucket to use (if None, a bucket will be created)
            region: The AWS region to use
        """
        self.region = region
        self.bucket_name = bucket_name
        
        # Create boto3 session using the default credentials
        self.session = boto3.Session()
        self.s3 = self.session.client('s3', region_name=region)
        
        # Ensure the bucket exists
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the S3 bucket exists, creating it if necessary."""
        if not self.bucket_name:
            # Generate a unique bucket name if none provided
            account_id = self._get_account_id()
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            self.bucket_name = f"aws-cost-reports-{account_id}-{timestamp}"
        
        # Check if the bucket exists
        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
            print(f"Using existing S3 bucket: {self.bucket_name}")
        except Exception:
            # Bucket doesn't exist, create it
            try:
                if self.region == 'us-east-1':
                    # Special case for us-east-1
                    self.s3.create_bucket(Bucket=self.bucket_name)
                else:
                    # For other regions
                    self.s3.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
                
                print(f"Created new S3 bucket: {self.bucket_name}")
                
                # Set up lifecycle policy for auto-expiration
                self._set_lifecycle_policy()
                
                # Set up bucket policy for public read access
                self._set_bucket_policy()
                
                # Enable website hosting
                self._enable_website_hosting()
                
            except Exception as e:
                print(f"Error creating S3 bucket: {str(e)}")
                raise
    
    def _get_account_id(self) -> str:
        """Get the AWS account ID."""
        sts = self.session.client('sts')
        return sts.get_caller_identity()["Account"]
    
    def _set_lifecycle_policy(self):
        """Set up a lifecycle policy to expire objects after 7 days."""
        lifecycle_config = {
            'Rules': [
                {
                    'ID': 'ExpireAfter7Days',
                    'Status': 'Enabled',
                    'Prefix': '',
                    'Expiration': {
                        'Days': 7
                    }
                }
            ]
        }
        
        self.s3.put_bucket_lifecycle_configuration(
            Bucket=self.bucket_name,
            LifecycleConfiguration=lifecycle_config
        )
        
        print(f"Set lifecycle policy to expire objects after 7 days")
    
    def _set_bucket_policy(self):
        """Set up a bucket policy to allow public read access."""
        bucket_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Sid': 'PublicReadGetObject',
                    'Effect': 'Allow',
                    'Principal': '*',
                    'Action': 's3:GetObject',
                    'Resource': f'arn:aws:s3:::{self.bucket_name}/*'
                }
            ]
        }
        
        # Convert the policy to JSON
        import json
        bucket_policy_json = json.dumps(bucket_policy)
        
        # Set the bucket policy
        self.s3.put_bucket_policy(
            Bucket=self.bucket_name,
            Policy=bucket_policy_json
        )
        
        print(f"Set bucket policy to allow public read access")
    
    def _enable_website_hosting(self):
        """Enable website hosting for the bucket."""
        website_config = {
            'ErrorDocument': {
                'Key': 'error.html'
            },
            'IndexDocument': {
                'Suffix': 'index.html'
            }
        }
        
        self.s3.put_bucket_website(
            Bucket=self.bucket_name,
            WebsiteConfiguration=website_config
        )
        
        print(f"Enabled website hosting for bucket")
    
    def upload_report(self, html_path: str, report_id: Optional[str] = None) -> Dict[str, Any]:
        """Upload an HTML report to S3.
        
        Args:
            html_path: The path to the HTML report file
            report_id: Optional report ID (if None, a UUID will be generated)
        
        Returns:
            Dict containing the report URL and expiration date
        """
        # Generate a report ID if none provided
        if not report_id:
            report_id = str(uuid.uuid4())
        
        # Generate the S3 key
        timestamp = datetime.now().strftime("%Y%m%d")
        s3_key = f"reports/{timestamp}/{report_id}/index.html"
        
        # Upload the HTML file
        with open(html_path, 'rb') as f:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=f.read(),
                ContentType='text/html'
            )
        
        # Generate the URL
        if self.region == 'us-east-1':
            url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
            website_url = f"http://{self.bucket_name}.s3-website-{self.region}.amazonaws.com/reports/{timestamp}/{report_id}/"
        else:
            url = f"https://{self.bucket_name}.s3-{self.region}.amazonaws.com/{s3_key}"
            website_url = f"http://{self.bucket_name}.s3-website-{self.region}.amazonaws.com/reports/{timestamp}/{report_id}/"
        
        # Calculate expiration date (7 days from now)
        expiration_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        return {
            "report_id": report_id,
            "s3_key": s3_key,
            "url": url,
            "website_url": website_url,
            "expiration_date": expiration_date,
            "bucket": self.bucket_name
        }
    
    def generate_presigned_url(self, s3_key: str, expiration_seconds: int = 604800) -> str:
        """Generate a presigned URL for an S3 object.
        
        Args:
            s3_key: The S3 key of the object
            expiration_seconds: The number of seconds until the URL expires (default: 7 days)
        
        Returns:
            str: The presigned URL
        """
        url = self.s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.bucket_name,
                'Key': s3_key
            },
            ExpiresIn=expiration_seconds
        )
        
        return url


# Example usage
if __name__ == "__main__":
    # Create a sample HTML file
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sample Report</title>
    </head>
    <body>
        <h1>Sample AWS Cost Report</h1>
        <p>This is a sample report.</p>
    </body>
    </html>
    """
    
    sample_path = "sample_report.html"
    with open(sample_path, 'w') as f:
        f.write(sample_html)
    
    # Upload the report
    hosting = S3ReportHosting()
    result = hosting.upload_report(sample_path)
    
    print(f"Report uploaded to S3:")
    print(f"  URL: {result['url']}")
    print(f"  Website URL: {result['website_url']}")
    print(f"  Expiration Date: {result['expiration_date']}")
    
    # Generate a presigned URL
    presigned_url = hosting.generate_presigned_url(result['s3_key'])
    print(f"  Presigned URL: {presigned_url}")

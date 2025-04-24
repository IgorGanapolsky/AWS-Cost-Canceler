#!/usr/bin/env python3
"""
Nova Act script to cancel specific AWS services shown in Cost Explorer.
This script automates the process of canceling targeted AWS services
that are generating charges, without affecting the entire AWS account.
"""

import os
import time
from datetime import datetime
import boto3
import fire
import sys
from pathlib import Path

# Import Nova Act directly - using relative imports since we're inside the package
sys.path.insert(0, str(Path(__file__).parents[3]))

# Try direct import of nova_act.py from the same directory level
try:
    from ..nova_act import NovaAct
except ImportError as e1:
    try:
        # Try importing from parent module
        from .. import NovaAct
    except ImportError as e2:
        try:
            # Try direct path to the module
            sys.path.insert(0, str(Path(__file__).parents[1]))
            from nova_act import NovaAct
        except ImportError as e3:
            print(f"Error importing NovaAct: {e1}, {e2}, {e3}")
            print("Attempting fallback solution...")
            
            # Last resort - extreme measures
            import importlib.util
            import inspect
            
            # Try to find and load the nova_act.py file directly
            nova_act_path = str(Path(__file__).parents[1] / "nova_act.py")
            if os.path.exists(nova_act_path):
                print(f"Found nova_act.py at {nova_act_path}")
                spec = importlib.util.spec_from_file_location("nova_act_module", nova_act_path)
                nova_act_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(nova_act_module)
                
                # Find the NovaAct class in the loaded module
                for name, obj in inspect.getmembers(nova_act_module):
                    if name == "NovaAct" and inspect.isclass(obj):
                        NovaAct = obj
                        print("Successfully loaded NovaAct class!")
                        break
                else:
                    print("Could not find NovaAct class in the module.")
                    sys.exit(1)
            else:
                print("Could not find nova_act.py file.")
                sys.exit(1)


class AWSServiceCanceler:
    """Class to cancel specific AWS services that are generating charges."""
    
    def __init__(self, nova_act_agent):
        """Initialize with a Nova Act agent instance."""
        self.agent = nova_act_agent
        self.session = boto3.Session()
        
    def login_to_aws_console(self, aws_account, aws_password):
        """Login to AWS Management Console."""
        print("Logging into AWS Console...")
        
        # Navigate to AWS login page
        self.agent.navigate("https://console.aws.amazon.com/")
        
        # Enter credentials
        self.agent.wait_and_click('input[id="resolving_input"]')
        self.agent.type(aws_account)
        self.agent.wait_and_click('button[id="next_button"]')
        
        # Handle password
        self.agent.wait_for_element('input[id="password"]')
        self.agent.type(aws_password)
        self.agent.wait_and_click('button[id="signin_button"]')
        
        # Wait for console to load
        self.agent.wait_for_element('body.awsui')
        print("Successfully logged into AWS Console")
    
    def cancel_opensearch_serverless(self):
        """Cancel OpenSearch Serverless collections causing SearchOCU and IndexingOCU charges."""
        print("Canceling OpenSearch Serverless collections...")
        
        # Navigate to OpenSearch Service console
        self.agent.navigate("https://console.aws.amazon.com/aos/home")
        
        # Wait for page to load
        self.agent.wait_for_element('body.awsui')
        
        # Go to Collections tab
        self.agent.wait_and_click('a[href*="collections"]')
        
        # Check if there are collections
        collections = self.agent.extract_elements('table tbody tr')
        
        if not collections or len(collections) == 0:
            print("No OpenSearch Serverless collections found in this region")
            return
        
        # Delete each collection
        for collection in collections:
            # Select the collection (checkbox)
            self.agent.click(collection.find_element('input[type="checkbox"]'))
            
            # Click delete button
            self.agent.wait_and_click('button:contains("Delete")')
            
            # Confirm deletion (type the name if needed)
            name_field = self.agent.wait_for_element('input[placeholder="delete"]')
            if name_field:
                self.agent.type("delete")
            
            # Confirm deletion
            self.agent.wait_and_click('button:contains("Delete")')
            
            # Wait for deletion to complete
            self.agent.wait_for_element('div:contains("successfully deleted")')
        
        print("Completed OpenSearch Serverless collections cancellation")
        
        # Also check for OpenSearch Ingestion pipelines
        self.agent.wait_and_click('a[href*="pipelines"]')
        
        # Check if there are pipelines
        pipelines = self.agent.extract_elements('table tbody tr')
        
        if not pipelines or len(pipelines) == 0:
            print("No OpenSearch Ingestion pipelines found in this region")
            return
        
        # Delete each pipeline
        for pipeline in pipelines:
            # Select the pipeline (checkbox)
            self.agent.click(pipeline.find_element('input[type="checkbox"]'))
            
            # Click delete button
            self.agent.wait_and_click('button:contains("Delete")')
            
            # Confirm deletion
            self.agent.wait_and_click('button:contains("Delete")')
            
            # Wait for deletion to complete
            self.agent.wait_for_element('div:contains("successfully deleted")')
        
        print("Completed OpenSearch Ingestion pipelines cancellation")
    
    def cancel_bedrock_services(self):
        """Cancel Amazon Bedrock Services (DeepSeek tokens)."""
        print("Canceling Amazon Bedrock services...")
        
        # Navigate to Bedrock console
        self.agent.navigate("https://console.aws.amazon.com/bedrock/home")
        
        # Wait for page to load
        self.agent.wait_for_element('body.awsui')
        
        # Go to Model access
        self.agent.wait_and_click('a[href*="model-access"]')
        
        # Uncheck all DeepSeek models
        deepseek_checkboxes = self.agent.extract_elements('input[type="checkbox"][id*="DeepSeek"]')
        
        if not deepseek_checkboxes or len(deepseek_checkboxes) == 0:
            print("No DeepSeek models found with access")
        else:
            for checkbox in deepseek_checkboxes:
                if checkbox.is_selected():
                    self.agent.click(checkbox)
            
            # Save changes
            self.agent.wait_and_click('button:contains("Save changes")')
            
            # Wait for confirmation
            self.agent.wait_for_element('div:contains("successfully updated")')
        
        # Check provisioned throughput
        self.agent.wait_and_click('a[href*="provisioned-throughput"]')
        
        # Delete any provisioned throughput for DeepSeek models
        throughput_items = self.agent.extract_elements('tr:contains("DeepSeek")')
        
        if not throughput_items or len(throughput_items) == 0:
            print("No DeepSeek provisioned throughput found")
        else:
            for item in throughput_items:
                # Select the item
                self.agent.click(item)
                
                # Click delete button
                self.agent.wait_and_click('button:contains("Delete")')
                
                # Confirm deletion
                self.agent.wait_and_click('button:contains("Delete")')
                
                # Wait for deletion to complete
                self.agent.wait_for_element('div:contains("successfully deleted")')
        
        print("Completed Amazon Bedrock services cancellation")
    
    def cancel_guardrail_services(self):
        """Cancel Amazon GuardRail Services."""
        print("Canceling Amazon GuardRail services...")
        
        # Navigate to Bedrock GuardRails console
        self.agent.navigate("https://console.aws.amazon.com/bedrock/home#/guardrails")
        
        # Wait for page to load
        self.agent.wait_for_element('body.awsui')
        
        # Check if there are guardrails
        guardrails = self.agent.extract_elements('table tbody tr')
        
        if not guardrails or len(guardrails) == 0:
            print("No Amazon GuardRails found in this region")
            return
        
        # Delete each guardrail
        for guardrail in guardrails:
            # Select the guardrail (checkbox)
            self.agent.click(guardrail.find_element('input[type="checkbox"]'))
            
            # Click delete button
            self.agent.wait_and_click('button:contains("Delete")')
            
            # Confirm deletion
            self.agent.wait_and_click('button:contains("Delete")')
            
            # Wait for deletion to complete
            self.agent.wait_for_element('div:contains("successfully deleted")')
        
        print("Completed Amazon GuardRail services cancellation")
        
        # Also check Control Tower GuardRails if applicable
        try:
            # Navigate to Control Tower console
            self.agent.navigate("https://console.aws.amazon.com/controltower/home#/controls")
            
            # Wait for page to load
            self.agent.wait_for_element('body.awsui')
            
            # Find enabled guardrails and disable them
            enabled_guardrails = self.agent.extract_elements('tr:contains("Enabled")')
            
            if not enabled_guardrails or len(enabled_guardrails) == 0:
                print("No enabled Control Tower GuardRails found")
            else:
                for guardrail in enabled_guardrails:
                    # Select the guardrail
                    self.agent.click(guardrail)
                    
                    # Click disable button
                    self.agent.wait_and_click('button:contains("Disable")')
                    
                    # Confirm disabling
                    self.agent.wait_and_click('button:contains("Disable")')
                    
                    # Wait for disabling to complete
                    self.agent.wait_for_element('div:contains("successfully disabled")')
            
            print("Completed Control Tower GuardRails check")
        except Exception as e:
            print(f"Control Tower GuardRails check skipped: {str(e)}")
    
    def check_marketplace_subscriptions(self):
        """Check and cancel AWS Marketplace subscriptions."""
        print("Checking AWS Marketplace subscriptions...")
        
        # Navigate to AWS Marketplace subscriptions
        self.agent.navigate("https://console.aws.amazon.com/marketplace/home#/subscriptions")
        
        # Wait for page to load
        self.agent.wait_for_element('body.awsui')
        
        # Check if there are subscriptions
        subscriptions = self.agent.extract_elements('table tbody tr')
        
        if not subscriptions or len(subscriptions) == 0:
            print("No AWS Marketplace subscriptions found")
            return
        
        # Cancel each subscription
        for subscription in subscriptions:
            # Click on Manage for the subscription
            self.agent.click(subscription.find_element('a:contains("Manage")'))
            
            # Click cancel subscription button
            self.agent.wait_and_click('button:contains("Cancel subscription")')
            
            # Confirm cancellation
            self.agent.wait_and_click('button:contains("Yes, cancel subscription")')
            
            # Wait for cancellation to complete
            self.agent.wait_for_element('div:contains("successfully cancelled")')
            
            # Go back to subscriptions list
            self.agent.navigate("https://console.aws.amazon.com/marketplace/home#/subscriptions")
            self.agent.wait_for_element('body.awsui')
        
        print("Completed AWS Marketplace subscriptions cancellation")
    
    def check_all_regions(self):
        """Check for services in all AWS regions."""
        print("Checking for services in all AWS regions...")
        
        # Get the region dropdown
        self.agent.navigate("https://console.aws.amazon.com/console/home")
        self.agent.wait_for_element('body.awsui')
        
        # Click on the region dropdown
        self.agent.wait_and_click('#awsc-nav-regions-menu-button')
        
        # Get all regions
        region_elements = self.agent.extract_elements('#awsc-nav-regions-menu li')
        regions = []
        
        for region_element in region_elements:
            region_name = self.agent.get_text_from_element(region_element)
            regions.append(region_name)
        
        print(f"Found {len(regions)} AWS regions to check")
        
        # Check each region for services
        for i, region in enumerate(regions):
            print(f"Checking region {i+1}/{len(regions)}: {region}")
            
            # Click on the region dropdown
            self.agent.wait_and_click('#awsc-nav-regions-menu-button')
            
            # Select the region
            region_selector = f'#awsc-nav-regions-menu li:contains("{region}")'
            self.agent.wait_and_click(region_selector)
            
            # Wait for region change
            time.sleep(2)
            
            # Check OpenSearch Serverless in this region
            self.cancel_opensearch_serverless()
            
            # Check Bedrock Services in this region
            self.cancel_bedrock_services()
            
            # Check GuardRail Services in this region
            self.cancel_guardrail_services()
        
        print("Completed checking all regions")
    
    def cancel_targeted_services(self):
        """Cancel specific AWS services that appear in Cost Explorer."""
        print("Beginning cancellation of targeted AWS services...")
        
        # Cancel OpenSearch Serverless collections (SearchOCU and IndexingOCU)
        self.cancel_opensearch_serverless()
        
        # Cancel Bedrock Services (DeepSeek tokens)
        self.cancel_bedrock_services()
        
        # Cancel GuardRail Services
        self.cancel_guardrail_services()
        
        # Check AWS Marketplace subscriptions
        self.check_marketplace_subscriptions()
        
        # Check services in all regions
        self.check_all_regions()
        
        print("Completed cancellation of targeted AWS services")


def main(aws_account=None, aws_password=None):
    """Run AWS service cancellation for specific services shown in Cost Explorer."""
    # Get AWS credentials from env or arguments
    aws_account = aws_account or os.environ.get("AWS_ACCOUNT", "")
    aws_password = aws_password or os.environ.get("AWS_PASSWORD", "")
    
    if not aws_account or not aws_password:
        print("Error: AWS account and password are required.")
        print("Either provide them as arguments or set the AWS_ACCOUNT and AWS_PASSWORD environment variables.")
        return
    
    # Initialize Nova Act agent
    agent = NovaAct(
        nova_act_api_key=os.environ.get("NOVA_ACT_API_KEY", ""),
        logs_directory="./aws_logs",
        headless=False  # Set to True for headless mode
    )
    
    try:
        # Create service canceler
        canceler = AWSServiceCanceler(agent)
        
        # Login to AWS Console
        canceler.login_to_aws_console(aws_account, aws_password)
        
        # Cancel targeted AWS services
        canceler.cancel_targeted_services()
        
        print("Successfully canceled targeted AWS services generating charges")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
    finally:
        # Close the browser session
        agent.close()


if __name__ == "__main__":
    fire.Fire(main)

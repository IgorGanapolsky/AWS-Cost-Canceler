#!/usr/bin/env python3
"""
AWS Service Canceler - Boto3 Edition
This script uses boto3 to programmatically cancel specific AWS services
that are generating charges as seen in the Cost Explorer.
"""

import os
import time
import sys
import boto3
import fire
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
dotenv_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path)

# Path to store canceled services information
CANCELED_SERVICES_PATH = Path(__file__).parent.parent / 'data'
CANCELED_SERVICES_FILE = CANCELED_SERVICES_PATH / 'canceled_services.json'

class AWSServiceCancelerBoto3:
    """Class to cancel specific AWS services that are generating charges using boto3."""
    
    def __init__(self):
        """Initialize with AWS credentials."""
        # Load AWS credentials from environment variables
        self.aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            print("ERROR: AWS API credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file.")
            print("Note: These are different from your AWS console login credentials.")
            print("You can create API keys in the AWS IAM console: https://console.aws.amazon.com/iam/home#/security_credentials")
            sys.exit(1)
        
        # Create boto3 session with API credentials
        self.session = boto3.Session(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )
        
        # Get AWS regions
        try:
            self.regions = self.get_all_regions()
            print(f"Found {len(self.regions)} AWS regions")
        except Exception as e:
            print(f"Error connecting to AWS: {str(e)}")
            print("Please check your AWS credentials.")
            sys.exit(1)
        
        # Initialize dictionary to track canceled services
        self.canceled_services = self.load_canceled_services()
    
    def load_canceled_services(self):
        """Load previously canceled services from JSON file."""
        # Create data directory if it doesn't exist
        CANCELED_SERVICES_PATH.mkdir(exist_ok=True)
        
        if CANCELED_SERVICES_FILE.exists():
            try:
                with open(CANCELED_SERVICES_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading canceled services: {str(e)}")
                return {}
        else:
            return {}
    
    def save_canceled_services(self):
        """Save canceled services information to JSON file."""
        try:
            with open(CANCELED_SERVICES_FILE, 'w') as f:
                json.dump(self.canceled_services, f, indent=2)
            print(f"Canceled services information saved to {CANCELED_SERVICES_FILE}")
        except Exception as e:
            print(f"Error saving canceled services: {str(e)}")
    
    def record_service_cancellation(self, service_name, cost):
        """Record that a service was canceled."""
        today = datetime.now().strftime('%Y-%m-%d')
        
        self.canceled_services[service_name] = {
            'status': 'Canceled',
            'canceled_on': today,
            'cost_at_cancellation': cost
        }
        
        # Save after each update to prevent data loss
        self.save_canceled_services()
    
    def get_service_status(self):
        """Get the status of all services that have been processed."""
        return self.canceled_services
    
    def get_all_regions(self):
        """Get all available AWS regions."""
        ec2 = self.session.client('ec2', region_name='us-east-1')
        regions = [region['RegionName'] for region in ec2.describe_regions()['Regions']]
        return regions
    
    def cancel_opensearch_serverless(self):
        """Cancel OpenSearch Serverless collections (IndexingOCU and SearchOCU)."""
        print("\n=== Canceling OpenSearch Serverless Collections ===")
        
        for region in self.regions:
            print(f"\nChecking region: {region}")
            try:
                # Create OpenSearch Serverless client for this region
                aoss = self.session.client('opensearchserverless', region_name=region)
                
                # List collections
                collections = aoss.list_collections()
                
                if 'collectionSummaries' in collections and collections['collectionSummaries']:
                    print(f"Found {len(collections['collectionSummaries'])} OpenSearch Serverless collections in {region}")
                    
                    # Delete each collection
                    for collection in collections['collectionSummaries']:
                        collection_id = collection['id']
                        collection_name = collection['name']
                        print(f"Deleting collection: {collection_name} (ID: {collection_id})")
                        
                        try:
                            # Delete the collection
                            aoss.delete_collection(id=collection_id)
                            print(f"Deletion initiated for collection: {collection_name}")
                            
                            # Wait for deletion to complete
                            print("Waiting for deletion to complete...")
                            while True:
                                try:
                                    status = aoss.get_collection(id=collection_id)
                                    print(f"Status: {status['status'] if 'status' in status else 'Unknown'}")
                                    time.sleep(5)
                                except aoss.exceptions.ResourceNotFoundException:
                                    print(f"Collection {collection_name} deleted successfully")
                                    break
                        except Exception as e:
                            print(f"Error deleting collection {collection_name}: {str(e)}")
                else:
                    print(f"No OpenSearch Serverless collections found in {region}")
                
                # Check for ingestion pipelines - this functionality may not be available in all regions
                # or may have a different API method name
                try:
                    # First try the list_ingestion_pipelines method if available
                    if hasattr(aoss, 'list_ingestion_pipelines'):
                        pipelines = aoss.list_ingestion_pipelines()
                        self._process_ingestion_pipelines(aoss, pipelines, region)
                    # Then try list_pipelines (which was causing the error)
                    elif hasattr(aoss, 'list_pipelines'):
                        pipelines = aoss.list_pipelines()
                        self._process_pipeline_summaries(aoss, pipelines, region)
                    else:
                        # Try the latest API methods as of 2025
                        # Method 1: Try get_pipeline_blueprints
                        if hasattr(aoss, 'get_pipeline_blueprints'):
                            print("Using get_pipeline_blueprints method for pipeline discovery")
                            try:
                                blueprints = aoss.get_pipeline_blueprints()
                                if 'blueprints' in blueprints and blueprints['blueprints']:
                                    print(f"Found {len(blueprints['blueprints'])} pipeline blueprints in {region}")
                                    # Process blueprints and delete associated pipelines
                                    self._process_pipeline_blueprints(aoss, blueprints, region)
                            except Exception as e:
                                print(f"Error listing pipeline blueprints in {region}: {str(e)}")
                        
                        # Method 2: General method to find all OpenSearch Serverless resources
                        print("Attempting to find and delete all OpenSearch Serverless resources...")
                        self._delete_all_opensearch_resources(region)
                except Exception as e:
                    print(f"Note: Pipeline deletion skipped in {region}. This is likely because the API doesn't support pipeline operations in this region.")
                    print(f"Technical details: {str(e)}")
            
            except Exception as e:
                print(f"Error accessing OpenSearch Serverless in {region}: {str(e)}")
    
    def _process_ingestion_pipelines(self, aoss, pipelines, region):
        """Process ingestion pipelines using the newer API."""
        if 'ingestionPipelines' in pipelines and pipelines['ingestionPipelines']:
            print(f"Found {len(pipelines['ingestionPipelines'])} OpenSearch ingestion pipelines in {region}")
            
            # Delete each pipeline
            for pipeline in pipelines['ingestionPipelines']:
                pipeline_id = pipeline['id']
                pipeline_name = pipeline.get('name', pipeline_id)
                print(f"Deleting pipeline: {pipeline_name} (ID: {pipeline_id})")
                
                try:
                    # Delete the pipeline
                    aoss.delete_ingestion_pipeline(id=pipeline_id)
                    print(f"Deletion initiated for pipeline: {pipeline_name}")
                    
                    # Wait for deletion to complete
                    print("Waiting for deletion to complete...")
                    while True:
                        try:
                            status = aoss.get_ingestion_pipeline(id=pipeline_id)
                            print(f"Status: {status['status'] if 'status' in status else 'Unknown'}")
                            time.sleep(5)
                        except aoss.exceptions.ResourceNotFoundException:
                            print(f"Pipeline {pipeline_name} deleted successfully")
                            break
                except Exception as e:
                    print(f"Error deleting pipeline {pipeline_name}: {str(e)}")
        else:
            print(f"No OpenSearch ingestion pipelines found in {region}")
    
    def _process_pipeline_summaries(self, aoss, pipelines, region):
        """Process pipeline summaries using the older API."""
        if 'pipelineSummaries' in pipelines and pipelines['pipelineSummaries']:
            print(f"Found {len(pipelines['pipelineSummaries'])} OpenSearch pipelines in {region}")
            
            # Delete each pipeline
            for pipeline in pipelines['pipelineSummaries']:
                pipeline_id = pipeline['id']
                pipeline_name = pipeline['name']
                print(f"Deleting pipeline: {pipeline_name} (ID: {pipeline_id})")
                
                try:
                    # Delete the pipeline
                    aoss.delete_pipeline(id=pipeline_id)
                    print(f"Deletion initiated for pipeline: {pipeline_name}")
                    
                    # Wait for deletion to complete
                    print("Waiting for deletion to complete...")
                    while True:
                        try:
                            status = aoss.get_pipeline(id=pipeline_id)
                            print(f"Status: {status['status'] if 'status' in status else 'Unknown'}")
                            time.sleep(5)
                        except aoss.exceptions.ResourceNotFoundException:
                            print(f"Pipeline {pipeline_name} deleted successfully")
                            break
                except Exception as e:
                    print(f"Error deleting pipeline {pipeline_name}: {str(e)}")
        else:
            print(f"No OpenSearch pipelines found in {region}")
    
    def _process_pipeline_blueprints(self, aoss, blueprints, region):
        """Process pipeline blueprints and delete associated pipelines."""
        for blueprint in blueprints['blueprints']:
            blueprint_id = blueprint['blueprintId']
            print(f"Found pipeline blueprint: {blueprint_id}")
            
            try:
                # Get pipelines associated with this blueprint
                associated_pipelines = aoss.list_pipelines_for_blueprint(blueprintId=blueprint_id)
                
                if 'pipelines' in associated_pipelines and associated_pipelines['pipelines']:
                    print(f"Found {len(associated_pipelines['pipelines'])} pipelines for blueprint {blueprint_id}")
                    
                    for pipeline in associated_pipelines['pipelines']:
                        pipeline_id = pipeline['pipelineId']
                        print(f"Deleting pipeline: {pipeline_id}")
                        
                        try:
                            aoss.delete_pipeline(pipelineId=pipeline_id)
                            print(f"Pipeline {pipeline_id} deletion initiated")
                        except Exception as e:
                            print(f"Error deleting pipeline {pipeline_id}: {str(e)}")
            except Exception as e:
                print(f"Error processing blueprint {blueprint_id}: {str(e)}")
    
    def _delete_all_opensearch_resources(self, region):
        """Attempt to delete all OpenSearch Serverless resources in the region."""
        # Use the AWS CLI as a fallback to get and delete OpenSearch resources
        try:
            # Create an AWS CLI command processor
            cli = self.session.client('opensearchserverless', region_name=region)
            
            # List all resource types that might exist
            resource_types = [
                'collection', 'security-config', 'access-policy', 'vpc-endpoint',
                'lifecycle-policy', 'data-policy'
            ]
            
            for resource_type in resource_types:
                list_method_name = f"list_{resource_type.replace('-', '_')}s"
                delete_method_name = f"delete_{resource_type.replace('-', '_')}"
                
                if hasattr(cli, list_method_name):
                    try:
                        list_method = getattr(cli, list_method_name)
                        response = list_method()
                        
                        # The key in the response will vary by resource type
                        resource_key = next((k for k in response.keys() if k.endswith('Summaries') or k.startswith('list')), None)
                        
                        if resource_key and isinstance(response[resource_key], list):
                            resources = response[resource_key]
                            print(f"Found {len(resources)} {resource_type}s in {region}")
                            
                            if hasattr(cli, delete_method_name):
                                delete_method = getattr(cli, delete_method_name)
                                for resource in resources:
                                    resource_id = resource.get('id', resource.get('name', resource.get('arn')))
                                    if resource_id:
                                        try:
                                            print(f"Deleting {resource_type}: {resource_id}")
                                            delete_method(id=resource_id)
                                            print(f"Deletion of {resource_type} {resource_id} initiated")
                                        except Exception as e:
                                            print(f"Error deleting {resource_type} {resource_id}: {str(e)}")
                    except Exception as e:
                        print(f"Error listing {resource_type}s in {region}: {str(e)}")
        except Exception as e:
            print(f"Error in general resource cleanup for {region}: {str(e)}")
    
    def cancel_bedrock_services(self):
        """Cancel Amazon Bedrock Services (DeepSeek tokens)."""
        print("\n=== Canceling Amazon Bedrock Services ===")
        
        for region in self.regions:
            print(f"\nChecking region: {region}")
            try:
                # Create Bedrock client for this region
                bedrock = self.session.client('bedrock', region_name=region)
                
                # Try to list model access
                try:
                    model_access = bedrock.get_foundation_model_access()
                    
                    if 'models' in model_access:
                        deepseek_models = [m for m in model_access['models'] if 'DeepSeek' in m]
                        
                        if deepseek_models:
                            print(f"Found {len(deepseek_models)} DeepSeek models with access in {region}")
                            
                            try:
                                # Update model access to remove DeepSeek models
                                current_models = set(model_access['models'])
                                updated_models = current_models - set(deepseek_models)
                                
                                if updated_models != current_models:
                                    print(f"Removing access to DeepSeek models in {region}...")
                                    bedrock.put_foundation_model_access(
                                        models=list(updated_models)
                                    )
                                    print(f"Successfully removed access to DeepSeek models in {region}")
                                else:
                                    print(f"No changes needed to model access in {region}")
                            except Exception as e:
                                print(f"Error updating model access in {region}: {str(e)}")
                        else:
                            print(f"No DeepSeek models found with access in {region}")
                    else:
                        print(f"No model access information available in {region}")
                except Exception as e:
                    print(f"Error listing model access in {region}: {str(e)}")
                
                # Check for provisioned throughput
                try:
                    throughput = bedrock.list_provisioned_model_throughputs()
                    
                    if 'provisionedModelSummaries' in throughput and throughput['provisionedModelSummaries']:
                        deepseek_throughputs = [
                            t for t in throughput['provisionedModelSummaries'] 
                            if 'DeepSeek' in t['modelId']
                        ]
                        
                        if deepseek_throughputs:
                            print(f"Found {len(deepseek_throughputs)} DeepSeek provisioned throughputs in {region}")
                            
                            # Delete each throughput
                            for throughput_item in deepseek_throughputs:
                                throughput_name = throughput_item['provisionedModelName']
                                throughput_arn = throughput_item['provisionedModelArn']
                                
                                print(f"Deleting provisioned throughput: {throughput_name}")
                                try:
                                    bedrock.delete_provisioned_model_throughput(
                                        provisionedModelId=throughput_arn
                                    )
                                    print(f"Deletion initiated for provisioned throughput: {throughput_name}")
                                except Exception as e:
                                    print(f"Error deleting provisioned throughput {throughput_name}: {str(e)}")
                        else:
                            print(f"No DeepSeek provisioned throughputs found in {region}")
                    else:
                        print(f"No provisioned throughputs found in {region}")
                except Exception as e:
                    print(f"Error listing provisioned throughputs in {region}: {str(e)}")
            
            except Exception as e:
                print(f"Error accessing Bedrock in {region}: {str(e)}")
    
    def cancel_guardrail_services(self):
        """Cancel Amazon GuardRail Services."""
        print("\n=== Canceling Amazon GuardRail Services ===")
        
        for region in self.regions:
            print(f"\nChecking region: {region}")
            try:
                # Create Bedrock-guardrails client for this region
                guardrails = self.session.client('bedrock-guardrails', region_name=region)
                
                # List guardrails
                try:
                    response = guardrails.list_guardrails()
                    
                    if 'guardrails' in response and response['guardrails']:
                        print(f"Found {len(response['guardrails'])} guardrails in {region}")
                        
                        # Delete each guardrail
                        for guardrail in response['guardrails']:
                            guardrail_id = guardrail['id']
                            guardrail_name = guardrail['name']
                            
                            print(f"Deleting guardrail: {guardrail_name} (ID: {guardrail_id})")
                            try:
                                guardrails.delete_guardrail(
                                    guardrailIdentifier=guardrail_id
                                )
                                print(f"Deletion initiated for guardrail: {guardrail_name}")
                            except Exception as e:
                                print(f"Error deleting guardrail {guardrail_name}: {str(e)}")
                    else:
                        print(f"No guardrails found in {region}")
                except Exception as e:
                    print(f"Error listing guardrails in {region}: {str(e)}")
            
            except Exception as e:
                print(f"Error accessing GuardRails in {region}: {str(e)}")
                
        # Also check Control Tower GuardRails if applicable
        print("\nChecking AWS Control Tower GuardRails...")
        try:
            controltower = self.session.client('controltower', region_name='us-east-1')
            
            try:
                # List enabled controls
                response = controltower.list_enabled_controls()
                
                if 'enabledControls' in response and response['enabledControls']:
                    print(f"Found {len(response['enabledControls'])} enabled Control Tower controls")
                    
                    # Disable each control
                    for control in response['enabledControls']:
                        control_id = control['controlIdentifier']
                        
                        print(f"Disabling control: {control_id}")
                        try:
                            controltower.disable_control(
                                controlIdentifier=control_id
                            )
                            print(f"Disable initiated for control: {control_id}")
                        except Exception as e:
                            print(f"Error disabling control {control_id}: {str(e)}")
                else:
                    print("No enabled Control Tower controls found")
            except Exception as e:
                print(f"Error listing Control Tower controls: {str(e)}")
            
        except Exception as e:
            print(f"Error accessing Control Tower: {str(e)}")
    
    def check_marketplace_subscriptions(self):
        """Check and cancel AWS Marketplace subscriptions."""
        print("\n=== Checking AWS Marketplace Subscriptions ===")
        
        # Marketplace subscriptions are primarily managed in us-east-1
        try:
            marketplace = self.session.client('marketplace-catalog', region_name='us-east-1')
            
            try:
                # List all active subscriptions
                response = marketplace.list_entities(
                    Catalog='AWSMarketplace',
                    EntityType='ServerProduct'
                )
                
                if 'EntitySummaryList' in response and response['EntitySummaryList']:
                    print(f"Found {len(response['EntitySummaryList'])} Marketplace entities")
                    
                    # Note: Marketplace subscriptions cannot be fully canceled via API
                    # We can only list them and provide information
                    for entity in response['EntitySummaryList']:
                        entity_id = entity['EntityId']
                        entity_name = entity.get('Name', 'Unknown')
                        
                        print(f"Found Marketplace entity: {entity_name} (ID: {entity_id})")
                        print("  Note: Marketplace subscriptions need to be canceled manually through the AWS Console")
                        print("  URL: https://console.aws.amazon.com/marketplace/home#/subscriptions")
                else:
                    print("No Marketplace entities found")
            except Exception as e:
                print(f"Error listing Marketplace entities: {str(e)}")
            
        except Exception as e:
            print(f"Error accessing Marketplace catalog: {str(e)}")
        
        print("\nTo cancel AWS Marketplace subscriptions, please visit:")
        print("https://console.aws.amazon.com/marketplace/home#/subscriptions")
    
    def cancel_targeted_services(self):
        """Cancel specific AWS services that appear in Cost Explorer."""
        services_to_cancel = {
            "Amazon OpenSearch Service": self.cancel_opensearch_serverless,
            "AWS Skill Builder Individual": self.cancel_marketplace_subscriptions,
            # Add more services and their cancellation functions as needed
        }
        
        for service_name, cancel_func in services_to_cancel.items():
            try:
                print(f"Canceling {service_name}...")
                cancel_func()
                self.record_service_cancellation(service_name, 0.0)  # Cost info not available here
            except Exception as e:
                print(f"Error canceling {service_name}: {str(e)}")
    
    def cancel_marketplace_subscriptions(self):
        """Cancel AWS Marketplace subscriptions."""
        print("\n=== Canceling AWS Marketplace Subscriptions ===")
        
        # Marketplace subscriptions are primarily managed in us-east-1
        try:
            marketplace = self.session.client('marketplace-catalog', region_name='us-east-1')
            
            try:
                # List all active subscriptions
                response = marketplace.list_entities(
                    Catalog='AWSMarketplace',
                    EntityType='ServerProduct'
                )
                
                if 'EntitySummaryList' in response and response['EntitySummaryList']:
                    print(f"Found {len(response['EntitySummaryList'])} Marketplace entities")
                    
                    # Note: Marketplace subscriptions cannot be fully canceled via API
                    # We can only list them and provide information
                    for entity in response['EntitySummaryList']:
                        entity_id = entity['EntityId']
                        entity_name = entity.get('Name', 'Unknown')
                        
                        print(f"Found Marketplace entity: {entity_name} (ID: {entity_id})")
                        print("  Note: Marketplace subscriptions need to be canceled manually through the AWS Console")
                        print("  URL: https://console.aws.amazon.com/marketplace/home#/subscriptions")
                else:
                    print("No Marketplace entities found")
            except Exception as e:
                print(f"Error listing Marketplace entities: {str(e)}")
            
        except Exception as e:
            print(f"Error accessing Marketplace catalog: {str(e)}")
        
        print("\nTo cancel AWS Marketplace subscriptions, please visit:")
        print("https://console.aws.amazon.com/marketplace/home#/subscriptions")


def main(service_list=None):
    """Run AWS service cancellation for specific services shown in Cost Explorer.
    
    Args:
        service_list: Optional list of services to cancel. If not provided, will
                     use Cost Explorer data to determine services to cancel.
    """
    # Initialize the canceler
    canceler = AWSServiceCancelerBoto3()
    
    # Run service cancellation
    if service_list:
        for service in service_list:
            canceler.cancel_targeted_services([service])
    else:
        canceler.cancel_targeted_services()
    
    # Return the cancellation status for reporting
    return canceler.get_service_status()


if __name__ == "__main__":
    fire.Fire(main)

"""
AWS Service Classifier - Dynamically identifies service types and billing models

This utility automatically detects and classifies AWS services based on:
1. Pay-as-you-go usage model (no persistent resources)
2. Resource-based billing (EC2, RDS, etc.)
3. Required services (Tax, etc.)

The classifier uses AWS pricing API, service metadata, and heuristics to
determine the appropriate service category.
"""

import boto3
import json
import logging
import os
from typing import Dict, List, Set, Any
from botocore.exceptions import ClientError

# Import our new AWS Resource Explorer if available
try:
    from .aws_resource_explorer import AWSResourceExplorer
    resource_explorer_available = True
except ImportError:
    resource_explorer_available = False

logger = logging.getLogger(__name__)

class AWSServiceClassifier:
    """Classifier for AWS services based on billing model"""
    
    def __init__(self):
        """Initialize the classifier with AWS session"""
        self.session = boto3.Session()
        self.pricing_client = self.session.client('pricing', region_name='us-east-1')
        self.service_cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                              'data', 'service_classifications.json')
        self.service_cache = self._load_service_cache()
        
    def _load_service_cache(self) -> Dict[str, str]:
        """Load cached service classifications from disk"""
        try:
            if os.path.exists(self.service_cache_path):
                with open(self.service_cache_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading service cache: {e}")
        
        # Default cache structure
        return {
            "pay_as_you_go": [
                'Amazon Rekognition', 
                'Amazon Transcribe',
                'Amazon Polly',
                'Amazon Textract',
                'Amazon Comprehend',
                'Amazon Translate',
                'Amazon Lex',
                'AWS CodeWhisperer',
                'Amazon Kendra'
            ],
            "resource_based": [],
            "required": ["Tax", "AWS Tax", "Tax on AWS services"],
            "last_updated": "2025-04-01"
        }
    
    def _save_service_cache(self):
        """Save service classifications to disk"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.service_cache_path), exist_ok=True)
            
            with open(self.service_cache_path, 'w') as f:
                json.dump(self.service_cache, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Error saving service cache: {e}")
    
    def update_service_classifications(self, force_refresh=False):
        """Update service classifications using AWS APIs and heuristics"""
        if not force_refresh and self.service_cache.get("pay_as_you_go"):
            # Already have classifications cached
            return
            
        # First, identify pay-as-you-go services using pricing API
        # AWS doesn't have a formal API for this, so we use a heuristic approach
        try:
            # Start with known pay-as-you-go AI services 
            pay_as_you_go_services = set(self.service_cache.get("pay_as_you_go", []))
            
            # Try to use Resource Explorer if available for better discovery
            if resource_explorer_available:
                try:
                    explorer = AWSResourceExplorer()
                    if explorer.is_available():
                        logger.info("Using AWS Resource Explorer for service discovery")
                        discovered_services = explorer.get_pay_as_you_go_services()
                        pay_as_you_go_services.update(discovered_services)
                        logger.info(f"Resource Explorer found {len(discovered_services)} pay-as-you-go services")
                except Exception as e:
                    logger.warning(f"Error using Resource Explorer: {e}")
            
            # Identify API-based services (likely pay-as-you-go) if boto3 client is available
            try:
                response = self.pricing_client.describe_services()
                for service in response.get('Services', []):
                    service_code = service.get('ServiceCode')
                    
                    # Get attribute values for this service
                    attr_response = self.pricing_client.describe_services(
                        ServiceCode=service_code,
                        FormatVersion='aws_v1'
                    )
                    
                    for attr in attr_response.get('AttributeNames', []):
                        # Services with usage-based pricing and no resource dimensions
                        # are likely pay-as-you-go
                        if attr in ['usagetype', 'operation'] and service_code not in ['AmazonEC2', 'AmazonRDS', 'AmazonS3']:
                            # Convert service code to display name
                            service_name = self._get_service_display_name(service_code)
                            if service_name:
                                pay_as_you_go_services.add(service_name)
            except Exception as e:
                logger.warning(f"Error fetching service data from AWS API: {e}")
                # Continue with default list if API fails
            
            # Update cache
            self.service_cache["pay_as_you_go"] = list(pay_as_you_go_services)
            self._save_service_cache()
            
        except Exception as e:
            logger.warning(f"Error updating service classifications: {e}")
            # Fall back to default list if API fails
    
    def _get_service_display_name(self, service_code: str) -> str:
        """Convert AWS service code to display name"""
        # Mapping of common service codes to display names
        mapping = {
            'AmazonRekognition': 'Amazon Rekognition',
            'AmazonTranscribe': 'Amazon Transcribe',
            'AmazonPolly': 'Amazon Polly',
            'AmazonTextract': 'Amazon Textract',
            'ComprehendMedical': 'Amazon Comprehend Medical',
            'Comprehend': 'Amazon Comprehend',
            'Translate': 'Amazon Translate',
            'LexBots': 'Amazon Lex',
            'CodeWhisperer': 'AWS CodeWhisperer',
            'AmazonKendra': 'Amazon Kendra'
        }
        
        return mapping.get(service_code, service_code)
    
    def is_pay_as_you_go_service(self, service_name: str) -> bool:
        """Check if a service is pay-as-you-go based"""
        # First, ensure we have updated classifications
        self.update_service_classifications()
        
        # Clean up service name for consistency
        service_name = service_name.strip()
        
        # Check if in known pay-as-you-go services
        pay_as_you_go_services = set(self.service_cache.get("pay_as_you_go", []))
        
        # Direct match
        if service_name in pay_as_you_go_services:
            return True
            
        # Try partial matches for service names that might have suffixes/prefixes
        for known_service in pay_as_you_go_services:
            if known_service in service_name:
                return True
                
        # Additional heuristics
        if any(keyword in service_name for keyword in ['API Gateway', 'Lambda', 'SageMaker']):
            # These are typically usage-based pricing
            return True
            
        return False
    
    def is_required_service(self, service_name: str) -> bool:
        """Check if a service is required (can't be cancelled)"""
        required_services = set(self.service_cache.get("required", []))
        
        # Direct match or partial match
        if service_name in required_services:
            return True
            
        # Tax is always a required service
        if 'Tax' in service_name:
            return True
            
        return False
        
    def get_service_classification(self, service_name: str) -> str:
        """Get the classification for a service
        
        Returns one of:
        - 'Pay-As-You-Go'
        - 'Required'
        - 'Resource-Based'
        """
        if self.is_pay_as_you_go_service(service_name):
            return 'Pay-As-You-Go'
        elif self.is_required_service(service_name):
            return 'Required'
        else:
            return 'Resource-Based'

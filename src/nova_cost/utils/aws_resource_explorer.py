"""
AWS Resource Explorer - Integration with AWS Resource Explorer API

This module provides integration with the AWS Resource Explorer API, which offers
a more comprehensive service discovery mechanism than the Nova ACT SDK.
It can identify all AWS resources across regions and services, making it easier to:

1. Discover pay-as-you-go services in use
2. Find resources that may be generating unexpected costs
3. Identify resources across all AWS regions
"""

import boto3
import logging
from typing import Dict, List, Any, Set
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class AWSResourceExplorer:
    """AWS Resource Explorer integration"""
    
    def __init__(self):
        """Initialize with AWS session"""
        self.session = boto3.Session()
        
        # Check if Resource Explorer is enabled in any region
        self.available_regions = self._get_enabled_regions()
        
    def _get_enabled_regions(self) -> List[str]:
        """Get regions where Resource Explorer is enabled"""
        enabled_regions = []
        
        try:
            # First check us-east-1 which is commonly enabled
            re_client = self.session.client('resource-explorer-2', region_name='us-east-1')
            try:
                # Check if the service is available by making a simple call
                response = re_client.get_index()
                enabled_regions.append('us-east-1')
            except ClientError as e:
                if e.response['Error']['Code'] != 'ResourceNotFoundException':
                    # An error other than "no index", meaning the service is available
                    enabled_regions.append('us-east-1')
        except Exception as e:
            logger.warning(f"Resource Explorer not available in us-east-1: {e}")
            
        # Check other major regions if needed
        for region in ['us-west-2', 'eu-west-1', 'ap-northeast-1']:
            try:
                re_client = self.session.client('resource-explorer-2', region_name=region)
                try:
                    response = re_client.get_index()
                    enabled_regions.append(region)
                except ClientError as e:
                    if e.response['Error']['Code'] != 'ResourceNotFoundException':
                        enabled_regions.append(region)
            except Exception:
                continue
                
        return enabled_regions
    
    def is_available(self) -> bool:
        """Check if AWS Resource Explorer is available in any region"""
        return len(self.available_regions) > 0
        
    def search_resources(self, service_type: str = None, resource_type: str = None) -> List[Dict[str, Any]]:
        """
        Search for AWS resources using Resource Explorer
        
        Args:
            service_type: AWS service to filter by (e.g., 'rekognition')
            resource_type: Specific resource type to filter by
            
        Returns:
            List of resources matching the criteria
        """
        if not self.available_regions:
            logger.warning("AWS Resource Explorer is not enabled in any region")
            return []
            
        # Use the first available region for searching
        region = self.available_regions[0]
        re_client = self.session.client('resource-explorer-2', region_name=region)
        
        # Build query filters
        query = ""
        
        if service_type:
            query += f"service:{service_type.lower()} "
            
        if resource_type:
            query += f"resourcetype:{resource_type} "
            
        try:
            # Search for resources matching the query
            response = re_client.search(
                QueryString=query.strip(),
                MaxResults=100  # Adjust as needed
            )
            
            resources = response.get('Resources', [])
            next_token = response.get('NextToken')
            
            # Handle pagination if needed
            while next_token:
                response = re_client.search(
                    QueryString=query.strip(),
                    MaxResults=100,
                    NextToken=next_token
                )
                resources.extend(response.get('Resources', []))
                next_token = response.get('NextToken')
                
                # Safety check to avoid too many resources
                if len(resources) >= 500:
                    break
                    
            return resources
            
        except Exception as e:
            logger.error(f"Error searching AWS Resource Explorer: {e}")
            return []
    
    def get_pay_as_you_go_services(self) -> Set[str]:
        """
        Identify pay-as-you-go services that are actively being used
        
        Returns:
            Set of pay-as-you-go service names
        """
        pay_as_you_go_services = set()
        
        # List of common pay-as-you-go services to check
        services_to_check = [
            'rekognition',
            'transcribe',
            'comprehend',
            'textract',
            'translate',
            'polly',
            'lex'
        ]
        
        # Check for resources from each service
        for service in services_to_check:
            resources = self.search_resources(service_type=service)
            if resources:
                # Convert service API name to display name
                display_name = f"Amazon {service.capitalize()}"
                pay_as_you_go_services.add(display_name)
                
        return pay_as_you_go_services

"""
AWS Resource Scanner - Utility to scan for AWS resources across regions and identify billing sources
"""
import boto3
import datetime
import time
import concurrent.futures
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, List, Tuple, Any, Optional
import logging
import urllib.parse
from functools import lru_cache

# Load environment variables
dotenv_path = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))).joinpath('.env')
load_dotenv(dotenv_path)

logger = logging.getLogger(__name__)

# Try to import Nova Act SDK properly
try:
    from nova_act import NovaAct
    NOVA_ACT_AVAILABLE = True
except ImportError:
    logger.info("Nova Act SDK not found. AWS console navigation will use fallback URLs.")
    NOVA_ACT_AVAILABLE = False

class NovaClient:
    """Client for interacting with the Nova SDK to get precise AWS console navigation paths."""

    def __init__(self, token: str):
        """Initialize the Nova client with an API token."""
        self.token = token
        self.base_url = "https://api.nova-act.aws/v1"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        # Check if Nova API is accessible to avoid unnecessary connection attempts
        self.api_available = self._check_api_availability()

    def _check_api_availability(self) -> bool:
        """Check if the Nova API is available to avoid unnecessary connection attempts."""
        try:
            import socket
            # Try DNS resolution first without making a connection
            socket.gethostbyname("api.AWS Cost Canceler.aws")
            return True
        except Exception:
            logger.info("Nova Act API (api.AWS Cost Canceler.aws) is not reachable - SDK integration disabled")
            return False

    def get_resource_url(self, resource_type: str, resource_id: str, region: str = "us-east-1") -> str:
        """
        Get a direct URL to an AWS resource in the AWS console.

        Args:
            resource_type: Type of AWS resource (e.g., 'opensearch:collection')
            resource_id: Identifier of the resource
            region: AWS region

        Returns:
            Direct URL to the resource in the AWS console
        """
        # Skip API call if we already know the API isn't available
        if not self.api_available:
            return ""

        try:
            url = f"{self.base_url}/resources/url"
            payload = {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "region": region
            }

            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()

            return response.json().get("url", "")
        except Exception as e:
            logger.warning(f"Error getting resource URL from Nova SDK: {e}")
            return ""

    def get_opensearch_config_urls(self, region: str = "us-east-1") -> Dict[str, str]:
        """
        Get URLs for OpenSearch Serverless configuration areas.

        Args:
            region: AWS region

        Returns:
            Dictionary of URLs for OpenSearch Serverless configuration areas
        """
        # Skip API call if we already know the API isn't available
        if not self.api_available:
            return {}

        try:
            url = f"{self.base_url}/opensearch/config-urls"
            payload = {"region": region}

            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()

            return response.json()
        except Exception as e:
            logger.warning(f"Error getting OpenSearch config URLs from Nova SDK: {e}")
            return {}

class AWSResourceScanner:
    """AWS Resource Scanner - Scans for resources across regions and identifies cost sources"""

    def __init__(self):
        """Initialize the scanner with AWS session"""
        self.session = boto3.Session()
        self.regions = self._get_all_regions()
        self.nova_sdk_token = os.getenv('NOVA_SDK_TOKEN')
        self.fallback_console_urls = {
            "AWS Cost Explorer": "https://console.aws.amazon.com/cost-management/home",
            "Amazon OpenSearch Service": "https://console.aws.amazon.com/opensearch",
            "AWS Skill Builder Individual": "https://explore.skillbuilder.aws/learn",
            "Amazon Bedrock": "https://console.aws.amazon.com/bedrock",
            "Amazon Rekognition": "https://console.aws.amazon.com/rekognition",
            "Amazon Transcribe": "https://console.aws.amazon.com/transcribe",
            "Amazon S3": "https://s3.console.aws.amazon.com/s3",
            "AWS Lambda": "https://console.aws.amazon.com/lambda",
            "Tax": "#", # Tax doesn't have a dedicated console URL
        }

        self.fallback_opensearch_paths = {
            "collections": "/collections",
            "domains": "/domains",
            "security": "/security"
        }

    def _get_all_regions(self) -> List[str]:
        """Get all available AWS regions"""
        try:
            ec2 = self.session.client('ec2', region_name='us-east-1')
            regions = [region['RegionName'] for region in ec2.describe_regions()['Regions']]
            return regions
        except Exception as e:
            print(f"Warning: Could not retrieve regions: {e}")
            # Fallback to common regions
            return ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'eu-west-1', 'eu-central-1']

    def scan_for_opensearch_resources(self) -> List[Dict[str, Any]]:
        """
        Scan all regions for OpenSearch domains

        Returns:
            List of OpenSearch domains with region information
        """
        all_domains = []

        # Use ThreadPoolExecutor to scan regions in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self._scan_region_for_opensearch, region): region for region in self.regions}
            for future in concurrent.futures.as_completed(futures):
                region = futures[future]
                try:
                    domains = future.result()
                    for domain in domains:
                        domain['Region'] = region
                        # Create direct URL to delete this specific domain
                        domain_name = domain['DomainName']
                        domain['DeleteUrl'] = self.generate_direct_console_url(region, 'opensearch', domain_name)
                        all_domains.append(domain)
                except Exception as e:
                    print(f"Error scanning {region} for OpenSearch domains: {e}")

        return all_domains

    def _scan_region_for_opensearch(self, region: str) -> List[Dict[str, Any]]:
        """
        Scan a specific region for OpenSearch domains

        Args:
            region: AWS region name

        Returns:
            List of OpenSearch domains in the region
        """
        try:
            opensearch = self.session.client('opensearch', region_name=region)
            domains = opensearch.list_domain_names()

            # Get full details for each domain
            domain_details = []
            for domain_info in domains.get('DomainNames', []):
                domain_name = domain_info['DomainName']
                try:
                    details = opensearch.describe_domain(DomainName=domain_name)
                    domain_details.append(details['DomainStatus'])
                except Exception as e:
                    print(f"Error getting details for domain {domain_name} in {region}: {e}")
                    # Add basic info even if we can't get full details
                    domain_details.append({'DomainName': domain_name})

            return domain_details
        except Exception as e:
            # Don't log regions where the service doesn't exist
            if "not available in the region" not in str(e).lower():
                print(f"Could not scan {region} for OpenSearch domains: {e}")
            return []

    def scan_for_opensearch_serverless(self) -> List[Dict[str, Any]]:
        """
        Scan for OpenSearch Serverless collections

        Returns:
            List of OpenSearch Serverless collections
        """
        # OpenSearch Serverless is only available in certain regions
        serverless_regions = ['us-east-1', 'us-east-2', 'us-west-2', 'eu-west-1', 'eu-central-1']
        all_collections = []

        for region in serverless_regions:
            try:
                # The service name is different for serverless
                aoss = self.session.client('opensearchserverless', region_name=region)
                response = aoss.list_collections()

                for collection in response.get('collectionSummaries', []):
                    collection['Region'] = region
                    collection['DeleteUrl'] = self.generate_direct_console_url(region, 'opensearch-serverless', 'collections')
                    all_collections.append(collection)
            except Exception as e:
                if "not available in the region" not in str(e).lower():
                    print(f"Could not scan {region} for OpenSearch Serverless: {e}")

        return all_collections

    def scan_for_hidden_opensearch_resources(self) -> List[Dict[str, Any]]:
        """
        Scan for hidden OpenSearch resources by checking Cost Explorer data

        Returns:
            List of regions with potential hidden resources
        """
        # Get cost data from Cost Explorer
        ce = self.session.client('ce', region_name='us-east-1')
        now = datetime.datetime.now()
        start_date = (now - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')

        try:
            response = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    },
                    {
                        'Type': 'DIMENSION',
                        'Key': 'REGION'
                    }
                ],
                Filter={
                    'Dimensions': {
                        'Key': 'SERVICE',
                        'Values': ['Amazon OpenSearch Service']
                    }
                }
            )

            # Extract regions with OpenSearch costs
            regions_with_costs = []

            for group in response.get('ResultsByTime', [{}])[0].get('Groups', []):
                service = group['Keys'][0]
                region = group['Keys'][1]
                cost = float(group['Metrics']['BlendedCost']['Amount'])

                if cost > 0.01:  # Only care about regions with non-trivial costs
                    # Map AWS billing region names to actual region codes
                    region_map = {
                        'us-east-1': 'us-east-1',
                        'US East (N. Virginia)': 'us-east-1',
                        'us-east-2': 'us-east-2',
                        'US East (Ohio)': 'us-east-2',
                        'us-west-1': 'us-west-1',
                        'US West (N. California)': 'us-west-1',
                        'us-west-2': 'us-west-2',
                        'US West (Oregon)': 'us-west-2',
                        'eu-west-1': 'eu-west-1',
                        'EU (Ireland)': 'eu-west-1',
                        'eu-west-2': 'eu-west-2',
                        'EU (London)': 'eu-west-2',
                        'eu-central-1': 'eu-central-1',
                        'EU (Frankfurt)': 'eu-central-1'
                    }

                    region_code = region_map.get(region, region)

                    regions_with_costs.append({
                        'Region': region_code,
                        'Cost': cost,
                        'ConsoleUrl': self.generate_direct_console_url(region_code, 'opensearch', 'domains')
                    })

            return regions_with_costs

        except Exception as e:
            print(f"Error scanning for hidden OpenSearch resources: {e}")
            return []

    @lru_cache(maxsize=10)
    def get_active_regions(self) -> List[str]:
        """Get a list of active AWS regions for the account."""
        # Start with common regions that typically have resources
        common_regions = ["us-east-1", "us-east-2", "us-west-1", "us-west-2", "eu-west-1", "eu-central-1", "ap-northeast-1"]

        # Only return regions where the account has had activity in the last 30 days
        try:
            ce = self.session.client('ce', region_name='us-east-1')
            now = datetime.datetime.now()
            start_date = (now - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = now.strftime('%Y-%m-%d')

            response = ce.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'REGION'}]
            )

            active_regions = []
            for group in response['ResultsByTime'][0]['Groups']:
                region = group['Keys'][0]
                cost = float(group['Metrics']['BlendedCost']['Amount'])

                if cost > 0.01 and region != "global":
                    active_regions.append(region)

            # Add common regions if they're not already in the list
            for region in common_regions:
                if region not in active_regions:
                    active_regions.append(region)

            return active_regions
        except Exception as e:
            print(f"Error getting active regions: {e}")
            return common_regions

    def get_console_url(self, service_name: str, resource_id: Optional[str] = None, region: str = "us-east-1") -> str:
        """
        Get AWS Console URL for a service, using Nova Act if available

        Args:
            service_name: Name of the AWS service
            resource_id: Optional resource ID
            region: AWS region (default: us-east-1)

        Returns:
            URL to the AWS Console for the service/resource
        """
        # For Nova Act navigation, only attempt if available and configured
        if NOVA_ACT_AVAILABLE:
            try:
                # Get URL using Nova Act browser automation
                url = self._get_url_via_nova_act(service_name, resource_id, region)
                if url:
                    return url
            except Exception as e:
                logger.warning(f"Error getting console URL via Nova Act: {e}")

        # Fall back to hardcoded URLs if Nova Act fails or is unavailable
        if service_name in self.fallback_console_urls:
            return self.fallback_console_urls[service_name]

        # If no hardcoded URL is available, create a generic one
        service_slug = service_name.lower().replace(" ", "-")
        return f"https://console.aws.amazon.com/{service_slug}/home?region={region}"

    def _get_url_via_nova_act(self, service_name: str, resource_id: Optional[str] = None, region: str = "us-east-1") -> str:
        """
        Get AWS Console URL using Nova Act browser automation

        Args:
            service_name: Name of the AWS service
            resource_id: Optional resource ID
            region: AWS region

        Returns:
            URL to the AWS console for the service
        """
        # Avoid browser automation for simple URLs we already know
        if service_name in self.fallback_console_urls:
            return self.fallback_console_urls[service_name]

        # For services requiring complex navigation, use Nova Act
        try:
            # Create a temporary script that uses Nova Act to get to the service page
            # We don't actually execute the browser here, but return a URL we know will work

            # Map service names to AWS Console sections
            service_to_console_map = {
                "Amazon OpenSearch Service": "opensearch",
                "AWS Cost Explorer": "cost-management",
                "Amazon Bedrock": "bedrock",
                "AWS Lambda": "lambda",
                "Amazon S3": "s3",
                "Amazon EC2": "ec2",
                "Amazon RDS": "rds"
            }

            # Get the console section for this service
            console_section = service_to_console_map.get(
                service_name,
                service_name.lower().replace(" ", "-").replace("amazon ", "").replace("aws ", "")
            )

            # For resource-specific URLs, include the resource ID
            if resource_id:
                return f"https://console.aws.amazon.com/{console_section}/home?region={region}#/resource/{resource_id}"
            else:
                return f"https://console.aws.amazon.com/{console_section}/home?region={region}"

        except Exception as e:
            logger.warning(f"Error in Nova Act console navigation: {e}")
            return ""

    def get_opensearch_config_urls(self, region: str = "us-east-1") -> Dict[str, str]:
        """
        Get OpenSearch configuration URLs

        Args:
            region: AWS region

        Returns:
            Dictionary of OpenSearch configuration section URLs
        """
        # Try to use Nova Act first if available
        if NOVA_ACT_AVAILABLE:
            try:
                # Full browser automation would be needed here
                # For now, use hardcoded paths
                pass
            except Exception as e:
                logger.warning(f"Error getting OpenSearch config URLs from Nova Act: {e}")

        # Fall back to hardcoded paths
        logger.info("Using fallback navigation paths for OpenSearch")

        base_url = f"https://console.aws.amazon.com/opensearch/home?region={region}#"
        return {
            section: f"{base_url}{path}"
            for section, path in self.fallback_opensearch_paths.items()
        }

    def generate_direct_console_url(self, region: str, resource_type: str, resource_id: str) -> str:
        """
        Generate a direct console URL for an AWS resource (fallback method)

        Args:
            region: AWS region
            resource_type: Type of resource
            resource_id: ID of the resource

        Returns:
            URL to the AWS console
        """
        # Basic mapping of resource types to console paths
        resource_paths = {
            "opensearch": "opensearch/home",
            "bedrock": "bedrock/home",
            "billing": "billing/home",
            "cloudtrail": "cloudtrail/home"
        }

        # Get the base path for this resource type
        base_path = resource_paths.get(resource_type, f"{resource_type}/home")

        # Build the URL
        url = f"https://console.aws.amazon.com/{base_path}?region={region}"

        # Add resource ID if provided (and not a wildcard)
        if resource_id and resource_id != "*":
            url += f"#/{resource_id}"

        return url

    def get_service_specific_cancellation_urls(self, service_name: str) -> List[Dict[str, Any]]:
        """
        Get service-specific cancellation URLs for AWS console navigation

        Args:
            service_name: Name of the AWS service

        Returns:
            List of URLs with instructions for service cancellation
        """
        urls = []

        # List of pay-as-you-go services that need special handling
        pay_as_you_go_services = {
            'Amazon Rekognition': {
                'resource_type': 'rekognition',
                'persistent_resources': ['face-collections'],
                'api_patterns': ['DetectFaces', 'DetectLabels', 'IndexFaces', 'SearchFacesByImage']
            },
            'Amazon Transcribe': {
                'resource_type': 'transcribe',
                'persistent_resources': ['custom-vocabulary', 'custom-language-model'],
                'api_patterns': ['StartTranscriptionJob', 'StartStreamTranscription']
            },
            'Amazon Textract': {
                'resource_type': 'textract',
                'persistent_resources': [],
                'api_patterns': ['AnalyzeDocument', 'DetectDocumentText', 'GetDocumentAnalysis']
            },
            'Amazon Comprehend': {
                'resource_type': 'comprehend',
                'persistent_resources': ['entity-recognizers', 'document-classifiers'],
                'api_patterns': ['DetectEntities', 'DetectSentiment', 'StartEntitiesDetectionJob']
            },
            'Amazon Polly': {
                'resource_type': 'polly',
                'persistent_resources': ['lexicons'],
                'api_patterns': ['SynthesizeSpeech']
            },
            'Amazon Translate': {
                'resource_type': 'translate',
                'persistent_resources': ['custom-terminology'],
                'api_patterns': ['TranslateText', 'StartTextTranslationJob']
            }
        }

        # Handle OpenSearch service specifically
        if "OpenSearch" in service_name:
            primary_region = "us-east-1"

            # If Nova Act SDK is available, we could use it for browser automation
            if NOVA_ACT_AVAILABLE:
                try:
                    # Future enhancement: Use NovaAct for interactive browser sessions
                    # For now, we'll construct the URLs manually
                    pass
                except Exception as e:
                    logger.warning(f"Error using Nova Act for OpenSearch URLs: {e}")

            # Get all active regions where this service might be running
            regions = self.get_active_regions()

            # Get configuration URLs for OpenSearch
            config_urls = self.get_opensearch_config_urls(primary_region)

            # Add main dashboard as the primary starting point
            urls.append({
                "name": "OpenSearch Serverless Dashboard",
                "url": f"https://console.aws.amazon.com/opensearch/home?region={primary_region}#/serverless/collections",
                "instructions": "Start here - View your collections and settings",
                "icon": "tachometer-alt",
                "type": "primary"
            })

            # Add configuration areas that need to be reviewed for cleanup
            urls.extend([
                {
                    "name": "Data Access Policies",
                    "url": f"https://console.aws.amazon.com/opensearch/home?region={primary_region}#/serverless/data-access-policies",
                    "instructions": "Review and remove unnecessary data access policies",
                    "icon": "key",
                    "type": "config"
                },
                {
                    "name": "SAML Authentication",
                    "url": f"https://console.aws.amazon.com/opensearch/home?region={primary_region}#/serverless/saml-providers",
                    "instructions": "Check and disable unused SAML authentication",
                    "icon": "shield-alt",
                    "type": "config"
                },
                {
                    "name": "Encryption Settings",
                    "url": f"https://console.aws.amazon.com/opensearch/home?region={primary_region}#/serverless/encryption-policies",
                    "instructions": "Review active encryption policies",
                    "icon": "lock",
                    "type": "config"
                },
                {
                    "name": "Network Access",
                    "url": f"https://console.aws.amazon.com/opensearch/home?region={primary_region}#/serverless/network-policies",
                    "instructions": "Check and remove unnecessary network policies",
                    "icon": "network-wired",
                    "type": "config"
                }
            ])

            # Add region-specific checks for collections in each region
            for region in regions:
                if region != primary_region:
                    urls.append({
                        "name": f"Check Collections in {region}",
                        "url": f"https://console.aws.amazon.com/opensearch/home?region={region}#/serverless/collections",
                        "instructions": f"View OpenSearch collections in {region}",
                        "icon": "search-location",
                        "type": "region"
                    })

            # Add CloudTrail check for recently deleted resources
            urls.append({
                "name": "Check Recently Deleted Resources",
                "url": f"https://console.aws.amazon.com/cloudtrail/home?region={primary_region}#/events?EventSource=aoss.amazonaws.com&EventName=Delete",
                "instructions": "Find recently deleted resources that might still incur charges",
                "icon": "history",
                "type": "audit"
            })

        # Handle AWS Cost Explorer service
        elif "Cost Explorer" in service_name:
            urls = [
                {
                    "name": "Cost Explorer Dashboard",
                    "url": "https://console.aws.amazon.com/cost-management/home#/dashboard",
                    "instructions": "View your cost dashboard and check for any optimizations",
                    "icon": "tachometer-alt",
                    "type": "primary"
                },
                {
                    "name": "CloudTrail Event History",
                    "url": "https://console.aws.amazon.com/cloudtrail/home#/events?EventSource=ce.amazonaws.com",
                    "instructions": "Review recent Cost Explorer API calls to identify usage patterns",
                    "icon": "history",
                    "type": "audit"
                },
                {
                    "name": "AWS Cost Explorer Report Configuration",
                    "url": "https://console.aws.amazon.com/cost-management/home#/reports",
                    "instructions": "Check and delete any saved Cost Explorer reports",
                    "icon": "file-alt",
                    "type": "config"
                },
                {
                    "name": "AWS Budget Configuration",
                    "url": "https://console.aws.amazon.com/billing/home#/budgets",
                    "instructions": "Review and update budgets used with Cost Explorer",
                    "icon": "dollar-sign",
                    "type": "config"
                }
            ]

        # Handle Amazon Bedrock service
        elif "Bedrock" in service_name:
            urls = [
                {
                    "name": "Amazon Bedrock Dashboard",
                    "url": "https://console.aws.amazon.com/bedrock/home#/overview",
                    "instructions": "View your Bedrock usage overview",
                    "icon": "tachometer-alt",
                    "type": "primary"
                },
                {
                    "name": "Model Access",
                    "url": "https://console.aws.amazon.com/bedrock/home#/modelaccess",
                    "instructions": "Review and remove foundation model access",
                    "icon": "key",
                    "type": "config"
                },
                {
                    "name": "Check Running Knowledge Bases",
                    "url": "https://console.aws.amazon.com/bedrock/home#/knowledgebases",
                    "instructions": "Delete any knowledge bases you no longer need",
                    "icon": "database",
                    "type": "config"
                },
                {
                    "name": "Model Evaluation",
                    "url": "https://console.aws.amazon.com/bedrock/home#/evaluation-jobs",
                    "instructions": "Check for any running model evaluation jobs",
                    "icon": "chart-bar",
                    "type": "config"
                },
                {
                    "name": "CloudTrail Event History",
                    "url": "https://console.aws.amazon.com/cloudtrail/home#/events?EventSource=bedrock.amazonaws.com",
                    "instructions": "Review recent Bedrock API calls",
                    "icon": "history",
                    "type": "audit"
                }
            ]

        # Handle pay-as-you-go AI/ML services
        elif service_name in pay_as_you_go_services:
            service_info = pay_as_you_go_services[service_name]
            resource_type = service_info['resource_type']
            region = "us-east-1"  # Default to us-east-1 for most global AI services

            # Add main dashboard link
            urls.append({
                "name": f"{service_name} Dashboard",
                "url": f"https://console.aws.amazon.com/{resource_type}/home?region={region}",
                "instructions": "View your usage and resource overview",
                "icon": "tachometer-alt",
                "type": "primary"
            })

            # Add CloudTrail check for API usage patterns
            urls.append({
                "name": "CloudTrail Event History",
                "url": self.get_cloudtrail_events_url(service_name),
                "instructions": f"Review recent {service_name} API calls to identify usage patterns",
                "icon": "history",
                "type": "audit"
            })

            # Add specific resource cleanup links
            for resource in service_info['persistent_resources']:
                # Format the resource name for display
                resource_display = resource.replace('-', ' ').title()
                urls.append({
                    "name": f"Check {resource_display}",
                    "url": f"https://console.aws.amazon.com/{resource_type}/home?region={region}#{resource}",
                    "instructions": f"Manage and delete unnecessary {resource_display}",
                    "icon": "database",
                    "type": "config"
                })

            # Add link to Lambda functions that might be using this service
            urls.append({
                "name": "Check Lambda Functions",
                "url": "https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions",
                "instructions": f"Identify Lambda functions that may be making {service_name} API calls",
                "icon": "code",
                "type": "audit"
            })

            # Add specific pay-as-you-go guidance
            urls.append({
                "name": "Billing Guide",
                "url": f"https://aws.amazon.com/{''.join(resource_type.split('-'))}/pricing/",
                "instructions": f"Review {service_name} pricing model and confirm charges have stopped",
                "icon": "dollar-sign",
                "type": "guide"
            })

        return urls

    def run_nova_act_browser_session(self, service_name: str) -> Optional[str]:
        """
        Use Nova Act to run an interactive browser session for AWS console navigation
        This is a placeholder for future implementation

        Args:
            service_name: AWS service to navigate to

        Returns:
            Optional URL captured from the browser session
        """
        if not NOVA_ACT_AVAILABLE:
            logger.warning("Nova Act SDK not available for browser navigation")
            return None

        try:
            # This is where we would integrate with Nova Act for interactive browsing
            # Example based on the samples:
            # with NovaAct(starting_page="https://console.aws.amazon.com") as nova:
            #     nova.act(f"navigate to {service_name}")
            #     nova.act("get the current URL")
            #     return nova.get_current_url()

            # For now, return None as this is a placeholder
            return None
        except Exception as e:
            logger.error(f"Error running Nova Act browser session: {e}")
            return None

    def get_cloudtrail_events_url(self, service_name: str, event_name: Optional[str] = None) -> str:
        """
        Get URL to CloudTrail events for a specific service

        Args:
            service_name: Name of the AWS service
            event_name: Optional specific event name to filter by

        Returns:
            URL to CloudTrail events filtered for the service
        """
        # Map service names to their CloudTrail event sources
        service_to_event_source = {
            "AWS Cost Explorer": "ce.amazonaws.com",
            "Amazon OpenSearch Service": "aoss.amazonaws.com",
            "Amazon Bedrock": "bedrock.amazonaws.com",
            "AWS Lambda": "lambda.amazonaws.com",
            "Amazon S3": "s3.amazonaws.com"
        }

        # Get the event source for this service
        event_source = service_to_event_source.get(
            service_name,
            service_name.lower().replace(" ", "").replace("amazon", "").replace("aws", "") + ".amazonaws.com"
        )

        # Construct the CloudTrail URL
        url = f"https://console.aws.amazon.com/cloudtrail/home#/events?EventSource={event_source}"

        # Add event name filter if provided
        if event_name:
            url += f"&EventName={event_name}"

        return url

    def find_exact_opensearch_billing_source(self) -> Optional[Dict[str, Any]]:
        """
        Find the exact resource that's causing OpenSearch billing charges by
        cross-referencing Cost Explorer and CloudTrail data

        Returns:
            Direct link to the exact billing source if found, None otherwise
        """
        try:
            # Get cost data from Cost Explorer
            ce = self.session.client('ce', region_name='us-east-1')
            now = datetime.datetime.now()
            start_date = (now - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            end_date = now.strftime('%Y-%m-%d')

            # Get detailed cost data with usage types
            response = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost', 'UsageQuantity'],
                GroupBy=[
                    {
                        'Type': 'DIMENSION',
                        'Key': 'SERVICE'
                    },
                    {
                        'Type': 'DIMENSION',
                        'Key': 'USAGE_TYPE'
                    }
                ]
            )

            # Analyze the response to find OpenSearch usage types
            opensearch_usage_types = []
            primary_region = None
            is_serverless = False

            for group in response.get('ResultsByTime', [{}])[0].get('Groups', []):
                service = group['Keys'][0]
                usage_type = group['Keys'][1]
                cost = float(group['Metrics']['BlendedCost']['Amount'])

                if 'OpenSearch' in service and cost > 0.01:
                    opensearch_usage_types.append(usage_type)

                    # Check if this is a Serverless collection
                    if 'Serverless' in usage_type or 'ServerlessOCU' in usage_type:
                        is_serverless = True

                    # Extract region from usage type (e.g., USE1-SearchOCU-t2.small.search)
                    region_code = usage_type.split('-')[0] if '-' in usage_type else None
                    if region_code:
                        region_map = {
                            'USE1': 'us-east-1',
                            'USE2': 'us-east-2',
                            'USW1': 'us-west-1',
                            'USW2': 'us-west-2',
                            'EUW1': 'eu-west-1',
                            'EUW2': 'eu-west-2',
                            'EUC1': 'eu-central-1'
                        }
                        if region_code in region_map and not primary_region:
                            primary_region = region_map[region_code]

            # Default to us-east-1 if we couldn't determine region
            if not primary_region:
                primary_region = 'us-east-1'

            # Always use direct console URLs that work in browsers
            if is_serverless:
                # Direct link to Serverless collections
                return {
                    "name": f"DIRECT LINK: OpenSearch Serverless in {primary_region}",
                    "url": self.generate_direct_console_url(primary_region, 'opensearch-serverless', 'collections'),
                    "instructions": f"This direct link will take you to the OpenSearch Serverless Collections in {primary_region} that are incurring charges."
                }
            else:
                # Try to find specific domain in CloudTrail first
                domain_name = self._find_recent_opensearch_domain(primary_region)
                if domain_name:
                    return {
                        "name": f"DIRECT LINK: OpenSearch Domain '{domain_name}' in {primary_region}",
                        "url": self.generate_direct_console_url(primary_region, 'opensearch', domain_name),
                        "instructions": f"This direct link will take you to the specific OpenSearch domain '{domain_name}' in {primary_region}."
                    }
                else:
                    # Direct link to all domains in the region
                    return {
                        "name": f"DIRECT LINK: OpenSearch Domains in {primary_region}",
                        "url": self.generate_direct_console_url(primary_region, 'opensearch', 'domains'),
                        "instructions": f"This direct link will take you to all OpenSearch domains in {primary_region}."
                    }

        except Exception as e:
            print(f"Error finding exact OpenSearch billing source: {e}")
            return None

    def _find_recent_opensearch_domain(self, region: str) -> Optional[str]:
        """
        Find the most recently created or accessed OpenSearch domain using CloudTrail

        Args:
            region: AWS region to check

        Returns:
            Domain name if found, None otherwise
        """
        try:
            # Use CloudTrail to find recent OpenSearch API calls
            cloudtrail = self.session.client('cloudtrail', region_name=region)
            now = datetime.datetime.now()
            start_time = now - datetime.timedelta(days=30)

            response = cloudtrail.lookup_events(
                LookupAttributes=[
                    {
                        'AttributeKey': 'EventSource',
                        'AttributeValue': 'es.amazonaws.com'
                    }
                ],
                StartTime=start_time,
                EndTime=now,
                MaxResults=10
            )

            # Look for domain names in CloudTrail events
            for event in response.get('Events', []):
                try:
                    cloud_trail_event = json.loads(event.get('CloudTrailEvent', '{}'))
                    request_parameters = cloud_trail_event.get('requestParameters', {})

                    # Check various API calls that might contain domain names
                    domain_name = request_parameters.get('domainName')
                    if domain_name:
                        return domain_name

                    # Check resource ARN which might contain domain name
                    resource_arn = cloud_trail_event.get('resources', [{}])[0].get('ARN', '')
                    if 'domain/' in resource_arn:
                        return resource_arn.split('domain/')[1]
                except:
                    continue

            return None

        except Exception as e:
            print(f"Error searching CloudTrail for OpenSearch domains: {e}")
            return None

    def _get_instance_type(self, domain: Dict[str, Any]) -> str:
        """Extract instance type from domain details"""
        try:
            return domain.get('ClusterConfig', {}).get('InstanceType', 'Unknown')
        except:
            return 'Unknown'

    def _get_instance_count(self, domain: Dict[str, Any]) -> int:
        """Extract instance count from domain details"""
        try:
            return domain.get('ClusterConfig', {}).get('InstanceCount', 0)
        except:
            return 0

    def _get_storage_size(self, domain: Dict[str, Any]) -> int:
        """Extract storage size from domain details"""
        try:
            return domain.get('EBSOptions', {}).get('VolumeSize', 0)
        except:
            return 0

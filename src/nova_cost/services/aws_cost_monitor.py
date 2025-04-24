"""
AWS Cost Monitoring Service
Handles interactions with AWS Cost Explorer API
"""
import boto3
import datetime
from typing import Dict, List, Tuple, Any, Optional


class AWSCostMonitor:
    """Monitor AWS costs using the Cost Explorer API"""
    
    def __init__(self):
        """Initialize the AWS Cost Monitor"""
        self.ce_client = boto3.client('ce')
        
        # Default service consolidation map
        self._service_consolidation = {
            "Claude 3.7 Sonnet": "Amazon Bedrock",
            "Claude 3.5 Sonnet": "Amazon Bedrock",
            "Claude 3 Haiku": "Amazon Bedrock", 
            "Claude 3 Opus": "Amazon Bedrock"
        }
        
        # Service paths with 2025 AWS Console URLs
        self._service_paths = {
            # AWS Billing & Cost Management
            "AWS Cost Explorer": "https://us-east-1.console.aws.amazon.com/cost-management/home#/cost-explorer",
            "Cost Explorer": "https://us-east-1.console.aws.amazon.com/cost-management/home#/cost-explorer",
            "AWS Budgets": "https://us-east-1.console.aws.amazon.com/billing/home#/budgets",
            "Tax": "https://us-east-1.console.aws.amazon.com/billing/home#/bills",
            
            # AWS Services
            "OpenSearch": "https://us-east-1.console.aws.amazon.com/aos/home#/opensearch/domains",
            "Bedrock": "https://us-east-1.console.aws.amazon.com/bedrock/home#/foundation-models",
            "Claude": "https://us-east-1.console.aws.amazon.com/bedrock/home#/foundation-models",
            "DynamoDB": "https://us-east-1.console.aws.amazon.com/dynamodbv2/home#tables",
            "Lambda": "https://us-east-1.console.aws.amazon.com/lambda/home#/functions",
            "EC2": "https://us-east-1.console.aws.amazon.com/ec2/home#Instances",
            "S3": "https://s3.console.aws.amazon.com/s3/buckets",
            "CloudWatch": "https://us-east-1.console.aws.amazon.com/cloudwatch/home#home:",
            "Skill Builder": "https://us-east-1.console.aws.amazon.com/skillbuilder/home#/subscriptions",
            "Marketplace": "https://aws.amazon.com/marketplace/management/subscriptions/metrics"
        }
    
    def get_date_range(self, days_back: int = 30) -> Tuple[str, str]:
        """
        Get formatted start and end dates for the specified time range
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Tuple of (start_date, end_date) as ISO format strings
        """
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days_back)
        return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def get_daily_costs(self, days_back: int = 30) -> List[Tuple[str, float, str]]:
        """
        Get daily costs for the specified number of days
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of (date, cost, service_name) tuples
        """
        start_date, end_date = self.get_date_range(days_back)
        
        try:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='DAILY',
                Metrics=['BlendedCost']
            )
            
            daily_costs = []
            for result in response['ResultsByTime']:
                date = result['TimePeriod']['Start']
                cost = float(result['Total']['BlendedCost']['Amount'])
                daily_costs.append((date, cost, "AWS Services"))
            
            return daily_costs
            
        except Exception as e:
            print(f"Warning: Unable to access AWS Cost Explorer API: {str(e)}")
            print("Using sample daily cost data instead.")
            
            # Return sample data when API access fails
            today = datetime.date.today()
            
            # Generate sample data for the specified days
            sample_daily_costs = []
            for i in range(days_back, 0, -1):
                date = today - datetime.timedelta(days=i)
                date_str = date.strftime('%Y-%m-%d')
                
                # Add some variation to costs
                if i % 5 == 0:  # Every 5 days, have a cost spike
                    cost = 9.75
                else:
                    cost = 3.00 + (i % 3)
                
                sample_daily_costs.append((date_str, cost, "AWS Services"))
            
            return sample_daily_costs
    
    def get_service_costs(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Get costs by service for the specified number of days
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of dictionaries with service cost details
        """
        start_date, end_date = self.get_date_range(days_back)
        
        try:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='MONTHLY',
                Metrics=['BlendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            
            services = []
            for group in response['ResultsByTime'][0]['Groups']:
                service_name = group['Keys'][0]
                cost = float(group['Metrics']['BlendedCost']['Amount'])
                
                # Skip very small costs
                if cost < 0.01:
                    continue
                
                # Determine service details based on service name
                details = "Usage charges"
                if "OpenSearch" in service_name:
                    details = "Search/OUs, Indexing/DUs, Storage"
                elif "Skill Builder" in service_name:
                    details = "Subscription"
                elif "Cost Explorer" in service_name:
                    details = "API usage charges"
                elif "Bedrock" in service_name:
                    details = "Model inference, tokens, API usage"
                elif "Claude" in service_name:
                    details = "Usage charges"
                
                services.append({
                    "service": service_name,
                    "cost": cost,
                    "details": details,
                    "status": "Active"
                })
            
            # Sort services by cost (descending)
            services.sort(key=lambda x: x["cost"], reverse=True)
            
            return services
            
        except Exception as e:
            print(f"Warning: Unable to access AWS Cost Explorer API: {str(e)}")
            print("Using sample cost data instead.")
            
            # Return sample data when API access fails
            return [
                {"service": "AWS Skill Builder Individual", "cost": 58.00, "details": "Subscription", "status": "Canceled on 2025-04-15"},
                {"service": "Amazon OpenSearch Service", "cost": 19.65, "details": "Search/OUs, Indexing/DUs, Storage", "status": "Canceled on 2025-04-15"},
                {"service": "AWS Cost Explorer (Usage Analytics Service)", "cost": 12.15, "details": "API usage charges", "status": "Active"},
                {"service": "Tax (AWS Services)", "cost": 3.82, "details": "Usage charges", "status": "Active"},
                {"service": "Amazon Bedrock", "cost": 0.12, "details": "Model inference, tokens, API usage", "status": "Active"},
                {"service": "Claude 3.7 Sonnet (Amazon Bedrock Edition)", "cost": 0.02, "details": "Usage charges", "status": "Active"},
                {"service": "Amazon S3", "cost": 0.01, "details": "Storage, requests", "status": "Active"}
            ]
    
    def get_service_paths(self) -> Dict[str, str]:
        """
        Get AWS Console paths for services
        
        Returns:
            Dictionary mapping service names to AWS console URLs
        """
        return self._service_paths
    
    def get_service_relationships(self) -> Dict[str, str]:
        """
        Get service relationships for consolidation
        
        Returns:
            Dictionary mapping services to their parent services
        """
        return self._service_consolidation
    
    def get_service_resources(self) -> Dict[str, Dict]:
        """
        Get detailed resources for each service
        
        Returns:
            Nested dictionary of service resources
        """
        # Sample service resources for cancellation
        return {
            "Amazon OpenSearch Service": {
                "resources": [
                    {
                        "name": "production-search",
                        "url": "https://us-east-1.console.aws.amazon.com/aos/home#/opensearch/domains",
                        "instructions": "Find \"production-search\" in the list, click \"Delete\" and confirm deletion"
                    },
                    {
                        "name": "development-search",
                        "url": "https://us-east-1.console.aws.amazon.com/aos/home#/opensearch/domains",
                        "instructions": "Find \"development-search\" in the list, click \"Delete\" and confirm deletion"
                    }
                ]
            },
            "Amazon Bedrock": {
                "resources": [
                    {
                        "name": "Claude 3.5 Sonnet",
                        "url": "https://us-east-1.console.aws.amazon.com/bedrock/home#/foundation-models",
                        "instructions": "Click \"Model access\" tab, find \"Claude 3.5 Sonnet\", click \"Edit access\" and disable the model"
                    }
                ]
            }
        }

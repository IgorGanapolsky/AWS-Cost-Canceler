"""
Tests for the AWSResourceScanner utility
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json
import datetime
from pathlib import Path

# Add the src directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.nova_cost.utils.aws_resource_scanner import AWSResourceScanner

class TestAWSResourceScanner(unittest.TestCase):
    """Test suite for AWSResourceScanner"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scanner = AWSResourceScanner()
        # Mock the boto3 session to avoid actual AWS calls during tests
        self.scanner.session = MagicMock()
    
    @patch('boto3.Session')
    def test_init(self, mock_session):
        """Test initialization with Nova SDK token"""
        # Arrange
        mock_session.return_value.client.return_value.describe_regions.return_value = {
            'Regions': [{'RegionName': 'us-east-1'}, {'RegionName': 'us-west-2'}]
        }
        
        # Act
        scanner = AWSResourceScanner()
        
        # Assert
        self.assertIsNotNone(scanner.nova_sdk_token)
        self.assertIsNotNone(scanner.regions)
    
    @patch('boto3.Session')
    def test_get_all_regions(self, mock_session):
        """Test that all AWS regions are retrieved"""
        # Arrange
        mock_ec2 = MagicMock()
        mock_ec2.describe_regions.return_value = {
            'Regions': [
                {'RegionName': 'us-east-1'}, 
                {'RegionName': 'us-west-2'}
            ]
        }
        mock_session.return_value.client.return_value = mock_ec2
        
        # Act
        scanner = AWSResourceScanner()
        regions = scanner._get_all_regions()
        
        # Assert
        self.assertEqual(regions, ['us-east-1', 'us-west-2'])
        mock_ec2.describe_regions.assert_called_once()
    
    @patch('boto3.Session')
    def test_get_all_regions_error_handling(self, mock_session):
        """Test fallback regions when API call fails"""
        # Arrange
        mock_ec2 = MagicMock()
        mock_ec2.describe_regions.side_effect = Exception("API Error")
        mock_session.return_value.client.return_value = mock_ec2
        
        # Act
        scanner = AWSResourceScanner()
        regions = scanner._get_all_regions()
        
        # Assert
        self.assertTrue(len(regions) > 0)  # Should have fallback regions
        self.assertIn('us-east-1', regions)  # Important region should be included
    
    @patch('boto3.Session')
    def test_scan_opensearch_resources(self, mock_session):
        """Test scanning for OpenSearch domains"""
        # Arrange
        mock_client = MagicMock()
        mock_client.list_domain_names.return_value = {
            'DomainNames': [{'DomainName': 'test-domain'}]
        }
        mock_client.describe_domain.return_value = {
            'DomainStatus': {
                'DomainName': 'test-domain',
                'Endpoint': 'test-endpoint',
                'EngineVersion': '1.0'
            }
        }
        self.scanner.session.client.return_value = mock_client
        self.scanner.regions = ['us-east-1']
        
        # Act
        with patch('concurrent.futures.ThreadPoolExecutor') as mock_executor:
            # Set up the mock executor to actually call the function
            mock_executor.return_value.__enter__.return_value.submit.side_effect = (
                lambda func, region: MagicMock(result=lambda: func(region))
            )
            domains = self.scanner.scan_for_opensearch_resources()
        
        # Assert
        self.assertEqual(len(domains), 1)
        self.assertEqual(domains[0]['DomainName'], 'test-domain')
        self.assertEqual(domains[0]['Region'], 'us-east-1')
        self.assertIn('DeleteUrl', domains[0])
    
    @patch('boto3.Session')
    def test_find_exact_opensearch_billing_source(self, mock_session):
        """Test finding the exact OpenSearch billing source"""
        # Arrange
        mock_ce = MagicMock()
        mock_ce.get_cost_and_usage.return_value = {
            'ResultsByTime': [{
                'Groups': [
                    {
                        'Keys': ['Amazon OpenSearch Service', 'USE1-SearchOCU-t2.small.search'],
                        'Metrics': {'BlendedCost': {'Amount': '10.0'}}
                    }
                ]
            }]
        }
        self.scanner.session.client.return_value = mock_ce
        
        # Act
        result = self.scanner.find_exact_opensearch_billing_source()
        
        # Assert
        self.assertIsNotNone(result)
        self.assertIn('DIRECT LINK', result['name'])
        self.assertIn('us-east-1', result['url'])
        self.assertIn('instructions', result)
        
    @patch('boto3.Session')
    def test_opensearch_serverless_detection(self, mock_session):
        """Test detection of OpenSearch Serverless vs Regular domains"""
        # Arrange
        mock_ce = MagicMock()
        # Simulate ServerlessOCU in the usage type
        mock_ce.get_cost_and_usage.return_value = {
            'ResultsByTime': [{
                'Groups': [
                    {
                        'Keys': ['Amazon OpenSearch Service', 'USE1-ServerlessIndexingOCU'],
                        'Metrics': {'BlendedCost': {'Amount': '10.0'}}
                    }
                ]
            }]
        }
        self.scanner.session.client.return_value = mock_ce
        
        # Act
        result = self.scanner.find_exact_opensearch_billing_source()
        
        # Assert
        self.assertIsNotNone(result)
        self.assertIn('Serverless', result['url'])
        
    def test_generate_nova_sdk_url(self):
        """Test Nova SDK URL generation for direct navigation"""
        # This is a new method we need to implement
        # Arrange
        region = 'us-west-2'
        resource_type = 'opensearch'
        resource_id = 'test-domain'
        
        # Act
        url = self.scanner.generate_nova_sdk_url(region, resource_type, resource_id)
        
        # Assert
        self.assertIsNotNone(url)
        self.assertIn('nova-sdk', url)
        self.assertIn(region, url)
        self.assertIn(resource_type, url)
        self.assertIn(resource_id, url)

    def test_get_service_specific_cancellation_urls_opensearch(self):
        """Test that OpenSearch cancellation URLs are generated correctly without duplicates."""
        scanner = AWSResourceScanner()
        urls = scanner.get_service_specific_cancellation_urls("Amazon OpenSearch Service")
        
        # Helper function to count occurrences of a specific URL pattern
        def count_url_pattern(pattern: str) -> int:
            return sum(1 for url in urls if pattern in url["url"])
        
        # Test for duplicates
        def assert_no_duplicates():
            seen_urls = set()
            duplicates = []
            for url in urls:
                if url["url"] in seen_urls:
                    duplicates.append(url["url"])
                seen_urls.add(url["url"])
            assert not duplicates, f"Found duplicate URLs: {duplicates}"
        
        # Verify no duplicates
        assert_no_duplicates()
        
        # Verify we have exactly one of each config area
        assert count_url_pattern("/serverless/data-access") == 1, "Should have exactly one data access policy URL"
        assert count_url_pattern("/serverless/security") == 2, "Should have exactly two security URLs (SAML and Encryption)"
        assert count_url_pattern("/serverless/network") == 1, "Should have exactly one network policy URL"
        
        # Verify we have the main dashboard
        assert count_url_pattern("/serverless") == 1, "Should have exactly one dashboard URL"
        
        # Verify we have CloudTrail check
        assert count_url_pattern("cloudtrail") == 1, "Should have exactly one CloudTrail URL"
        
        # Verify order of items
        url_types = [url["name"] for url in urls]
        assert "OpenSearch Serverless Dashboard" == url_types[0], "Dashboard should be first"
        assert "Data Access Policies" in url_types[1:5], "Config areas should be after dashboard"
        assert "Check Recently Deleted Resources" == url_types[-1], "CloudTrail check should be last"

    def test_get_service_specific_cancellation_urls_other_services(self):
        """Test that non-OpenSearch services return appropriate URLs."""
        scanner = AWSResourceScanner()
        urls = scanner.get_service_specific_cancellation_urls("Some Other Service")
        assert isinstance(urls, list), "Should return a list even for other services"

    def test_get_opensearch_navigation_info(self):
        """Test retrieving navigation information for OpenSearch."""
        scanner = AWSResourceScanner()
        nav_info = scanner.get_opensearch_navigation_info()
        
        # Verify we have all required navigation paths
        self.assertIn("collections", nav_info)
        self.assertIn("data_access", nav_info)
        self.assertIn("identity", nav_info)
        self.assertIn("encryption", nav_info)
        self.assertIn("network", nav_info)
        
        # Verify URLs are correctly formatted
        for key, url in nav_info.items():
            self.assertTrue(url.startswith("https://"))
            self.assertIn("console.aws.amazon.com", url)
            
        # Test navigation paths are used correctly in cancellation URLs
        urls = scanner.get_service_specific_cancellation_urls("Amazon OpenSearch Service")
        
        # Check if dashboard link points to collections
        dashboard_url = next((u["url"] for u in urls if u["name"] == "OpenSearch Serverless Dashboard"), None)
        self.assertEqual(dashboard_url, nav_info["collections"])
        
        # Check if data access link is correct
        data_access_url = next((u["url"] for u in urls if u["name"] == "Data Access Policies"), None)
        self.assertEqual(data_access_url, nav_info["data_access"])

    def test_get_opensearch_navigation_info_integration(self):
        """Test that OpenSearch navigation info is correctly integrated in the dashboard generation."""
        scanner = AWSResourceScanner()
        
        # 1. Test navigation info detection
        nav_info = scanner.get_opensearch_navigation_info()
        
        # Verify structure and content
        self.assertIsInstance(nav_info, dict, "Should return a dictionary")
        self.assertIn("collections", nav_info, "Should include collections path")
        self.assertIn("data_access", nav_info, "Should include data access path")
        self.assertIn("identity", nav_info, "Should include identity/SAML path")
        self.assertIn("encryption", nav_info, "Should include encryption path")
        self.assertIn("network", nav_info, "Should include network path")
        
        # 2. Test URL generation for report
        urls = scanner.get_service_specific_cancellation_urls("Amazon OpenSearch Service")
        
        # Check if we have the right structure for the HTML report
        dashboard_entry = next((u for u in urls if u.get("name") == "OpenSearch Serverless Dashboard"), None)
        self.assertIsNotNone(dashboard_entry, "Should include dashboard entry")
        self.assertEqual(dashboard_entry["url"], nav_info["collections"], "Dashboard should link to collections")
        
        # Test data access URL
        data_access_entry = next((u for u in urls if "Data Access" in u.get("name", "")), None)
        self.assertIsNotNone(data_access_entry, "Should include data access entry")
        self.assertEqual(data_access_entry["url"], nav_info["data_access"], "Should use dynamic URL from navigation info")
        
        # 3. Test that all required URLs are generated
        url_types = [u.get("type") for u in urls]
        self.assertIn("primary", url_types, "Should include primary dashboard")
        self.assertIn("config", url_types, "Should include configuration areas")
        self.assertIn("audit", url_types, "Should include audit tools")

if __name__ == '__main__':
    unittest.main()

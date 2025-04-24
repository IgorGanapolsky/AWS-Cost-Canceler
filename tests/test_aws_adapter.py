"""
Tests for AWS Cost Adapter

These tests ensure that the AWS adapter correctly implements the CostDataPort
interface and properly handles fallback to sample data when AWS credentials are invalid.
"""
import os
import unittest
from unittest.mock import patch, MagicMock
import boto3
from botocore.exceptions import ClientError

from src.nova_cost.adapters.aws_cost_adapter import AWSCostAdapter


class TestAWSCostAdapter(unittest.TestCase):
    """Test cases for the AWS Cost Adapter implementation"""

    def setUp(self):
        """Set up test environment before each test"""
        self.adapter = AWSCostAdapter()
    
    def test_get_date_range(self):
        """Test that date range is correctly calculated"""
        start_date, end_date = self.adapter.get_date_range(days_back=30)
        
        # Verify format
        self.assertRegex(start_date, r'^\d{4}-\d{2}-\d{2}$')
        self.assertRegex(end_date, r'^\d{4}-\d{2}-\d{2}$')
    
    @patch('boto3.client')
    def test_get_service_costs_success(self, mock_boto_client):
        """Test successful retrieval of service costs from AWS"""
        # Mock the cost explorer client and its response
        mock_ce = MagicMock()
        mock_boto_client.return_value = mock_ce
        
        # Configure the mock to return a valid response
        mock_ce.get_cost_and_usage.return_value = {
            'ResultsByTime': [{
                'Groups': [
                    {
                        'Keys': ['AWS Lambda'],
                        'Metrics': {'BlendedCost': {'Amount': '10.50'}}
                    },
                    {
                        'Keys': ['Amazon S3'],
                        'Metrics': {'BlendedCost': {'Amount': '5.25'}}
                    }
                ]
            }]
        }
        
        results = self.adapter.get_service_costs(days_back=7)
        
        # Assertions
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['service'], 'AWS Lambda')
        self.assertEqual(results[0]['cost'], 10.50)
        self.assertEqual(results[1]['service'], 'Amazon S3')
        self.assertEqual(results[1]['cost'], 5.25)
    
    @patch('boto3.client')
    def test_get_service_costs_fallback(self, mock_boto_client):
        """Test fallback to sample data when AWS API fails"""
        # Mock the cost explorer client to raise an exception
        mock_ce = MagicMock()
        mock_boto_client.return_value = mock_ce
        
        # Configure the mock to raise an exception
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        mock_ce.get_cost_and_usage.side_effect = ClientError(error_response, 'GetCostAndUsage')
        
        results = self.adapter.get_service_costs(days_back=7)
        
        # Verify we got sample data
        self.assertGreater(len(results), 0)
        self.assertIn('service', results[0])
        self.assertIn('cost', results[0])
        
        # Verify sample data contains expected services
        service_names = [service['service'] for service in results]
        self.assertIn('AWS Skill Builder Individual', service_names)
    
    @patch('boto3.client')
    def test_get_daily_costs_success(self, mock_boto_client):
        """Test successful retrieval of daily costs from AWS"""
        # Mock the cost explorer client and its response
        mock_ce = MagicMock()
        mock_boto_client.return_value = mock_ce
        
        # Configure the mock to return a valid response
        mock_ce.get_cost_and_usage.return_value = {
            'ResultsByTime': [
                {
                    'TimePeriod': {'Start': '2025-04-01'},
                    'Total': {'BlendedCost': {'Amount': '12.34'}}
                },
                {
                    'TimePeriod': {'Start': '2025-04-02'},
                    'Total': {'BlendedCost': {'Amount': '23.45'}}
                }
            ]
        }
        
        results = self.adapter.get_daily_costs(days_back=7)
        
        # Assertions
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], '2025-04-01')
        self.assertEqual(results[0][1], 12.34)
        self.assertEqual(results[1][0], '2025-04-02')
        self.assertEqual(results[1][1], 23.45)
    
    @patch('boto3.client')
    def test_get_daily_costs_fallback(self, mock_boto_client):
        """Test fallback to sample data when AWS API fails"""
        # Mock the cost explorer client to raise an exception
        mock_ce = MagicMock()
        mock_boto_client.return_value = mock_ce
        
        # Configure the mock to raise an exception
        error_response = {'Error': {'Code': 'AccessDeniedException', 'Message': 'Access denied'}}
        mock_ce.get_cost_and_usage.side_effect = ClientError(error_response, 'GetCostAndUsage')
        
        results = self.adapter.get_daily_costs(days_back=7)
        
        # Verify we got sample data
        self.assertGreater(len(results), 0)
        self.assertEqual(len(results[0]), 3)  # (date, cost, service_name)
        
        # Verify date format in sample data
        for date, cost, service in results:
            self.assertRegex(date, r'^\d{4}-\d{2}-\d{2}$')
            self.assertGreaterEqual(cost, 0)


if __name__ == '__main__':
    unittest.main()

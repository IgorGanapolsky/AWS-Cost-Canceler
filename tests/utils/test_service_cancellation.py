"""
Unit tests for the Service Cancellation API
"""
import unittest
from unittest.mock import patch, MagicMock
import boto3
import botocore.session
from botocore.stub import Stubber
import json
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.nova_cost.api.service_cancellation import ServiceCancellationAPI, cancel_service_directly


class TestServiceCancellationAPI(unittest.TestCase):
    """Test the ServiceCancellationAPI class"""
    
    def setUp(self):
        """Set up the test case"""
        self.api = ServiceCancellationAPI()
    
    @patch('boto3.Session')
    def test_init(self, mock_session):
        """Test initialization"""
        api = ServiceCancellationAPI()
        mock_session.assert_called_once()
    
    @patch.object(ServiceCancellationAPI, '_cancel_opensearch')
    def test_cancel_opensearch_service(self, mock_cancel):
        """Test canceling OpenSearch service"""
        # Set up the mock
        mock_cancel.return_value = {"domain_name": "test-domain", "action": "deleted"}
        
        # Call the API
        result = self.api.cancel_service("Amazon OpenSearch Service", "test-domain", "us-east-1")
        
        # Verify the result
        self.assertTrue(result['success'])
        self.assertEqual(result['details']['domain_name'], "test-domain")
        mock_cancel.assert_called_once()
    
    @patch.object(ServiceCancellationAPI, '_cancel_opensearch_serverless')
    def test_cancel_opensearch_serverless(self, mock_cancel):
        """Test canceling OpenSearch Serverless"""
        # Set up the mock
        mock_cancel.return_value = {"collection_id": "test-collection", "action": "deleted"}
        
        # Call the API
        result = self.api.cancel_service("OpenSearch Serverless", "test-collection", "us-east-1")
        
        # Verify the result
        self.assertTrue(result['success'])
        self.assertEqual(result['details']['collection_id'], "test-collection")
        mock_cancel.assert_called_once()
    
    @patch.object(ServiceCancellationAPI, '_cancel_ec2')
    def test_cancel_ec2(self, mock_cancel):
        """Test canceling EC2 instances"""
        # Set up the mock
        mock_cancel.return_value = {"instance_id": "i-12345", "action": "terminated"}
        
        # Call the API
        result = self.api.cancel_service("Amazon EC2", "i-12345", "us-east-1")
        
        # Verify the result
        self.assertTrue(result['success'])
        self.assertEqual(result['details']['instance_id'], "i-12345")
        mock_cancel.assert_called_once()
    
    @patch('boto3.Session')
    def test_cancel_service_error(self, mock_session):
        """Test error handling in cancel_service"""
        # Mock a client error
        mock_client = MagicMock()
        mock_client.delete_domain.side_effect = botocore.exceptions.ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Domain not found"}},
            "DeleteDomain"
        )
        mock_session.return_value.client.return_value = mock_client
        
        # Call the API with an error-inducing input
        result = self.api.cancel_service("Amazon OpenSearch Service", "non-existent-domain", "us-east-1")
        
        # Verify error handling
        self.assertFalse(result['success'])
        self.assertEqual(result['error_code'], "ResourceNotFoundException")
    
    def test_default_cancellation(self):
        """Test the default cancellation for unsupported services"""
        # Call the API with an unsupported service
        result = self.api.cancel_service("Unsupported Service", "resource-id", "us-east-1")
        
        # Verify the default behavior
        self.assertTrue(result['success'])  # It shouldn't fail, just return a not implemented message
        self.assertEqual(result['details']['action'], "not_implemented")
    
    @patch('boto3.Session')
    def test_opensearch_cancellation_implementation(self, mock_session):
        """Test the OpenSearch cancellation implementation"""
        # Set up the mock
        mock_client = MagicMock()
        mock_client.delete_domain.return_value = {
            "DomainStatus": {"DomainName": "test-domain", "Processing": True},
            "DeletionDate": "2024-04-20T12:00:00Z"
        }
        mock_session.return_value.client.return_value = mock_client
        
        # Call the implementation directly
        result = self.api._cancel_opensearch(mock_session.return_value, "test-domain", "us-east-1")
        
        # Verify the implementation
        self.assertEqual(result['domain_name'], "test-domain")
        self.assertEqual(result['action'], "deleted")
        mock_client.delete_domain.assert_called_once_with(DomainName="test-domain")
    
    @patch('boto3.Session')
    def test_cancel_service_directly_function(self, mock_session):
        """Test the cancel_service_directly function"""
        # Set up the mock
        api_instance = MagicMock()
        api_instance.cancel_service.return_value = {
            "success": True,
            "message": "Successfully canceled service",
            "details": {"service_id": "test-service", "action": "deleted"}
        }
        
        with patch('src.nova_cost.api.service_cancellation.ServiceCancellationAPI', return_value=api_instance):
            # Call the function
            result = cancel_service_directly("Test Service", "test-service", "us-east-1")
            
            # Verify the result
            self.assertTrue(result['success'])
            self.assertEqual(result['details']['service_id'], "test-service")
            api_instance.cancel_service.assert_called_once_with("Test Service", "test-service", "us-east-1")


if __name__ == '__main__':
    unittest.main()

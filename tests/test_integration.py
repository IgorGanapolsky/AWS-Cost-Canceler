"""
Integration Tests for Nova Cost

These tests verify that all components work correctly together,
testing the entire pipeline from data retrieval to report generation.
"""
import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock

from src.nova_cost import create_service, generate_report, analyze_costs


class TestEndToEndPipeline(unittest.TestCase):
    """Integration tests for the entire AWS cost reporting pipeline"""
    
    def setUp(self):
        """Set up the test environment"""
        # Mock AWS response data for consistent testing
        self.mock_services = [
            {"service": "AWS Lambda", "cost": 10.50, "details": "Serverless compute", "status": "Active"},
            {"service": "Amazon S3", "cost": 5.25, "details": "Storage", "status": "Active"},
            {"service": "AWS Skill Builder", "cost": 29.00, "details": "Training", "status": "Canceled on 2025-04-15"}
        ]
        
        self.mock_daily_costs = [
            ("2025-04-01", 12.34, "AWS Services"),
            ("2025-04-02", 23.45, "AWS Services")
        ]

    @patch('src.nova_cost.adapters.aws_cost_adapter.AWSCostAdapter.get_service_costs')
    @patch('src.nova_cost.adapters.aws_cost_adapter.AWSCostAdapter.get_daily_costs')
    def test_generate_report_integration(self, mock_daily_costs, mock_service_costs):
        """Test the full report generation pipeline"""
        # Configure mocks to return test data
        mock_service_costs.return_value = self.mock_services
        mock_daily_costs.return_value = self.mock_daily_costs
        
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Generate the report using the public API
            report_path = generate_report(days_back=30, output_path=temp_path, open_report=False)
            
            # Verify report was generated at the correct path
            self.assertEqual(report_path, temp_path)
            self.assertTrue(os.path.exists(temp_path))
            
            # Check that the file has content (basic validation)
            with open(temp_path, 'r') as f:
                content = f.read()
                self.assertIn('<!DOCTYPE html>', content)
                self.assertIn('AWS Cost Report Dashboard', content)
                
                # Verify our mock data is in the report
                self.assertIn('AWS Lambda', content)
                self.assertIn('Amazon S3', content)
                self.assertIn('AWS Skill Builder', content)
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @patch('src.nova_cost.adapters.aws_cost_adapter.AWSCostAdapter.get_service_costs')
    def test_analyze_costs_integration(self, mock_service_costs):
        """Test the cost analysis pipeline"""
        # Configure mock to return test data
        mock_service_costs.return_value = self.mock_services
        
        # Test with a threshold that should return 2 services
        high_cost_services = analyze_costs(threshold=10.0, days_back=30)
        
        # Verify results
        self.assertEqual(len(high_cost_services), 2)
        self.assertEqual(high_cost_services[0]['service'], 'AWS Lambda')
        self.assertEqual(high_cost_services[1]['service'], 'AWS Skill Builder')
        
        # Test with a threshold that should return only 1 service
        high_cost_services = analyze_costs(threshold=20.0, days_back=30)
        
        # Verify results
        self.assertEqual(len(high_cost_services), 1)
        self.assertEqual(high_cost_services[0]['service'], 'AWS Skill Builder')
        
        # Test with a threshold that should return no services
        high_cost_services = analyze_costs(threshold=50.0, days_back=30)
        
        # Verify results
        self.assertEqual(len(high_cost_services), 0)


class TestRegressionScenarios(unittest.TestCase):
    """Test specific scenarios to prevent regressions"""
    
    @patch('src.nova_cost.adapters.aws_cost_adapter.AWSCostAdapter.get_service_costs')
    def test_mixed_status_services(self, mock_service_costs):
        """Test handling of mixed active and canceled services"""
        # Services with mixed active/canceled status
        mock_services = [
            {"service": "AWS Lambda", "cost": 10.50, "details": "Compute", "status": "Active"},
            {"service": "Amazon OpenSearch", "cost": 19.65, "details": "Search", "status": "Canceled on 2025-04-15"},
            {"service": "AWS Skill Builder", "cost": 58.00, "details": "Training", "status": "Canceled on 2025-04-15"}
        ]
        
        mock_service_costs.return_value = mock_services
        
        # Generate the report using the public API
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Generate a report with this mixture of statuses
            report_path = generate_report(days_back=30, output_path=temp_path, open_report=False)
            
            # Verify report generated and has content
            self.assertTrue(os.path.exists(temp_path))
            
            # Check that the generated report correctly handles the statuses
            with open(temp_path, 'r') as f:
                content = f.read()
                
                # Ensure active status is shown
                self.assertIn('Active', content)
                
                # Ensure canceled status is shown
                self.assertIn('Canceled on 2025-04-15', content)
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @patch('src.nova_cost.adapters.aws_cost_adapter.AWSCostAdapter.get_service_costs')
    @patch('src.nova_cost.adapters.aws_cost_adapter.AWSCostAdapter.get_daily_costs')
    def test_zero_cost_handling(self, mock_daily_costs, mock_service_costs):
        """Test handling of services with zero costs"""
        # Services with zero costs
        mock_services = [
            {"service": "AWS Lambda", "cost": 0.0, "details": "Compute", "status": "Active"},
            {"service": "Amazon S3", "cost": 0.00, "details": "Storage", "status": "Active"}
        ]
        
        # Daily costs with zeros
        mock_daily = [
            ("2025-04-01", 0.0, "AWS Services"),
            ("2025-04-02", 0.0, "AWS Services")
        ]
        
        mock_service_costs.return_value = mock_services
        mock_daily_costs.return_value = mock_daily
        
        # Generate the report
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Test that zero costs don't break the report generation
            report_path = generate_report(days_back=30, output_path=temp_path, open_report=False)
            
            # Verify report was generated
            self.assertTrue(os.path.exists(temp_path))
            
            # Also verify cost analysis works with zero costs
            high_cost_services = analyze_costs(threshold=0.1, days_back=30)
            self.assertEqual(len(high_cost_services), 0)
        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == '__main__':
    unittest.main()

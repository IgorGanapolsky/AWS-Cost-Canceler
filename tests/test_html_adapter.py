"""
Tests for HTML Report Adapter

These tests ensure that the HTML report adapter correctly implements 
the ReportGeneratorPort interface and properly generates HTML reports.
"""
import os
import unittest
import tempfile
import datetime
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.nova_cost.adapters.html_report_adapter import HTMLReportAdapter


class TestHTMLReportAdapter(unittest.TestCase):
    """Test cases for the HTML Report Adapter implementation"""

    def setUp(self):
        """Set up test environment before each test"""
        self.adapter = HTMLReportAdapter()
        
        # Sample data for testing
        self.sample_services = [
            {"service": "AWS Lambda", "cost": 10.50, "details": "Serverless compute", "status": "Active"},
            {"service": "Amazon S3", "cost": 5.25, "details": "Storage", "status": "Active"},
            {"service": "AWS Skill Builder", "cost": 29.00, "details": "Training", "status": "Canceled on 2025-04-15"}
        ]
        
        self.sample_daily_costs = [
            ("2025-04-01", 12.34, "AWS Services"),
            ("2025-04-02", 23.45, "AWS Services")
        ]
        
        self.sample_paths = {
            "Lambda": "https://console.aws.amazon.com/lambda",
            "S3": "https://console.aws.amazon.com/s3"
        }
        
        self.sample_resources = {
            "Amazon S3": {
                "resources": [
                    {
                        "name": "my-bucket",
                        "url": "https://s3.console.aws.amazon.com/s3/buckets/my-bucket",
                        "instructions": "Click Delete and confirm"
                    }
                ]
            }
        }
        
        self.sample_relationships = {
            "Claude 3.5 Sonnet": "Amazon Bedrock"
        }
    
    def test_add_data_methods(self):
        """Test that all data addition methods work correctly"""
        # Add all types of data
        self.adapter.add_service_costs(self.sample_services, "2025-03-15", "2025-04-15")
        self.adapter.add_daily_costs(self.sample_daily_costs)
        self.adapter.add_total_cost(100.25)
        self.adapter.add_service_paths(self.sample_paths)
        self.adapter.add_service_resources(self.sample_resources)
        self.adapter.add_service_relationships(self.sample_relationships)
        
        # Verify data was stored correctly
        self.assertEqual(self.adapter.report_data['service_costs'], self.sample_services)
        self.assertEqual(self.adapter.report_data['daily_costs'], self.sample_daily_costs)
        self.assertEqual(self.adapter.report_data['total_cost'], 100.25)
        self.assertEqual(self.adapter.report_data['start_date'], "2025-03-15")
        self.assertEqual(self.adapter.report_data['end_date'], "2025-04-15")
        self.assertEqual(self.adapter.report_data['service_paths'], self.sample_paths)
        self.assertEqual(self.adapter.report_data['service_resources'], self.sample_resources)
        self.assertEqual(self.adapter.report_data['service_relationships'], self.sample_relationships)
    
    @patch('jinja2.Environment')
    def test_generate_report_custom_path(self, mock_env):
        """Test report generation with a custom output path"""
        # Create a temporary directory for the test
        with tempfile.TemporaryDirectory() as temp_dir:
            test_output = os.path.join(temp_dir, "test_report.html")
            
            # Create a fresh adapter with a mocked environment
            adapter = HTMLReportAdapter()
            
            # Replace the jinja environment with our mock
            mock_template = MagicMock()
            mock_env_instance = MagicMock()
            mock_env.return_value = mock_env_instance
            mock_env_instance.get_template.return_value = mock_template
            mock_template.render.return_value = "<html>Test Report</html>"
            adapter.env = mock_env_instance
            
            # Add some test data
            adapter.add_service_costs(self.sample_services, "2025-03-15", "2025-04-15")
            adapter.add_total_cost(100.25)
            
            # Mock the file open operation
            with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
                # Generate the report
                report_path = adapter.generate_report(output_path=test_output)
                
                # Assertions
                self.assertEqual(report_path, test_output)
                
                # Verify open was called with the right path
                mock_file.assert_called_with(test_output, 'w')
                
                # Verify render was called with our data
                mock_template.render.assert_called_once()
                
                # Verify write was called with the template result
                mock_file().write.assert_called_once_with("<html>Test Report</html>")
    
    @patch('jinja2.Environment')
    def test_generate_report_default_path(self, mock_env):
        """Test report generation with the default output path"""
        # Mock the date to get a predictable filename
        with patch('datetime.date') as mock_date:
            mock_today = MagicMock()
            mock_today.strftime.return_value = "2025-04-16"
            mock_date.today.return_value = mock_today
            
            # Create a fresh adapter with a mocked environment
            adapter = HTMLReportAdapter()
            
            # Replace the jinja environment with our mock
            mock_template = MagicMock()
            mock_env_instance = MagicMock()
            mock_env.return_value = mock_env_instance
            mock_env_instance.get_template.return_value = mock_template
            mock_template.render.return_value = "<html>Test Report</html>"
            adapter.env = mock_env_instance
            
            # Add some test data
            adapter.add_service_costs(self.sample_services, "2025-03-15", "2025-04-15")
            adapter.add_total_cost(100.25)
            
            # Mock the file open operation
            with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
                # Generate the report
                report_path = adapter.generate_report()
                
                # Verify the default path structure
                self.assertIn("data/reports", report_path)
                self.assertIn("aws_cost_report_2025-04-16.html", report_path)
                
                # Verify open was called with the right path
                mock_file.assert_called_with(report_path, 'w')
                
                # Verify render was called with our data
                mock_template.render.assert_called_once()
                
                # Verify write was called with the template result
                mock_file().write.assert_called_once_with("<html>Test Report</html>")
    
    def test_template_exists(self):
        """Test that the template file actually exists"""
        # Get the template path from the adapter
        template_dir = self.adapter.template_dir
        template_path = os.path.join(template_dir, "report_template.html")
        
        # Check that the template exists
        self.assertTrue(os.path.exists(template_path), 
                        f"Template file doesn't exist at {template_path}")


if __name__ == '__main__':
    unittest.main()

"""
Tests for the Cost Analysis Service

These tests ensure that the Cost Analysis Service correctly implements
the core business logic for analyzing AWS costs and generating reports.
"""
import unittest
from unittest.mock import MagicMock, patch

from src.nova_cost.domain.services import CostAnalysisService


class TestCostAnalysisService(unittest.TestCase):
    """Test cases for the Cost Analysis Service"""

    def setUp(self):
        """Set up test environment before each test"""
        # Create mock implementations of the ports
        self.mock_cost_data = MagicMock()
        self.mock_report_generator = MagicMock()
        self.mock_service_metadata = MagicMock()
        
        # Sample test data
        self.sample_services = [
            {"service": "AWS Lambda", "cost": 10.50, "details": "Serverless compute", "status": "Active"},
            {"service": "Amazon S3", "cost": 5.25, "details": "Storage", "status": "Active"},
            {"service": "AWS Skill Builder", "cost": 29.00, "details": "Training", "status": "Canceled on 2025-04-15"}
        ]
        
        self.sample_daily_costs = [
            ("2025-04-01", 12.34, "AWS Services"),
            ("2025-04-02", 23.45, "AWS Services")
        ]
        
        # Configure the mock cost data port
        self.mock_cost_data.get_service_costs.return_value = self.sample_services
        self.mock_cost_data.get_daily_costs.return_value = self.sample_daily_costs
        self.mock_cost_data.get_date_range.return_value = ("2025-03-15", "2025-04-15")
        
        # Configure the mock service metadata port
        self.mock_service_metadata.get_service_paths.return_value = {
            "Lambda": "https://console.aws.amazon.com/lambda",
            "S3": "https://console.aws.amazon.com/s3"
        }
        self.mock_service_metadata.get_service_resources.return_value = {
            "Amazon S3": {"resources": [{"name": "my-bucket", "url": "https://example.com"}]}
        }
        self.mock_service_metadata.get_service_relationships.return_value = {
            "Claude 3.5 Sonnet": "Amazon Bedrock"
        }
        
        # Create the service with mock dependencies
        self.service = CostAnalysisService(
            cost_data_port=self.mock_cost_data,
            report_generator_port=self.mock_report_generator,
            service_metadata_port=self.mock_service_metadata
        )
    
    def test_analyze_costs(self):
        """Test that cost analysis correctly identifies high-cost services"""
        # Test with threshold of 10.0
        high_cost_services = self.service.analyze_costs(days_back=30, threshold=10.0)
        
        # Assertions
        self.assertEqual(len(high_cost_services), 2)
        self.assertIn(self.sample_services[0], high_cost_services)  # AWS Lambda (10.50)
        self.assertIn(self.sample_services[2], high_cost_services)  # AWS Skill Builder (29.00)
        self.assertNotIn(self.sample_services[1], high_cost_services)  # Amazon S3 (5.25)
        
        # Verify the cost data port was called correctly
        self.mock_cost_data.get_service_costs.assert_called_once_with(days_back=30)
    
    def test_analyze_costs_no_results(self):
        """Test cost analysis when no services exceed the threshold"""
        # Test with very high threshold
        high_cost_services = self.service.analyze_costs(days_back=30, threshold=50.0)
        
        # Assertions
        self.assertEqual(len(high_cost_services), 0)
    
    def test_generate_cost_report(self):
        """Test report generation with all data correctly passed to the report generator"""
        # Configure the mock report generator
        self.mock_report_generator.generate_report.return_value = "/path/to/report.html"
        
        # Generate the report
        report_path = self.service.generate_cost_report(days_back=30)
        
        # Assertions
        self.assertEqual(report_path, "/path/to/report.html")
        
        # Verify the cost data port methods were called
        self.mock_cost_data.get_service_costs.assert_called_once_with(days_back=30)
        self.mock_cost_data.get_daily_costs.assert_called_once_with(days_back=30)
        self.mock_cost_data.get_date_range.assert_called_once_with(30)  # Using positional parameter
        
        # Verify the service metadata port methods were called
        self.mock_service_metadata.get_service_paths.assert_called_once()
        self.mock_service_metadata.get_service_resources.assert_called_once()
        self.mock_service_metadata.get_service_relationships.assert_called_once()
        
        # Verify the report generator methods were called with the right data
        self.mock_report_generator.add_service_costs.assert_called_once()
        self.mock_report_generator.add_daily_costs.assert_called_once()
        self.mock_report_generator.add_total_cost.assert_called_once()
        self.mock_report_generator.add_service_paths.assert_called_once()
        self.mock_report_generator.add_service_resources.assert_called_once()
        self.mock_report_generator.add_service_relationships.assert_called_once()
        self.mock_report_generator.generate_report.assert_called_once()
        
        # Verify the total cost calculation is based on daily costs
        expected_total = sum(cost for _, cost, _ in self.sample_daily_costs)  # 12.34 + 23.45 = 35.79
        self.mock_report_generator.add_total_cost.assert_called_once_with(expected_total)


if __name__ == '__main__':
    unittest.main()

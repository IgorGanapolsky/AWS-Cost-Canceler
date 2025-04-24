"""
Test HTML Report Enhanced Features

These tests ensure that the HTML report includes all required enhanced features:
- Detailed tooltips with meaningful information
- Properly sized and proportioned service breakdown chart
- Threshold analysis with clear period information
- All services properly displayed
"""
import os
import unittest
from unittest.mock import patch, MagicMock
import datetime
import re
from pathlib import Path
import tempfile

from src.nova_cost.adapters.html_report_adapter import HTMLReportAdapter


class TestHTMLReportEnhanced(unittest.TestCase):
    """Test enhanced features of the HTML report"""
    
    def setUp(self):
        """Set up test data"""
        self.adapter = HTMLReportAdapter()
        
        # Mock service cost data
        self.service_costs = [
            {"service": "Amazon OpenSearch Service", "cost": 36.50, "status": "Active", "details": "Search service"},
            {"service": "Amazon Bedrock", "cost": 9.12, "status": "Active", "details": "AI service"},
            {"service": "Claude 3.5 Sonnet", "cost": 8.02, "status": "Active", "details": "LLM model"}
        ]
        
        # Mock daily cost data
        self.daily_costs = [
            ("2025-03-17", 2.5, "AWS Services"),
            ("2025-03-18", 3.0, "AWS Services"),
            ("2025-04-15", 6.8, "AWS Services"),
            ("2025-04-16", 4.2, "AWS Services")
        ]
        
        # Set report date range
        self.start_date = "2025-03-17"
        self.end_date = "2025-04-16"
        
        # Mock service paths for console links
        self.service_paths = {
            "Amazon OpenSearch Service": "/opensearch",
            "Amazon Bedrock": "/bedrock",
            "Claude 3.5 Sonnet": "/bedrock/claude"
        }
        
        # Mock service resources for cancellation
        self.service_resources = {
            "Amazon OpenSearch Service": [
                {"name": "search-dev", "resource_id": "dev123"},
                {"name": "search-prod", "resource_id": "prod456"}
            ]
        }
    
    def generate_test_report(self):
        """Generate a test report and return the HTML content"""
        # Add all data to the adapter
        self.adapter.add_service_costs(self.service_costs, self.start_date, self.end_date)
        self.adapter.add_daily_costs(self.daily_costs)
        self.adapter.add_total_cost(sum(cost for _, cost, _ in self.daily_costs))
        self.adapter.add_service_paths(self.service_paths)
        self.adapter.add_service_resources(self.service_resources)
        
        # Create temporary file for the report
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Generate the report
            self.adapter.generate_report(temp_path)
            
            # Read the HTML content
            with open(temp_path, 'r') as f:
                html_content = f.read()
                
            return html_content
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_service_breakdown_chart_includes_all_services(self):
        """Test that the service breakdown chart includes all services"""
        html_content = self.generate_test_report()
        
        # Check that all services are included in the chart data
        for service in self.service_costs:
            service_name = service["service"]
            self.assertIn(service_name, html_content, f"Service '{service_name}' not found in chart data")
    
    def test_daily_cost_chart_has_enhanced_tooltips(self):
        """Test that the daily cost chart has enhanced tooltips with meaningful info"""
        html_content = self.generate_test_report()
        
        # Check for enhanced tooltip callbacks in the daily cost chart
        self.assertIn("tooltip: {", html_content)
        self.assertIn("callbacks: {", html_content)
        self.assertIn("title: function", html_content)
        self.assertIn("label: function", html_content)
        
        # Check that the tooltip includes cost
        self.assertIn("Cost: $", html_content)
        
        # Check that tooltip includes services
        self.assertIn("Services:", html_content)
    
    def test_threshold_analysis_shows_period_information(self):
        """Test that the threshold analysis section shows period information"""
        html_content = self.generate_test_report()
        
        # Check for period information
        period_text = f"Costs for period: {self.start_date} to {self.end_date}"
        self.assertIn(period_text, html_content)
        
        # Check for days count
        days_text = "(31 days)"
        self.assertIn(days_text, html_content)
        
        # Check for 'over threshold' column
        self.assertIn("OVER THRESHOLD", html_content)
    
    def test_cost_column_includes_period_clarification(self):
        """Test that the cost column includes period clarification"""
        html_content = self.generate_test_report()
        
        # Check that the cost column includes period clarification
        self.assertIn("COST (31-day total)", html_content)
    
    def test_service_breakdown_chart_has_title_with_date_range(self):
        """Test that the service breakdown chart has a title with date range"""
        html_content = self.generate_test_report()
        
        # Check for chart title with date range
        title_text = f"Service Cost Distribution ({self.start_date} to {self.end_date})"
        self.assertIn(title_text, html_content)
    
    def test_service_breakdown_chart_has_percentage_information(self):
        """Test that the service breakdown chart tooltips include percentage information"""
        html_content = self.generate_test_report()
        
        # Check for percentage calculation in tooltips
        self.assertIn("percentage = ((service.cost / serviceCosts.reduce((a, b) => a + b, 0)) * 100).toFixed(1)", html_content)
        self.assertIn("Cost: $${service.cost.toFixed(2)} (${percentage}%)", html_content)
    
    def test_service_breakdown_chart_has_datalabels(self):
        """Test that the service breakdown chart shows percentage labels directly on the chart"""
        html_content = self.generate_test_report()
        
        # Check for Chart.js datalabels plugin
        self.assertIn("datalabels: {", html_content)
        self.assertIn("formatter: function(value, context)", html_content)
        self.assertIn("const percentage =", html_content)
        self.assertIn("return `${percentage}%`;", html_content)


if __name__ == '__main__':
    unittest.main()

"""
Tests for CLI Adapter

These tests ensure that the CLI interface correctly handles user input
and properly delegates to the underlying services.
"""
import unittest
import sys
from io import StringIO
from unittest.mock import patch, MagicMock

from src.nova_cost.adapters.cli_adapter import CLIAdapter, main


class TestCLIAdapter(unittest.TestCase):
    """Test cases for the CLI adapter"""
    
    def setUp(self):
        """Set up test environment"""
        # Create a mock service for testing
        self.mock_cost_analysis_service = MagicMock()
        
        # Configure the mock service
        self.mock_cost_analysis_service.generate_cost_report.return_value = "/path/to/report.html"
        self.mock_cost_analysis_service.analyze_costs.return_value = [
            {"service": "AWS Lambda", "cost": 10.50, "details": "Compute", "status": "Active"},
            {"service": "Amazon S3", "cost": 5.25, "details": "Storage", "status": "Active"}
        ]
    
    @patch('src.nova_cost.adapters.cli_adapter.CostAnalysisService')
    def test_cli_report_command(self, mock_service_class):
        """Test the 'report' command"""
        # Set up the mock service
        mock_service_instance = MagicMock()
        mock_service_instance.generate_cost_report.return_value = "/path/to/report.html"
        mock_service_class.return_value = mock_service_instance
        
        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            # Run the CLI with report command - note that --open is a flag, not a value
            cli = CLIAdapter()
            exit_code = cli.run(["report", "--days", "15", "--output", "/custom/path.html"])
            
            # Verify success exit code
            self.assertEqual(exit_code, 0)
            
            # Verify the service was called with the right parameters
            mock_service_instance.generate_cost_report.assert_called_once_with(
                days_back=15,
                output_path="/custom/path.html"
            )
            
            # Verify output contains report path
            self.assertIn("/path/to/report.html", captured_output.getvalue())
        finally:
            sys.stdout = sys.__stdout__
    
    @patch('src.nova_cost.adapters.cli_adapter.CostAnalysisService')
    def test_cli_analyze_command(self, mock_service_class):
        """Test the 'analyze' command"""
        # Set up the mock service
        mock_service_instance = MagicMock()
        mock_service_instance.analyze_costs.return_value = [
            {"service": "AWS Lambda", "cost": 10.50, "details": "Compute", "status": "Active"},
            {"service": "Amazon S3", "cost": 5.25, "details": "Storage", "status": "Active"}
        ]
        mock_service_class.return_value = mock_service_instance
        
        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            # Run the CLI with analyze command
            cli = CLIAdapter()
            exit_code = cli.run(["analyze", "--days", "15", "--threshold", "5.0"])
            
            # Verify success exit code
            self.assertEqual(exit_code, 0)
            
            # Verify the service was called with the right parameters
            mock_service_instance.analyze_costs.assert_called_once_with(
                days_back=15,
                threshold=5.0
            )
            
            # Verify output contains service names
            output = captured_output.getvalue()
            self.assertIn("AWS Lambda", output)
            self.assertIn("Amazon S3", output)
        finally:
            sys.stdout = sys.__stdout__
    
    @patch('src.nova_cost.adapters.cli_adapter.CostAnalysisService')
    def test_cli_error_handling(self, mock_service_class):
        """Test error handling in the CLI"""
        # Set up the mock service to raise an exception
        mock_service_instance = MagicMock()
        mock_service_instance.generate_cost_report.side_effect = Exception("Service error")
        mock_service_class.return_value = mock_service_instance
        
        # Capture stdout
        captured_output = StringIO()
        sys.stdout = captured_output
        
        try:
            # Run the CLI expecting an error
            cli = CLIAdapter()
            exit_code = cli.run(["report"])
            
            # Verify error exit code
            self.assertEqual(exit_code, 1)
            
            # Verify error message
            self.assertIn("Error generating report", captured_output.getvalue())
        finally:
            sys.stdout = sys.__stdout__
    
    @patch('src.nova_cost.adapters.cli_adapter.CLIAdapter')
    def test_main_function(self, mock_cli_adapter):
        """Test the main entry point"""
        # Set up the mock CLI adapter
        mock_adapter_instance = MagicMock()
        mock_adapter_instance.run.return_value = 0
        mock_cli_adapter.return_value = mock_adapter_instance
        
        # Call the main function
        result = main(["analyze", "--threshold", "5.0"])
        
        # Verify exit code
        self.assertEqual(result, 0)
        
        # Verify adapter was called with correct args
        mock_adapter_instance.run.assert_called_once_with(["analyze", "--threshold", "5.0"])


class TestCLIArgumentValidation(unittest.TestCase):
    """Test argument validation in the CLI"""
    
    @patch('src.nova_cost.adapters.cli_adapter.CostAnalysisService')
    def test_days_validation(self, mock_service_class):
        """Test validation of days parameter"""
        # Set up the mock service
        mock_service_instance = MagicMock()
        mock_service_class.return_value = mock_service_instance
        
        # Create a mock parser that will validate days
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            # Set up a mock ArgumentParser that will validate days
            mock_parse_args.side_effect = SystemExit(2)
            
            # Run the CLI with invalid days
            cli = CLIAdapter()
            
            # Capture stdout to suppress error messages
            captured_output = StringIO()
            sys.stderr = captured_output
            
            try:
                # This should exit due to argparse validation
                with self.assertRaises(SystemExit):
                    cli.run(["report", "--days", "-5"])
                
                # After exception, service should not be called
                mock_service_instance.generate_cost_report.assert_not_called()
            finally:
                sys.stderr = sys.__stderr__
    
    @patch('src.nova_cost.adapters.cli_adapter.CostAnalysisService')
    def test_threshold_validation(self, mock_service_class):
        """Test validation of threshold parameter"""
        # Set up the mock service
        mock_service_instance = MagicMock()
        mock_service_class.return_value = mock_service_instance
        
        # Create a mock parser that will validate threshold
        with patch('argparse.ArgumentParser.parse_args') as mock_parse_args:
            # Set up a mock ArgumentParser that will validate threshold
            mock_parse_args.side_effect = SystemExit(2)
            
            # Run the CLI with invalid threshold
            cli = CLIAdapter()
            
            # Capture stdout to suppress error messages
            captured_output = StringIO()
            sys.stderr = captured_output
            
            try:
                # This should exit due to argparse validation
                with self.assertRaises(SystemExit):
                    cli.run(["analyze", "--threshold", "invalid"])
                
                # After exception, service should not be called
                mock_service_instance.analyze_costs.assert_not_called()
            finally:
                sys.stderr = sys.__stderr__


if __name__ == '__main__':
    unittest.main()

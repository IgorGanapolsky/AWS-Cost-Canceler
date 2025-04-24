"""
CLI Adapter - Primary adapter for the command line interface

This adapter implements the command line interface for the Nova Cost application,
following Hexagonal Architecture principles to separate UI concerns from domain logic.
"""
import argparse
import sys
import webbrowser
from typing import List, Optional, Dict, Any

from ..domain.services import CostAnalysisService
from ..adapters.aws_cost_adapter import AWSCostAdapter
from ..adapters.html_report_adapter import HTMLReportAdapter


class CLIAdapter:
    """Command Line Interface adapter for Nova Cost"""
    
    def __init__(self):
        """Initialize the CLI adapter with required services"""
        # Set up the adapters
        cost_adapter = AWSCostAdapter()
        report_adapter = HTMLReportAdapter()
        
        # Create the domain service
        self.cost_analysis_service = CostAnalysisService(
            cost_data_port=cost_adapter,
            report_generator_port=report_adapter,
            service_metadata_port=cost_adapter  # AWS adapter also implements metadata port
        )
    
    def run(self, argv: Optional[List[str]] = None) -> int:
        """
        Run the CLI adapter with the given arguments
        
        Args:
            argv: Command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        parser = argparse.ArgumentParser(description="AWS Cost Analysis Tool")
        subparsers = parser.add_subparsers(dest="command", help="Command to run")
        
        # Report command
        report_parser = subparsers.add_parser("report", help="Generate cost report")
        report_parser.add_argument("--days", type=int, default=30, help="Days of data to analyze")
        report_parser.add_argument("--output", help="Output file path for the report")
        report_parser.add_argument("--open", action="store_true", default=True, help="Open the report after generation")
        
        # Analyze command
        analyze_parser = subparsers.add_parser("analyze", help="Analyze costs")
        analyze_parser.add_argument("--threshold", type=float, default=10.0, help="Cost threshold")
        analyze_parser.add_argument("--days", type=int, default=30, help="Days of data to analyze")
        
        args = parser.parse_args(argv)
        
        if args.command == "report":
            try:
                # Generate report using domain service
                report_path = self.cost_analysis_service.generate_cost_report(
                    days_back=args.days,
                    output_path=args.output
                )
                
                # Open report if requested
                if args.open and report_path:
                    webbrowser.open(f"file://{report_path}")
                
                print(f"Report generated: {report_path}")
                return 0
            except Exception as e:
                print(f"Error generating report: {str(e)}")
                return 1
                
        elif args.command == "analyze":
            try:
                # Analyze costs using domain service
                high_cost_services = self.cost_analysis_service.analyze_costs(
                    days_back=args.days,
                    threshold=args.threshold
                )
                
                # Print analysis results
                if high_cost_services:
                    print(f"\n=== Services above ${args.threshold:.2f} threshold ===")
                    for service in high_cost_services:
                        print(f"{service['service']}: ${service['cost']:.2f}")
                else:
                    print(f"\nNo services found above ${args.threshold:.2f} threshold")
                
                return 0
            except Exception as e:
                print(f"Error analyzing costs: {str(e)}")
                return 1
        else:
            parser.print_help()
            return 1


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI"""
    cli = CLIAdapter()
    return cli.run(argv)

"""
Public API for Nova Cost - AWS Cost Analysis Tool
"""
import os
import webbrowser
from typing import Optional, Dict, List, Any, Tuple, Union
from pathlib import Path

from nova_cost.services.aws_cost_monitor import AWSCostMonitor
from nova_cost.services.report_generator import HTMLReportGenerator


def generate_report(
    days_back: int = 30,
    output_path: Optional[str] = None,
    open_report: bool = True
) -> str:
    """
    Generate an AWS cost report for the specified time period.
    
    Args:
        days_back: Number of days to analyze
        output_path: Optional custom output path for the report
        open_report: Whether to open the report in a browser after generation
        
    Returns:
        Path to the generated report
    """
    # Initialize services
    cost_monitor = AWSCostMonitor()
    report_generator = HTMLReportGenerator()
    
    # Get the start and end dates
    services = cost_monitor.get_service_costs(days_back=days_back)
    daily_costs = cost_monitor.get_daily_costs(days_back=days_back)
    
    # Calculate total cost
    total_cost = sum(cost for _, cost, _ in daily_costs)
    
    # Set report start/end dates
    start_date, end_date = cost_monitor.get_date_range(days_back)
    
    # Add data to the report generator
    report_generator.add_service_costs(services, start_date, end_date)
    report_generator.add_daily_costs(daily_costs)
    report_generator.add_total_cost(total_cost)
    
    # Add AWS console paths for direct links
    service_paths = cost_monitor.get_service_paths()
    report_generator.add_service_paths(service_paths)
    
    # Add service relationships for consolidation (e.g., Claude models under Bedrock)
    service_relationships = cost_monitor.get_service_relationships()
    report_generator.add_service_relationships(service_relationships)
    
    # Add service resources for detailed cancellation
    service_resources = cost_monitor.get_service_resources()
    report_generator.add_service_resources(service_resources)
    
    # Generate the report
    report_path = report_generator.generate_html_report(output_path)
    
    # Open the report if requested
    if open_report and report_path:
        webbrowser.open(f"file://{report_path}")
    
    return report_path


def analyze_costs(threshold: float = 10.0, days_back: int = 30) -> List[Dict[str, Any]]:
    """
    Analyze AWS costs and identify services above the specified threshold.
    
    Args:
        threshold: Cost threshold in USD
        days_back: Number of days to analyze
        
    Returns:
        List of services with costs above the threshold
    """
    # Initialize cost monitor
    cost_monitor = AWSCostMonitor()
    
    # Get service costs
    services = cost_monitor.get_service_costs(days_back=days_back)
    
    # Filter services above threshold
    high_cost_services = [
        service for service in services 
        if service["cost"] > threshold
    ]
    
    # Print analysis
    if high_cost_services:
        print(f"\n=== Services above ${threshold:.2f} threshold ===")
        for service in high_cost_services:
            print(f"{service['service']}: ${service['cost']:.2f}")
    else:
        print(f"\nNo services found above ${threshold:.2f} threshold")
    
    return high_cost_services

"""
Nova Cost - AWS Cost Analysis and Reporting Tool

A comprehensive tool for analyzing AWS costs and generating interactive reports.
Built using Hexagonal Architecture (Ports and Adapters pattern) to ensure
clear separation of concerns and high testability.
"""

__version__ = "1.0.0"

# Convenience imports for public API
from .adapters.cli_adapter import main
from .domain.services import CostAnalysisService
from .adapters.aws_cost_adapter import AWSCostAdapter
from .adapters.html_report_adapter import HTMLReportAdapter
from .api.service_cancellation import ServiceCancellationAPI, cancel_service_directly


def create_service():
    """
    Factory method to create the main domain service with required adapters.
    
    Returns:
        Configured CostAnalysisService instance
    """
    cost_adapter = AWSCostAdapter()
    report_adapter = HTMLReportAdapter(cost_adapter)
    
    return CostAnalysisService(
        cost_data_port=cost_adapter,
        report_generator_port=report_adapter,
        service_metadata_port=cost_adapter
    )


def generate_report(days_back=30, output_path=None, open_report=True):
    """
    Generate an AWS cost report.
    
    Args:
        days_back: Number of days to analyze
        output_path: Optional custom output path
        open_report: Whether to open report in browser
    
    Returns:
        Path to the generated report
    """
    service = create_service()
    return service.generate_cost_report(days_back, output_path, open_report)


def analyze_costs(threshold=10.0, days_back=30):
    """
    Analyze AWS costs and identify services above threshold.
    
    Args:
        threshold: Cost threshold in USD
        days_back: Number of days to analyze
    
    Returns:
        List of high-cost services
    """
    service = create_service()
    return service.analyze_service_costs(threshold, days_back)


def run_api(host='0.0.0.0', port=5000, debug=False):
    """
    Run the Nova Cost API server.
    
    Args:
        host: Host to bind to
        port: Port to listen on
        debug: Whether to run in debug mode
        
    Returns:
        The Flask app instance
    """
    from .api.app import create_app
    app = create_app()
    app.run(host=host, port=port, debug=debug)
    return app


def cancel_service(service_name, service_id=None, region="us-east-1"):
    """
    Cancel an AWS service directly.
    
    Args:
        service_name: Name of the service to cancel
        service_id: ID of the specific resource to cancel (optional)
        region: AWS region where the resource is deployed
        
    Returns:
        Dictionary with cancellation status and details
    """
    return cancel_service_directly(service_name, service_id, region)


__all__ = [
    "CostAnalysisService",
    "AWSCostAdapter", 
    "HTMLReportAdapter",
    "create_service",
    "generate_report",
    "analyze_costs",
    "run_api",
    "cancel_service",
    "ServiceCancellationAPI"
]
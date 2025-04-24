"""
Domain Services - Core business logic for Nova Cost application

This module contains the core business logic for cost analysis and reporting,
isolated from external concerns like UI and data sources according to 
Hexagonal Architecture principles.
"""
from typing import Dict, List, Tuple, Any, Optional
from datetime import date

from ..domain.ports import CostDataPort, ReportGeneratorPort, ServiceMetadataPort


class CostAnalysisService:
    """
    Core domain service for analyzing AWS costs
    
    This service coordinates between the data access port and reporting port
    to implement the core business logic for cost analysis.
    """
    
    def __init__(
        self, 
        cost_data_port: CostDataPort,
        report_generator_port: ReportGeneratorPort,
        service_metadata_port: ServiceMetadataPort
    ):
        """Initialize with required ports"""
        self.cost_data_port = cost_data_port
        self.report_generator_port = report_generator_port
        self.service_metadata_port = service_metadata_port
    
    def analyze_costs(self, days_back: int = 30, threshold: float = 10.0) -> List[Dict[str, Any]]:
        """
        Analyze costs and identify services above threshold
        
        Args:
            days_back: Number of days to analyze
            threshold: Cost threshold in USD
            
        Returns:
            List of high-cost services
        """
        # Get service costs from data port
        services = self.cost_data_port.get_service_costs(days_back=days_back)
        
        # Filter services above threshold
        high_cost_services = [
            service for service in services 
            if service["cost"] > threshold
        ]
        
        return high_cost_services
    
    def generate_cost_report(
        self, 
        days_back: int = 30,
        output_path: Optional[str] = None,
        open_report: bool = True
    ) -> str:
        """
        Generate a comprehensive cost report
        
        Args:
            days_back: Number of days to analyze
            output_path: Optional custom output path
            open_report: Whether to open the report in browser
            
        Returns:
            Path to the generated report
        """
        # Get cost data
        services = self.cost_data_port.get_service_costs(days_back=days_back)
        daily_costs = self.cost_data_port.get_daily_costs(days_back=days_back)
        start_date, end_date = self.cost_data_port.get_date_range(days_back)
        
        # Calculate total cost
        total_cost = sum(cost for _, cost, _ in daily_costs)
        
        # Add data to report generator
        self.report_generator_port.add_service_costs(services, start_date, end_date)
        self.report_generator_port.add_daily_costs(daily_costs)
        self.report_generator_port.add_total_cost(total_cost)
        
        # Add service metadata
        self._add_service_metadata()
        
        # Generate and return the report
        return self.report_generator_port.generate_report(output_path=output_path, open_report=open_report)
    
    def _add_service_metadata(self) -> None:
        """Add service metadata to the report"""
        # Get metadata from the service metadata port
        service_paths = self.service_metadata_port.get_service_paths()
        service_relationships = self.service_metadata_port.get_service_relationships()
        service_resources = self.service_metadata_port.get_service_resources()
        
        # Add metadata to the report via report generator port
        self.report_generator_port.add_service_paths(service_paths)
        self.report_generator_port.add_service_relationships(service_relationships)
        self.report_generator_port.add_service_resources(service_resources)

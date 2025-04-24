"""
Domain Ports - Interfaces for the Nova Cost application

This module defines the abstract interfaces (ports) that connect the domain
to external systems and UI components. Following Hexagonal Architecture principles,
these interfaces ensure the domain logic remains isolated from implementation details.
"""
from abc import ABC, abstractmethod
from datetime import date
from typing import Dict, List, Tuple, Any, Optional


class CostDataPort(ABC):
    """Port for retrieving cost data from a cost tracking system"""
    
    @abstractmethod
    def get_daily_costs(self, days_back: int = 30) -> List[Tuple[str, float, str]]:
        """
        Get daily costs for the specified time period
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of (date, cost, service_name) tuples
        """
        pass
    
    @abstractmethod
    def get_service_costs(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Get costs by service for the specified time period
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of dictionaries with service cost details
        """
        pass
    
    @abstractmethod
    def get_date_range(self, days_back: int = 30) -> Tuple[str, str]:
        """
        Get formatted start and end dates for the specified time range
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Tuple of (start_date, end_date) as ISO format strings
        """
        pass


class ReportGeneratorPort(ABC):
    """Port for generating reports from cost data"""
    
    @abstractmethod
    def add_service_costs(self, services: List[Dict[str, Any]], start_date: str, end_date: str) -> None:
        """
        Add service cost data to the report
        
        Args:
            services: List of service cost dictionaries
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        """
        pass
    
    @abstractmethod
    def add_daily_costs(self, daily_costs: List[Tuple[str, float, str]]) -> None:
        """
        Add daily cost data to the report
        
        Args:
            daily_costs: List of (date, cost, service) tuples
        """
        pass
    
    @abstractmethod
    def add_total_cost(self, total_cost: float) -> None:
        """
        Add total cost to the report
        
        Args:
            total_cost: Total cost amount
        """
        pass
    
    @abstractmethod
    def generate_report(self, output_path: Optional[str] = None) -> str:
        """
        Generate the final report
        
        Args:
            output_path: Optional custom output path for the report
            
        Returns:
            Path to the generated report
        """
        pass


class ServiceMetadataPort(ABC):
    """Port for retrieving service metadata"""
    
    @abstractmethod
    def get_service_paths(self) -> Dict[str, str]:
        """
        Get console paths for services
        
        Returns:
            Dictionary mapping service names to console URLs
        """
        pass
    
    @abstractmethod
    def get_service_relationships(self) -> Dict[str, str]:
        """
        Get service relationships for consolidation
        
        Returns:
            Dictionary mapping services to their parent services
        """
        pass
    
    @abstractmethod
    def get_service_resources(self) -> Dict[str, Dict]:
        """
        Get detailed resources for each service
        
        Returns:
            Nested dictionary of service resources
        """
        pass

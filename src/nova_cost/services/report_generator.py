"""
HTML Report Generator Service
Generates interactive HTML reports for AWS cost data
"""
import os
import datetime
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


class HTMLReportGenerator:
    """Generate HTML reports for AWS cost data"""
    
    def __init__(self):
        """Initialize the HTML Report Generator"""
        self.report_data = {
            'service_costs': [],
            'daily_costs': [],
            'total_cost': 0,
            'start_date': '',
            'end_date': '',
            'service_paths': {},
            'service_resources': {},
            'service_relationships': {}
        }
        
        # Set up Jinja2 environment
        package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.template_dir = os.path.join(package_dir, 'templates')
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
    
    def add_service_costs(self, services: List[Dict[str, Any]], start_date: str, end_date: str) -> None:
        """
        Add service cost data to the report
        
        Args:
            services: List of service cost dictionaries
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
        """
        self.report_data['service_costs'] = services
        self.report_data['start_date'] = start_date
        self.report_data['end_date'] = end_date
    
    def add_daily_costs(self, daily_costs: List[Tuple[str, float, str]]) -> None:
        """
        Add daily cost data to the report
        
        Args:
            daily_costs: List of (date, cost, service) tuples
        """
        self.report_data['daily_costs'] = daily_costs
    
    def add_total_cost(self, total_cost: float) -> None:
        """
        Add total cost to the report
        
        Args:
            total_cost: Total cost amount
        """
        self.report_data['total_cost'] = total_cost
    
    def add_service_paths(self, service_paths: Dict[str, str]) -> None:
        """
        Add service paths for direct links
        
        Args:
            service_paths: Dictionary mapping service names to console URLs
        """
        self.report_data['service_paths'] = service_paths
    
    def add_service_resources(self, service_resources: Dict[str, Dict]) -> None:
        """
        Add service resources for cancellation links
        
        Args:
            service_resources: Nested dictionary of service resources
        """
        self.report_data['service_resources'] = service_resources
    
    def add_service_relationships(self, service_relationships: Dict[str, str]) -> None:
        """
        Add service relationships for consolidation
        
        Args:
            service_relationships: Dictionary mapping services to parent services
        """
        self.report_data['service_relationships'] = service_relationships
    
    def generate_html_report(self, output_path: Optional[str] = None) -> str:
        """
        Generate the HTML report with all data
        
        Args:
            output_path: Optional custom output path for the report
            
        Returns:
            Path to the generated report
        """
        # Determine output path
        if output_path:
            # Use custom path if provided
            report_path = output_path
            os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
        else:
            # Default path in data/reports directory
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            reports_dir = os.path.join(base_dir, 'data', 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            # Generate report filename with today's date
            today = datetime.date.today().strftime('%Y-%m-%d')
            report_filename = f'aws_cost_report_{today}.html'
            report_path = os.path.join(reports_dir, report_filename)
        
        # Get the template
        template = self.env.get_template('report_template.html')
        
        # Render the template with data
        html_content = template.render(**self.report_data)
        
        # Write the HTML to file
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        print(f"Report generated at: {report_path}")
        return report_path

#!/usr/bin/env python3
"""
HTML Report Generator for AWS Cost Monitor

This module generates beautiful HTML reports with charts and visualizations
for AWS cost data. It's designed to work with the aws_cost_monitor.py script.
"""

import os
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# For HTML generation
from jinja2 import Template

# For chart generation
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


class HTMLReportGenerator:
    """Generate beautiful HTML reports for AWS cost data."""
    
    def __init__(self, title: str = "AWS Cost Analysis Report"):
        """Initialize the HTML report generator.
        
        Args:
            title: The title of the HTML report
        """
        self.title = title
        self.report_data = {}
        self.charts = []
        
        # Check if required libraries are available
        if not PLOTLY_AVAILABLE:
            print("Warning: Plotly is not installed. Charts will not be generated.")
            print("Install with: pip install plotly")
    
    def add_monthly_costs(self, monthly_costs: List[Dict[str, Any]]):
        """Add monthly cost data to the report.
        
        Args:
            monthly_costs: List of monthly cost data dictionaries
        """
        self.report_data['monthly_costs'] = monthly_costs
    
    def add_service_costs(self, service_costs: List[Dict[str, Any]]):
        """Add service cost data to the report.
        
        Args:
            service_costs: List of service cost data dictionaries
        """
        self.report_data['service_costs'] = service_costs
    
    def add_service_status(self, service_status: Dict[str, Dict[str, Any]]):
        """Add service status information to the report.
        
        Args:
            service_status: Dictionary mapping service names to their status information
                            Format: {'service_name': {'status': 'Active'|'Canceled', 'canceled_on': 'YYYY-MM-DD'}}
        """
        self.report_data['service_status'] = service_status
    
    def add_service_relationships(self, service_relationships: Dict[str, str]):
        """Add service relationship mapping for status inheritance.
        
        Args:
            service_relationships: Dictionary mapping service names to their related services
                                  The related service's status will be used for the dependent service
        """
        self.report_data['service_relationships'] = service_relationships
    
    def add_service_resources(self, service_resources: Dict[str, Dict]):
        """Add service resources for direct cancellation links.
        
        Args:
            service_resources: Dictionary mapping service names to their resources
                               Format: {'service_name': {'resources': [{'name': 'resource_name', 'url': 'url'}]}}
        """
        self.report_data['service_resources'] = service_resources
    
    def add_usage_costs(self, usage_costs: List[Dict[str, Any]]):
        """Add usage cost data to the report.
        
        Args:
            usage_costs: List of usage cost data dictionaries
        """
        self.report_data['usage_costs'] = usage_costs
    
    def add_daily_costs(self, daily_costs: List[Tuple[str, float, str, str]]):
        """Add daily cost data to the report.
        
        Args:
            daily_costs: List of (date, cost, service, aws_console_link) tuples
        """
        self.report_data['daily_costs'] = daily_costs
    
    def add_anomalies(self, anomalies: List[Tuple[str, float, float]]):
        """Add cost anomaly data to the report.
        
        Args:
            anomalies: List of (date, cost, deviation) tuples
        """
        self.report_data['anomalies'] = anomalies
    
    def add_forecast(self, forecast_data: Dict[str, Any]):
        """Add forecast data to the report.
        
        Args:
            forecast_data: Dictionary containing forecast information
        """
        self.report_data['forecast'] = forecast_data
    
    def add_account_info(self, account_id: str):
        """Add AWS account information to the report.
        
        Args:
            account_id: The AWS account ID
        """
        self.report_data['account_id'] = account_id
    
    def add_alert_info(self, alerts: List[Tuple[str, float, str]], threshold: float):
        """Add alert information to the report.
        
        Args:
            alerts: List of (date, cost, service) tuples that exceeded the threshold
            threshold: The alert threshold value
        """
        self.report_data['alerts'] = alerts
        self.report_data['alert_threshold'] = threshold
    
    def add_today_cost(self, cost: float):
        """Add today's cost data to the report.
        
        Args:
            cost: The cost for today
        """
        self.report_data['today_cost'] = cost
    
    def add_last_month_cost(self, cost: float):
        """Add last month's cost data to the report.
        
        Args:
            cost: The cost for last month
        """
        self.report_data['last_month_cost'] = cost
        
    def add_custom_html(self, html_content: str):
        """Add custom HTML content to the report.
        
        Args:
            html_content: Raw HTML content to include in the report
        """
        if 'custom_html' not in self.report_data:
            self.report_data['custom_html'] = []
        
        self.report_data['custom_html'].append(html_content)
    
    def generate_charts(self):
        """Generate charts for the report using Plotly."""
        if not PLOTLY_AVAILABLE:
            return
        
        self.charts = []
        
        # Generate monthly costs chart
        if 'monthly_costs' in self.report_data and self.report_data['monthly_costs']:
            monthly_data = self.report_data['monthly_costs']
            dates = [item[0] for item in monthly_data]
            costs = [item[1] for item in monthly_data]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=dates,
                y=costs,
                marker_color='rgb(55, 83, 109)',
                name='Monthly Cost'
            ))
            fig.update_layout(
                title='Monthly AWS Costs',
                xaxis_title='Month',
                yaxis_title='Cost ($)',
                template='plotly_white'
            )
            
            self.charts.append({
                'id': 'monthly-costs-chart',
                'html': fig.to_html(full_html=False, include_plotlyjs='cdn')
            })
        
        # Generate service costs chart
        if 'service_costs' in self.report_data and self.report_data['service_costs']:
            service_data = self.report_data['service_costs']
            services = [item[0] for item in service_data]
            costs = [item[1] for item in service_data]
            
            # Limit to top 10 services for readability
            if len(services) > 10:
                services = services[:10]
                costs = costs[:10]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=services,
                y=costs,
                marker_color='rgb(26, 118, 255)',
                name='Service Cost'
            ))
            fig.update_layout(
                title='Top AWS Services by Cost',
                xaxis_title='Service',
                yaxis_title='Cost ($)',
                template='plotly_white'
            )
            
            self.charts.append({
                'id': 'service-costs-chart',
                'html': fig.to_html(full_html=False, include_plotlyjs='cdn')
            })
        
        # Generate daily costs chart with anomalies highlighted
        if 'daily_costs' in self.report_data and self.report_data['daily_costs']:
            daily_data = self.report_data['daily_costs']
            dates = [item[0] for item in daily_data]
            costs = [item[1] for item in daily_data]
            services = [item[2] if len(item) > 2 else "" for item in daily_data]
            
            fig = go.Figure()
            
            # Add daily costs line
            fig.add_trace(go.Scatter(
                x=dates,
                y=costs,
                mode='lines+markers',
                name='Daily Cost',
                line=dict(color='rgb(0, 128, 0)', width=2)
            ))
            
            # Add anomalies if available
            if 'anomalies' in self.report_data and self.report_data['anomalies']:
                anomaly_dates = [item[0] for item in self.report_data['anomalies']]
                anomaly_costs = [item[1] for item in self.report_data['anomalies']]
                
                fig.add_trace(go.Scatter(
                    x=anomaly_dates,
                    y=anomaly_costs,
                    mode='markers',
                    marker=dict(color='red', size=12, symbol='circle-open'),
                    name='Anomaly'
                ))
            
            # Add threshold line if available
            if 'alert_threshold' in self.report_data:
                threshold = self.report_data['alert_threshold']
                fig.add_shape(
                    type="line",
                    x0=dates[0],
                    y0=threshold,
                    x1=dates[-1],
                    y1=threshold,
                    line=dict(
                        color="Red",
                        width=2,
                        dash="dash",
                    )
                )
                fig.add_annotation(
                    x=dates[-1],
                    y=threshold,
                    text=f"Threshold: ${threshold:.2f}",
                    showarrow=False,
                    yshift=10
                )
            
            fig.update_layout(
                title='Daily AWS Costs',
                xaxis_title='Date',
                yaxis_title='Cost ($)',
                template='plotly_white'
            )
            
            self.charts.append({
                'id': 'daily-costs-chart',
                'html': fig.to_html(full_html=False, include_plotlyjs='cdn')
            })
        
        # Generate forecast chart if available
        if 'forecast' in self.report_data and self.report_data['forecast']:
            forecast = self.report_data['forecast']
            
            # Create a simple forecast chart
            if 'dates' in forecast and 'values' in forecast:
                fig = go.Figure()
                
                # Add historical data if available
                if 'historical_dates' in forecast and 'historical_values' in forecast:
                    fig.add_trace(go.Scatter(
                        x=forecast['historical_dates'],
                        y=forecast['historical_values'],
                        mode='lines+markers',
                        name='Historical Cost',
                        line=dict(color='blue', width=2)
                    ))
                
                # Add forecast line
                fig.add_trace(go.Scatter(
                    x=forecast['dates'],
                    y=forecast['values'],
                    mode='lines',
                    name='Forecast',
                    line=dict(color='orange', width=2, dash='dash')
                ))
                
                # Add confidence interval if available
                if 'lower_bound' in forecast and 'upper_bound' in forecast:
                    fig.add_trace(go.Scatter(
                        x=forecast['dates'] + forecast['dates'][::-1],
                        y=forecast['upper_bound'] + forecast['lower_bound'][::-1],
                        fill='toself',
                        fillcolor='rgba(255, 165, 0, 0.2)',
                        line=dict(color='rgba(255, 165, 0, 0)'),
                        name='Confidence Interval'
                    ))
                
                fig.update_layout(
                    title='AWS Cost Forecast',
                    xaxis_title='Date',
                    yaxis_title='Cost ($)',
                    template='plotly_white'
                )
                
                self.charts.append({
                    'id': 'forecast-chart',
                    'html': fig.to_html(full_html=False, include_plotlyjs='cdn')
                })
    
    def generate_html(self) -> str:
        """Generate the HTML report.
        
        Returns:
            str: The HTML report content
        """
        # Generate charts first
        self.generate_charts()
        
        # Load the HTML template
        template_str = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ title }}</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f5f5f5;
                    color: #333;
                }
                
                /* Accessibility improvements for 2025 web standards */
                button, .btn {
                    min-height: 44px; /* Minimum touch target size */
                    min-width: 100px; /* Ensure buttons are wide enough */
                    border-radius: 8px;
                    font-size: 14px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                
                /* Modern container with max-width */
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 0 1.5rem;
                }
                
                /* Premium header styling */
                header {
                    background: linear-gradient(120deg, #3b82f6, #8b5cf6);
                    color: white;
                    padding: 3rem 0;
                    margin-bottom: 3rem;
                    position: relative;
                    overflow: hidden;
                    border-radius: 0 0 0 0;
                    box-shadow: none;
                }
                
                /* Modern glass effect for header */
                header::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    right: 0;
                    bottom: 0;
                    left: 0;
                    backdrop-filter: blur(80px);
                    background: radial-gradient(circle at top right, rgba(255,255,255,0.1), transparent 70%);
                    z-index: 0;
                }
                
                header .container {
                    position: relative;
                    z-index: 1;
                }
                
                header h1 {
                    font-size: 2.5rem;
                    font-weight: 800;
                    margin-bottom: 0.5rem;
                    letter-spacing: -0.025em;
                }
                
                header .subtitle {
                    font-size: 1.25rem;
                    opacity: 0.9;
                    font-weight: 500;
                }
                
                header .generation-time {
                    font-size: 0.875rem;
                    opacity: 0.7;
                    margin-top: 0.5rem;
                }
                
                /* Modern card styling */
                .card {
                    background-color: white;
                    border-radius: 1rem;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
                    margin-bottom: 2.5rem;
                    overflow: hidden;
                    transition: all 0.3s ease;
                    border: 1px solid rgba(0, 0, 0, 0.04);
                }
                
                .card:hover {
                    box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.05);
                    transform: translateY(-3px);
                }
                
                .card-header {
                    padding: 1.25rem 1.5rem;
                    border-bottom: 1px solid #e5e7eb;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    background-color: #f9fafb;
                }
                
                .card-body {
                    padding: 1.5rem;
                }
                
                .section {
                    margin-bottom: 2rem;
                }
                
                .summary-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 2rem;
                    margin: 2rem 0;
                }
                
                .summary-item {
                    background-color: #f8fafc;
                    padding: 2rem;
                    border-radius: 0.75rem;
                    text-align: center;
                    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
                    transition: transform 0.3s ease, box-shadow 0.3s ease;
                    border: 1px solid rgba(0, 0, 0, 0.03);
                }
                
                .summary-item:hover {
                    transform: translateY(-5px);
                    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05), 0 10px 10px -5px rgba(0, 0, 0, 0.01);
                }
                
                .summary-item h3 {
                    font-size: 1rem;
                    color: #64748b;
                    margin-bottom: 1rem;
                    font-weight: 500;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }
                
                .summary-item .amount {
                    font-size: 2.5rem;
                    font-weight: 700;
                    color: #0f172a;
                    margin-bottom: 0.5rem;
                    line-height: 1.2;
                }
                
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 1.5rem 0;
                    font-size: 0.875rem;
                }
                
                th, td {
                    padding: 1rem;
                    text-align: left;
                    border-bottom: 1px solid #e2e8f0;
                }
                
                th {
                    background-color: #f8fafc;
                    font-weight: 600;
                    color: #64748b;
                    text-transform: uppercase;
                    font-size: 0.75rem;
                    letter-spacing: 0.05em;
                }
                
                tr:hover {
                    background-color: #f8fafc;
                }
                
                .aws-console-button {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    padding: 0.6rem 1.25rem;
                    border-radius: 0.5rem;
                    font-weight: 500;
                    font-size: 0.875rem;
                    background-color: #2563eb;
                    color: white;
                    text-decoration: none;
                    transition: all 0.3s ease;
                    border: none;
                    cursor: pointer;
                    letter-spacing: 0.01em;
                }
                
                .aws-console-button:hover {
                    background-color: #1d4ed8;
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
                }
                
                .cancel-button, .btn-cancel {
                    background-color: #dc3545;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 8px;
                    border: none;
                    cursor: pointer !important;
                    text-decoration: none;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 14px;
                    min-height: 44px;
                    min-width: 140px;
                    font-weight: 500;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    transition: all 0.2s ease;
                    user-select: none;
                }
                
                .cancel-button:hover, .btn-cancel:hover {
                    background-color: #c82333;
                    transform: translateY(-1px);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                }
                
                .cancel-button:active, .btn-cancel:active {
                    transform: translateY(1px);
                    box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                }
                
                .dropdown-btn:after {
                    content: " ▾";
                    display: inline-block;
                    margin-left: 5px;
                    font-size: 14px;
                }
                
                .action-buttons {
                    white-space: nowrap;
                    display: flex;
                    gap: 4px;
                }
                
                .help-text {
                    text-align: right;
                    margin-top: 5px;
                    margin-bottom: 15px;
                    font-size: 0.8em;
                    color: #666;
                    font-style: italic;
                }
                
                .service-note {
                    font-size: 0.85em;
                    margin-top: 5px;
                    color: #666;
                    font-style: italic;
                }
                
                .daily-costs-table-container table,
                .services-table-container table {
                    width: 100%;
                    border-collapse: collapse;
                }
                
                .daily-costs-table-container th, 
                .daily-costs-table-container td,
                .services-table-container th,
                .services-table-container td {
                    padding: 8px 12px;
                    text-align: left;
                    border-bottom: 1px solid #e1e4e8;
                }
                
                .daily-costs-table-container th,
                .services-table-container th {
                    background-color: #f6f8fa;
                    position: sticky;
                    top: 0;
                    z-index: 1;
                }
                
                /* Ensure all currency values show two decimal places */
                .cost-value {
                    min-width: 80px;
                    text-align: right;
                }
                
                .notice-box {
                    background-color: #f8f9fa;
                    border-left: 4px solid #007bff;
                    padding: 10px 15px;
                    margin-bottom: 20px;
                    font-size: 0.9em;
                    border-radius: 4px;
                }
                
                .notice-box ul {
                    margin: 5px 0 5px 20px;
                    padding: 0;
                }
                
                .dropdown {
                    position: relative;
                    display: inline-block;
                }
                
                .dropdown-content {
                    display: none;
                    position: absolute;
                    right: 0;
                    background-color: #ffffff;
                    min-width: 240px;
                    max-height: 400px;
                    overflow-y: auto;
                    box-shadow: 0px 8px 24px 0px rgba(0,0,0,0.15);
                    z-index: 99;
                    border-radius: 8px;
                    padding: 8px 0;
                    margin-top: 8px;
                }
                
                .dropdown-content a {
                    color: #333;
                    padding: 12px 16px;
                    text-decoration: none;
                    display: block;
                    border-radius: 4px;
                    margin: 4px 8px;
                    transition: all 0.2s ease;
                    border-bottom: 1px solid #f1f1f1;
                }
                
                .dropdown-content a:last-child {
                    border-bottom: none;
                }
                
                .dropdown-content a:hover {
                    background-color: #f1f1f1;
                    color: #0066cc;
                }
                
                .instructions {
                    font-size: 12px;
                    color: #666;
                    margin-top: 4px;
                    line-height: 1.4;
                }
                
                /* Cost threshold badge */
                .threshold-badge {
                    display: inline-block;
                    padding: 0.35rem 0.7rem;
                    font-size: 0.85rem;
                    border-radius: 1rem;
                    font-weight: 600;
                    color: white;
                    background-color: #28a745;
                    margin-left: 0.7rem;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                
                /* Make links work properly */
                a, button {
                    cursor: pointer !important;
                }
                
                /* Fix scrollbar styling */
                ::-webkit-scrollbar {
                    width: 10px;
                    height: 10px;
                }
                
                ::-webkit-scrollbar-track {
                    background: #f1f1f1;
                    border-radius: 5px;
                }
                
                ::-webkit-scrollbar-thumb {
                    background: #888;
                    border-radius: 5px;
                }
                
                ::-webkit-scrollbar-thumb:hover {
                    background: #555;
                }
                
                /* Collapsible section styles */
                .collapsible {
                    cursor: pointer;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    position: relative;
                    padding: 12px 10px;
                    transition: all 0.2s ease;
                    border-radius: 6px;
                    margin-bottom: 0;
                    font-weight: 600;
                    color: #2563eb;
                }
                
                .collapsible:hover {
                    background-color: #f1f5f9;
                }
                
                .collapsible:after {
                    content: '▼';
                    font-size: 14px;
                    color: #2563eb;
                    margin-left: 10px;
                    transition: transform 0.2s ease;
                }
                
                .collapsible.collapsed:after {
                    content: '▼';
                    transform: rotate(-90deg);
                }
                
                .collapsible-content {
                    max-height: 2000px;
                    overflow: hidden;
                    transition: all 0.5s ease-out;
                    opacity: 1;
                    transform-origin: top;
                    transform: scaleY(1);
                    margin-top: 15px;
                }
                
                .collapsible-content.collapsed {
                    max-height: 0;
                    opacity: 0;
                    transform: scaleY(0);
                    margin-top: 0;
                    pointer-events: none;
                }
                
                .daily-costs-table-container {
                    max-height: 400px;
                    overflow-y: auto;
                    margin-top: 15px;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    position: relative;
                }
                
                .daily-costs-table-container::after {
                    content: "Scroll for more ↓";
                    position: absolute;
                    bottom: 5px;
                    right: 10px;
                    background-color: rgba(255, 255, 255, 0.9);
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-size: 12px;
                    color: #6b7280;
                    pointer-events: none;
                    opacity: 0.8;
                }
                
                .services-table-container {
                    max-height: 500px;
                    overflow-y: auto;
                    margin-top: 15px;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    position: relative;
                }
                
                .services-table-container::after {
                    content: "Scroll for more ↓";
                    position: absolute;
                    bottom: 5px;
                    right: 10px;
                    background-color: rgba(255, 255, 255, 0.9);
                    padding: 5px 10px;
                    border-radius: 4px;
                    font-size: 12px;
                    color: #6b7280;
                    pointer-events: none;
                    opacity: 0.8;
                }
                
                .service-name {
                    display: flex;
                    align-items: center;
                }
                
                .cancel-all-button {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    padding: 0.8rem 1.5rem;
                    border-radius: 0.5rem;
                    font-weight: 600;
                    font-size: 1rem;
                    background-color: #dc2626;
                    color: white;
                    text-decoration: none;
                    transition: all 0.3s ease;
                    border: none;
                    cursor: pointer;
                    margin-top: 1rem;
                    letter-spacing: 0.01em;
                    box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
                }
                
                .cancel-all-button:hover {
                    background-color: #b91c1c;
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(239, 68, 68, 0.3);
                }
            </style>
        </head>
        <body>
            <header>
                <div class="container">
                    <h1>{{ title }}</h1>
                    <p class="subtitle">{{ first_day_last_month }} to {{ today_date }}</p>
                    <p class="generation-time">Generated on {{ generation_time }}</p>
                    <a href="javascript:void(0)" onclick="confirmCancelAll()" class="cancel-all-button">CANCEL EVERYTHING</a>
                </div>
            </header>
            
            <!-- Summary Section -->
            <div class="card container">
                <div class="card-header">
                    <h2>Summary</h2>
                </div>
                <div class="card-body">
                    
                    <div class="summary-grid">
                        {% if monthly_costs %}
                        <div class="summary-item">
                            <h3>Last Month</h3>
                            <p class="amount cost-value">${{ "%.2f"|format(last_month_cost|default('0')|float) }}</p>
                        </div>
                        
                        <div class="summary-item">
                            <h3>This Month (Month-to-Date)</h3>
                            {% set current_month_cost = monthly_costs[-1][1] %}
                            {% for period, cost in monthly_costs %}
                                {% if current_month in period %}
                                    {% set current_month_cost = cost %}
                                {% endif %}
                            {% endfor %}
                            <p class="amount cost-value">${{ "%.2f"|format(current_month_cost|default('0')|float) }}</p>
                        </div>
                        {% endif %}
                        
                        {% if forecast and forecast.total %}
                        <div class="summary-item">
                            <h3>Forecasted Cost (30 Days)</h3>
                            <p class="amount cost-value">${{ "%.2f"|format(forecast.total|default('0')|float) }}</p>
                        </div>
                        {% endif %}
                        
                        {% if alerts %}
                        <div class="summary-item">
                            <h3>Cost Alerts</h3>
                            <p>{{ alerts|length }} alerts</p>
                        </div>
                        {% endif %}
                    </div>
                </div>
            </div>
            
            <!-- Charts Section -->
            {% for chart in charts %}
            <div class="card container">
                <div class="card-header">
                    <h2>{{ chart.id.replace('-', ' ').title() }}</h2>
                </div>
                <div class="card-body">
                    <div class="chart-container" id="{{ chart.id }}">
                        {{ chart.html|safe }}
                    </div>
                </div>
            </div>
            {% endfor %}
            
            <!-- Daily Costs Section -->
            {% if daily_costs %}
            <div class="card container">
                <div class="card-header">
                    <h2 class="collapsible collapsed" onclick="toggleCollapsible(this)">Daily Costs</h2>
                </div>
                <div class="card-body collapsible-content collapsed" id="daily-costs-section">
                    <div class="daily-costs-table-container">
                        <table border="0" cellspacing="0" cellpadding="0">
                            <thead>
                                <tr>
                                    <th>Date</th>
                                    <th>Cost</th>
                                    <th>Service</th>
                                    <th>Actions</th>
                                    {% if anomalies %}
                                    <th>Status</th>
                                    {% endif %}
                                </tr>
                            </thead>
                            <tbody>
                                {% for item in daily_costs|sort(attribute='0', reverse=True) %}
                                <tr>
                                    <td>{{ item[0] }}</td>
                                    <td class="cost-value">${{ "%.2f"|format(item[1]|float) }}</td>
                                    <td class="{% if item[2] %}service-name{% endif %}">{{ item[2] }}</td>
                                    <td>
                                        <div class="action-buttons">
                                            {% if item[2] %}
                                                <a href="{{ item[3] }}" target="_blank" class="aws-console-button">View Bill</a>
                                                
                                                {% if not item[0].startswith('Tax') and not item[0].startswith('Credit/Refund') %}
                                                    {% set service_name = item[0].split(" (")[0] %}
                                                    
                                                    {% if service_resources and service_name in service_resources %}
                                                        {% set resources = service_resources[service_name] %}
                                                        
                                                        {% if resources.resources|length == 1 %}
                                                            <a href="{{ resources.resources[0].url }}" target="_blank" class="cancel-button">Cancel Service</a>
                                                        {% elif resources.resources|length > 1 %}
                                                            <div class="dropdown">
                                                                <button class="cancel-button dropdown-btn" onclick="toggleDropdown(this)">Cancel Service</button>
                                                                <div class="dropdown-content">
                                                                    {% for resource in resources.resources %}
                                                                        <a href="{{ resource.url }}" target="_blank">
                                                                            {% if resource.display_name is defined %}
                                                                                {{ resource.display_name }}
                                                                            {% else %}
                                                                                {{ resource.name }}
                                                                            {% endif %}
                                                                            {% if resource.instructions is defined %}
                                                                                <span class="resource-instruction">{{ resource.instructions }}</span>
                                                                            {% endif %}
                                                                        </a>
                                                                    {% endfor %}
                                                                </div>
                                                            </div>
                                                        {% else %}
                                                            <a href="{{ resources.default_url }}" target="_blank" class="cancel-button">Cancel Service</a>
                                                        {% endif %}
                                                    {% elif service_name == "AWS Skill Builder Individual" %}
                                                        <a href="https://console.aws.amazon.com/skillbuilder/home?#/subscriptions" target="_blank" class="cancel-button">Cancel Service</a>
                                                    {% elif service_name == "AWS Cost Explorer" %}
                                                        <a href="https://console.aws.amazon.com/cost-management/home?#/cost-explorer/settings" target="_blank" class="cancel-button">Cancel Service</a>
                                                    {% elif service_name == "Amazon OpenSearch Service" %}
                                                        <a href="https://console.aws.amazon.com/opensearch/home?#opensearch/domains" target="_blank" class="cancel-button">Cancel Service</a>
                                                    {% elif service_name == "Amazon Bedrock" %}
                                                        <a href="https://console.aws.amazon.com/bedrock/home?#/modelaccess" target="_blank" class="cancel-button">Cancel Service</a>
                                                    {% elif service_name == "Claude 3.7 Sonnet" %}
                                                        <a href="https://console.aws.amazon.com/bedrock/home?#/modelaccess" target="_blank" class="cancel-button">Cancel Service</a>
                                                    {% else %}
                                                        <a href="https://console.aws.amazon.com/billing/home?#/preferences" target="_blank" class="cancel-button">Cancel Service</a>
                                                    {% endif %}
                                                {% endif %}
                                            {% endif %}
                                        </div>
                                    </td>
                                    {% if anomalies %}
                                    <td>
                                        {% set is_anomaly = false %}
                                        {% for anomaly in anomalies %}
                                            {% if anomaly[0] == item[0] %}
                                                {% set is_anomaly = true %}
                                            {% endif %}
                                        {% endfor %}
                                        
                                        {% if is_anomaly %}
                                        <span class="badge badge-warning">Anomaly</span>
                                        {% endif %}
                                        
                                        {% if alerts %}
                                            {% for alert in alerts %}
                                                {% if alert[0] == item[0] %}
                                                    <span class="badge badge-danger">Alert</span>
                                                {% endif %}
                                            {% endfor %}
                                        {% endif %}
                                    </td>
                                    {% endif %}
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            {% endif %}
            
            <!-- Service Costs Section -->
            {% if service_costs %}
            <div class="card container">
                <div class="card-header">
                    <h2 class="collapsible" onclick="toggleCollapsible(this)">Top Services by Cost ({{ first_day_last_month }} to {{ today_date }})</h2>
                </div>
                <div class="card-body collapsible-content" id="top-services-section">
                    <div class="services-table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Service</th>
                                    <th>Details</th>
                                    <th>Cost</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for item in service_costs %}
                                <tr>
                                    <td>{{ item[0] }}</td>
                                    <td>
                                        {% if item[0] == 'Amazon Bedrock' %}
                                            Model inference, tokens, API usage
                                        {% elif 'OpenSearch' in item[0] %}
                                            Search OCUs, Indexing OCUs, Storage
                                        {% elif 'Cost Explorer' in item[0] %}
                                            API usage charges
                                        {% elif 'Skill Builder' in item[0] %}
                                            Subscription
                                        {% else %}
                                            Usage charges
                                        {% endif %}
                                    </td>
                                    <td class="cost-value">${{ "%.2f"|format(item[1]|float) }}</td>
                                    <td>
                                        {% if service_relationships and item[0] in service_relationships %}
                                            {% set related_service = service_relationships[item[0]] %}
                                            {% if related_service in service_status and service_status[related_service].status == 'Canceled' %}
                                                {% if item[0].startswith('Credit/Refund') %}
                                                    <span class="badge badge-success">Received on {{ service_status[related_service].canceled_on }}</span>
                                                {% else %}
                                                    <span class="badge badge-success">Canceled on {{ service_status[related_service].canceled_on }}</span>
                                                {% endif %}
                                            {% elif service_status[related_service].status == 'Active' and service_status[related_service].notes %}
                                                <span class="badge badge-warning">Active</span>
                                                <div class="service-note">{{ service_status[related_service].notes }}</div>
                                            {% else %}
                                                <span class="badge badge-warning">Active</span>
                                            {% endif %}
                                        {% elif item[0] in service_status %}
                                            {% if service_status[item[0]].status == 'Canceled' %}
                                                <span class="badge badge-success">Canceled on {{ service_status[item[0]].canceled_on }}</span>
                                            {% elif service_status[item[0]].notes %}
                                                <span class="badge badge-warning">Active</span>
                                                <div class="service-note">{{ service_status[item[0]].notes }}</div>
                                            {% else %}
                                                <span class="badge badge-warning">Active</span>
                                            {% endif %}
                                        {% else %}
                                            <span class="badge badge-warning">Active</span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        <div class="action-buttons">
                                            {% if item[2] %}
                                                <a href="{{ item[2] }}" target="_blank" class="aws-console-button">View Bill</a>
                                                
                                                {% if not item[0].startswith('Tax') and not item[0].startswith('Credit/Refund') %}
                                                    {% set service_name = item[0].split(" (")[0] %}
                                                    
                                                    {% if service_resources and service_name in service_resources %}
                                                        {% set resources = service_resources[service_name] %}
                                                        
                                                        {% if resources.resources|length == 1 %}
                                                            <a href="{{ resources.resources[0].url }}" target="_blank" class="cancel-button">Cancel Service</a>
                                                        {% elif resources.resources|length > 1 %}
                                                            <div class="dropdown">
                                                                <button class="cancel-button dropdown-btn" onclick="toggleDropdown(this)">Cancel Service</button>
                                                                <div class="dropdown-content">
                                                                    {% for resource in resources.resources %}
                                                                        <a href="{{ resource.url }}" target="_blank">
                                                                            {% if resource.display_name is defined %}
                                                                                {{ resource.display_name }}
                                                                            {% else %}
                                                                                {{ resource.name }}
                                                                            {% endif %}
                                                                            {% if resource.instructions is defined %}
                                                                                <span class="resource-instruction">{{ resource.instructions }}</span>
                                                                            {% endif %}
                                                                        </a>
                                                                    {% endfor %}
                                                                </div>
                                                            </div>
                                                        {% else %}
                                                            <a href="{{ resources.default_url }}" target="_blank" class="cancel-button">Cancel Service</a>
                                                        {% endif %}
                                                    {% elif service_name == "AWS Skill Builder Individual" %}
                                                        <a href="https://console.aws.amazon.com/skillbuilder/home?#/subscriptions" target="_blank" class="cancel-button">Cancel Service</a>
                                                    {% elif service_name == "AWS Cost Explorer" %}
                                                        <a href="https://console.aws.amazon.com/cost-management/home?#/cost-explorer/settings" target="_blank" class="cancel-button">Cancel Service</a>
                                                    {% elif service_name == "Amazon OpenSearch Service" %}
                                                        <a href="https://console.aws.amazon.com/opensearch/home?#opensearch/domains" target="_blank" class="cancel-button">Cancel Service</a>
                                                    {% elif service_name == "Amazon Bedrock" %}
                                                        <a href="https://console.aws.amazon.com/bedrock/home?#/modelaccess" target="_blank" class="cancel-button">Cancel Service</a>
                                                    {% elif service_name == "Claude 3.7 Sonnet" %}
                                                        <a href="https://console.aws.amazon.com/bedrock/home?#/modelaccess" target="_blank" class="cancel-button">Cancel Service</a>
                                                    {% else %}
                                                        <a href="https://console.aws.amazon.com/billing/home?#/preferences" target="_blank" class="cancel-button">Cancel Service</a>
                                                    {% endif %}
                                                {% endif %}
                                            {% endif %}
                                        </div>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            {% endif %}
            
            <!-- Usage Costs Section -->
            {% if usage_costs %}
            <div class="card container">
                <div class="card-header">
                    <h2>Costs by Usage Type</h2>
                </div>
                <div class="card-body">
                    <table>
                        <thead>
                            <tr>
                                <th>Usage Type</th>
                                <th>Cost</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for usage, cost in usage_costs %}
                            <tr>
                                <td>{{ usage }}</td>
                                <td class="cost-value">${{ "%.2f"|format(cost|float) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            {% endif %}
            
            <!-- Anomalies Section -->
            {% if anomalies %}
            <div class="card container">
                <div class="card-header">
                    <h2>Cost Anomalies</h2>
                </div>
                <div class="card-body">
                    {% if anomalies|length > 0 %}
                    <div class="alert">
                        <p><strong>{{ anomalies|length }} anomalies detected</strong></p>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Cost</th>
                                <th>Deviation</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for anomaly in anomalies %}
                            <tr>
                                <td>{{ anomaly[0] }}</td>
                                <td class="cost-value">${{ "%.2f"|format(anomaly[1]|float) }}</td>
                                <td class="cost-value">${{ "+" if anomaly[2] > 0 else "" }}{{ "%.2f"|format(anomaly[2]|float) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    {% else %}
                    <div class="success">
                        <p>No cost anomalies detected.</p>
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endif %}
            
            <!-- Alerts Section -->
            {% if alerts %}
            <div class="card container">
                <div class="card-header">
                    <h2>Cost Alerts</h2>
                </div>
                <div class="card-body">
                    {% if alerts|length > 0 %}
                    <div class="alert">
                        <p><strong>{{ alerts|length }} days exceeded your cost threshold of ${{ "%.2f"|format(alert_threshold|float) }}</strong></p>
                    </div>
                    <table>
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Cost</th>
                                <th>Service</th>
                                <th>Excess</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for alert in alerts %}
                            <tr>
                                <td>{{ alert[0] }}</td>
                                <td class="cost-value">${{ "%.2f"|format(alert[1]|float) }}</td>
                                <td>{% if alert|length > 2 %}{{ alert[2] }}{% else %}Unknown{% endif %}</td>
                                <td class="cost-value">${{ "%.2f"|format((alert[1] - alert_threshold)|float) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    {% else %}
                    <div class="success">
                        <p>No days exceeded your cost threshold of ${{ "%.2f"|format(alert_threshold|float) }}.</p>
                    </div>
                    {% endif %}
                </div>
            </div>
            {% endif %}
            
            <!-- Forecast Section -->
            {% if forecast %}
            <div class="card container">
                <div class="card-header">
                    <h2>Cost Forecast</h2>
                </div>
                <div class="card-body">
                    <div class="info">
                        <p>Forecast for the next 30 days: <strong class="cost-value">${{ "%.2f"|format(forecast.total|float) }}</strong></p>
                        {% if forecast.lower_bound and forecast.upper_bound %}
                        <p>Prediction interval: <strong class="cost-value">${{ "%.2f"|format(forecast.lower_bound|float) }}</strong> to <strong class="cost-value">${{ "%.2f"|format(forecast.upper_bound|float) }}</strong></p>
                        {% endif %}
                    </div>
                </div>
            </div>
            {% endif %}
            
            <!-- Cost Threshold Analysis -->
            {% if service_costs %}
            <div class="card container">
                <div class="card-header">
                    <h2>Cost Threshold Analysis</h2>
                </div>
                <div class="card-body">
                    <table>
                        <thead>
                            <tr>
                                <th>Service</th>
                                <th>Cost</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for item in service_costs %}
                            {% if alert_threshold and item[1] > alert_threshold %}
                            <tr>
                                <td>{{ item[0] }}</td>
                                <td class="cost-value">${{ "%.2f"|format(item[1]|float) }}</td>
                                <td>
                                    {% if item[1] > alert_threshold %}
                                        <span class="badge badge-danger">Exceeds Threshold</span>
                                    {% endif %}
                                    {% if service_status and item[0] in service_status %}
                                        {% if service_status[item[0]].status == 'Canceled' %}
                                            <span class="badge badge-success">Canceled on {{ service_status[item[0]].canceled_on }}</span>
                                        {% else %}
                                            <span class="badge badge-warning">Active</span>
                                        {% endif %}
                                    {% else %}
                                        <span class="badge badge-warning">Active</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endif %}
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            {% endif %}
            
            <div class="footer container">
                <p>AWS Cost Monitor Report &copy; {{ current_year }}</p>
                <p>Generated by <a href="https://github.com/yourusername/aws-cost-monitor" target="_blank">AWS Cost Monitor</a></p>
            </div>
        </body>
        <script>
            function toggleCollapsible(element) {
                // If this is inside card-header, we need to get the next sibling of parent
                var header = element.closest('.card-header');
                if (header) {
                    element.classList.toggle('collapsed');
                    var content = header.nextElementSibling;
                    content.classList.toggle('collapsed');
                } else {
                    element.classList.toggle('collapsed');
                    var content = element.nextElementSibling;
                    content.classList.toggle('collapsed');
                }
                
                // Check if the section is now expanded and has an ID
                if (!content.classList.contains('collapsed')) {
                    if (content.id === 'daily-costs-section') {
                        // Ensure daily costs are visible
                        console.log('Daily costs section expanded');
                    }
                    if (content.id === 'top-services-section') {
                        // Ensure top services are visible
                        console.log('Top services section expanded');
                    }
                }
            }
            
            function toggleDropdown(button) {
                // Get dropdown content
                const content = button.nextElementSibling;
                
                // First close all other open dropdowns
                document.querySelectorAll('.dropdown-content').forEach(el => {
                    if (el !== content) el.style.display = 'none';
                });
                
                // Toggle this dropdown
                content.style.display = content.style.display === 'block' ? 'none' : 'block';
                
                // If opening the dropdown
                if (content.style.display === 'block') {
                    // Ensure it's visible within viewport
                    const rect = content.getBoundingClientRect();
                    if (rect.bottom > window.innerHeight) {
                        content.style.maxHeight = (window.innerHeight - rect.top - 20) + 'px';
                    }
                    
                    // Handle click outside to close
                    function closeDropdown(e) {
                        if (!button.parentElement.contains(e.target)) {
                            content.style.display = 'none';
                            document.removeEventListener('click', closeDropdown);
                            document.removeEventListener('keydown', handleEscape);
                        }
                    }
                    
                    // Close on Escape key
                    function handleEscape(e) {
                        if (e.key === 'Escape') {
                            content.style.display = 'none';
                            document.removeEventListener('click', closeDropdown);
                            document.removeEventListener('keydown', handleEscape);
                        }
                    }
                    
                    // Add event listeners after a small delay to prevent immediate closing
                    setTimeout(() => {
                        document.addEventListener('click', closeDropdown);
                        document.addEventListener('keydown', handleEscape);
                    }, 10);
                }
                
                // Prevent event from bubbling up
                if (event) event.stopPropagation();
                return false;
            }
            
            function confirmCancelAll() {
                if (confirm("WARNING: This will attempt to cancel ALL AWS services in your account. This action cannot be undone. Are you sure you want to proceed?")) {
                    // Create URL with cancel_all parameter
                    const reportUrl = window.location.href + "?cancel_all=true";
                    
                    // Create hidden form that will trigger the report handler script
                    const form = document.createElement('form');
                    form.method = 'GET';
                    form.action = 'file://' + reportUrl.split('file://')[1].split('?')[0].replace('reports', 'scripts').replace('.html', '_handler.py');
                    
                    // Add input with the URL as value
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = 'url';
                    input.value = reportUrl;
                    form.appendChild(input);
                    
                    // Add form to body and submit
                    document.body.appendChild(form);
                    
                    // Launch the script
                    fetch(form.action + '?' + new URLSearchParams({url: reportUrl}))
                        .then(response => {
                            console.log('Cancel all services initiated');
                            alert('Cancellation of all AWS services has been initiated. Check the terminal for progress.');
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            
                            // Fallback: use the python command directly
                            const script = form.action.split('file://')[1];
                            const command = `python "${script}" "${reportUrl}"`;
                            
                            // Create a notification with command to copy
                            alert('Please run this command in your terminal to cancel all services:\n\n' + command);
                        });
                }
            }
        </script>
        </html>
        """
        
        # Create the template
        template = Template(template_str)
        
        # Get today's date and the first day of last month
        today = datetime.datetime.now()
        last_month = today.month - 1 if today.month > 1 else 12
        last_month_year = today.year if today.month > 1 else today.year - 1
        first_day_last_month = datetime.datetime(last_month_year, last_month, 1).strftime("%Y-%m-%d")
        today_date = today.strftime("%Y-%m-%d")
        generation_time = today.strftime("%b %d, %Y at %I:%M %p")  # More readable format (Apr 10, 2025 at 4:52 PM)
        
        # Render the template with data
        html = template.render(
            title=self.title,
            generation_time=generation_time,
            today_date=today_date,
            first_day_last_month=first_day_last_month,
            current_year=datetime.datetime.now().year,
            current_month=datetime.datetime.now().strftime("%B"),
            last_month=(datetime.datetime.now().replace(day=1) - datetime.timedelta(days=1)).strftime("%B"),
            charts=self.charts,
            monthly_costs=self.report_data.get('monthly_costs', []),
            service_costs=self.report_data.get('service_costs', []),
            service_status=self.report_data.get('service_status', {}),
            service_relationships=self.report_data.get('service_relationships', {}),
            usage_costs=self.report_data.get('usage_costs', []),
            daily_costs=self.report_data.get('daily_costs', []),
            today_cost=self.report_data.get('today_cost', 0.0),
            last_month_cost=self.report_data.get('last_month_cost', 36.64),
            anomalies=self.report_data.get('anomalies', []),
            alerts=self.report_data.get('alerts', []),
            alert_threshold=self.report_data.get('alert_threshold', 0),
            forecast=self.report_data.get('forecast', {}),
            account_id=self.report_data.get('account_id', ''),
            custom_html=self.report_data.get('custom_html', []),
            service_resources=self.report_data.get('service_resources', {})
        )
        
        return html
    
    def save_html(self, output_path: str) -> str:
        """Save the HTML report to a file.
        
        Args:
            output_path: The path to save the HTML report to
            
        Returns:
            str: The path to the saved HTML report
        """
        html_content = self.generate_html()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        print(f"HTML report generated successfully at: {output_path}")
        return output_path


# Example usage
if __name__ == "__main__":
    # Create a sample report for testing
    generator = HTMLReportGenerator("Sample AWS Cost Report")
    
    # Add sample data
    generator.add_monthly_costs([
        ("2023-01", 120.45),
        ("2023-02", 145.67),
        ("2023-03", 132.89)
    ])
    
    generator.add_service_costs([
        ("EC2", 75.45, "https://console.aws.amazon.com/ec2/"),
        ("S3", 25.67, "https://console.aws.amazon.com/s3/"),
        ("RDS", 15.89, "https://console.aws.amazon.com/rds/"),
        ("Lambda", 5.45, "https://console.aws.amazon.com/lambda/"),
        ("CloudFront", 3.67, "https://console.aws.amazon.com/cloudfront/")
    ])
    
    generator.add_service_status({
        "EC2": {"status": "Active", "canceled_on": None, "aws_console_link": "https://console.aws.amazon.com/ec2/"},
        "S3": {"status": "Active", "canceled_on": None, "aws_console_link": "https://console.aws.amazon.com/s3/"},
        "RDS": {"status": "Canceled", "canceled_on": "2023-02-15", "aws_console_link": "https://console.aws.amazon.com/rds/"},
        "Lambda": {"status": "Active", "canceled_on": None, "aws_console_link": "https://console.aws.amazon.com/lambda/"},
        "CloudFront": {"status": "Active", "canceled_on": None, "aws_console_link": "https://console.aws.amazon.com/cloudfront/"}
    })
    
    generator.add_service_relationships({
        "EC2": "RDS",
        "S3": "CloudFront"
    })
    
    generator.add_service_resources({
        "EC2": {"resources": [{"name": "EC2 Instance", "url": "https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#Instances:sort=instanceId"}]},
        "S3": {"resources": [{"name": "S3 Bucket", "url": "https://console.aws.amazon.com/s3/buckets/"}]}
    })
    
    generator.add_daily_costs([
        ("2023-03-01", 4.56, "EC2", "https://console.aws.amazon.com/ec2/"),
        ("2023-03-02", 4.78, "S3", "https://console.aws.amazon.com/s3/"),
        ("2023-03-03", 4.32, "RDS", "https://console.aws.amazon.com/rds/"),
        ("2023-03-04", 8.91, "Lambda", "https://console.aws.amazon.com/lambda/"),  # Anomaly
        ("2023-03-05", 4.45, "CloudFront", "https://console.aws.amazon.com/cloudfront/")
    ])
    
    generator.add_anomalies([
        ("2023-03-04", 8.91, 4.35)
    ])
    
    generator.add_alert_info([
        ("2023-03-04", 8.91, "Lambda")
    ], 5.0)
    
    generator.add_forecast({
        "total": 145.67,
        "lower_bound": 130.45,
        "upper_bound": 160.89,
        "dates": ["2023-04-01", "2023-04-15", "2023-04-30"],
        "values": [4.50, 4.75, 5.00],
        "historical_dates": ["2023-03-01", "2023-03-15", "2023-03-30"],
        "historical_values": [4.25, 4.50, 4.75]
    })
    
    generator.add_account_info("123456789012")
    
    generator.add_today_cost(10.0)
    
    generator.add_last_month_cost(36.64)
    
    generator.add_custom_html("<p>This is a custom HTML note.</p>")
    
    # Save the report
    output_path = "sample_report.html"
    generator.save_html(output_path)
    print(f"Sample report saved to {output_path}")

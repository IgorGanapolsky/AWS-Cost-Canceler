#!/usr/bin/env python3
"""
AWS Cost Monitor - Cost Explorer API
This script uses the AWS Cost Explorer API to provide detailed information
about your current AWS charges and forecast future spending.

Features:
- Detailed cost breakdowns by service and usage type
- Daily and monthly cost analysis
- Cost forecasting
- Cost anomaly detection
- Cost threshold alerts
- Email notifications of cost reports
"""

import os
import sys
import boto3
import fire
import json
import smtplib
import statistics
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from tabulate import tabulate

# Load environment variables from .env file
dotenv_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path)

# Constants for alerts and notifications
DEFAULT_ALERT_THRESHOLD = 1.0  # Alert threshold in dollars
DEFAULT_NOTIFY_EMAIL = "easy.smart.llc@gmail.com"  # Default notification email


class AWSCostMonitor:
    """Monitor AWS costs using the Cost Explorer API."""
    
    def __init__(self, alert_threshold=None, notify_email=None):
        """Initialize with AWS credentials.
        
        Args:
            alert_threshold: Dollar amount for cost alerts (default: 1.0)
            notify_email: Email address for notifications (default from .env or DEFAULT_NOTIFY_EMAIL)
        """
        # Load AWS credentials from environment variables
        self.aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            print("ERROR: AWS API credentials not found. Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file.")
            print("Note: These are different from your AWS console login credentials.")
            print("You can create API keys in the AWS IAM console: https://console.aws.amazon.com/iam/home#/security_credentials")
            sys.exit(1)
        
        # Create boto3 session with API credentials
        self.session = boto3.Session(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key
        )
        
        # Initialize Cost Explorer client
        self.ce = self.session.client('ce', region_name='us-east-1')
        
        # Set alert threshold
        self.alert_threshold = alert_threshold or DEFAULT_ALERT_THRESHOLD
        
        # Set notification email
        self.notify_email = notify_email or os.environ.get("NOTIFY_EMAIL", DEFAULT_NOTIFY_EMAIL)
        
        # Store for report output
        self.report_content = []
    
    def log(self, message):
        """Log a message to both console and the report content."""
        print(message)
        self.report_content.append(message)
    
    def get_month_date_range(self, months_back=1):
        """Get date range for the specified number of months back."""
        today = datetime.now()
        
        # End date is today
        end_date = today.strftime("%Y-%m-%d")
        
        # Start date is first day of the month, X months ago
        if months_back == 0:  # Current month
            start_date = today.replace(day=1).strftime("%Y-%m-%d")
        else:
            # Calculate first day of previous month(s)
            first_day = today.replace(day=1)
            for _ in range(months_back):
                # Move to the last day of the previous month
                last_day_prev_month = first_day - timedelta(days=1)
                # Then to the first day of that month
                first_day = last_day_prev_month.replace(day=1)
            start_date = first_day.strftime("%Y-%m-%d")
        
        return start_date, end_date
    
    def get_cost_and_usage(self, months_back=1, granularity='MONTHLY', metrics=None, group_by=None):
        """Get cost and usage data from AWS Cost Explorer."""
        if metrics is None:
            metrics = ["BlendedCost", "UnblendedCost", "UsageQuantity"]
        
        start_date, end_date = self.get_month_date_range(months_back)
        
        params = {
            'TimePeriod': {
                'Start': start_date,
                'End': end_date
            },
            'Granularity': granularity,
            'Metrics': metrics
        }
        
        if group_by:
            params['GroupBy'] = group_by
        
        response = self.ce.get_cost_and_usage(**params)
        return response
    
    def get_cost_forecast(self, days_forward=30):
        """Get cost forecast for the specified number of days forward."""
        today = datetime.now()
        
        # Start date is today
        start_date = today.strftime("%Y-%m-%d")
        
        # End date is X days in the future
        end_date = (today + timedelta(days=days_forward)).strftime("%Y-%m-%d")
        
        # Try to get the forecast, but don't raise an exception if it fails
        try:
            response = self.ce.get_cost_forecast(
                TimePeriod={
                    'Start': start_date,
                    'End': end_date
                },
                Granularity='MONTHLY',
                Metric='BLENDED_COST'
            )
            return response
        except Exception as e:
            # Just return None if there's an error
            return None
    
    def get_service_costs(self, months_back=1):
        """Get costs grouped by service."""
        return self.get_cost_and_usage(
            months_back=months_back,
            group_by=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        )
    
    def get_usage_type_costs(self, months_back=1):
        """Get costs grouped by usage type."""
        return self.get_cost_and_usage(
            months_back=months_back,
            group_by=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'USAGE_TYPE'
                }
            ]
        )
    
    def get_daily_costs(self, days_back=30):
        """Get daily costs for the past X days with service breakdown."""
        today = datetime.now()
        
        # End date is today
        end_date = today.strftime("%Y-%m-%d")
        
        # Start date is X days ago
        start_date = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        # Get overall costs by day
        response = self.ce.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=["BlendedCost"]
        )
        
        # Also get service-level breakdown for each day
        service_response = self.ce.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=["BlendedCost"],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        )
        
        # Create a mapping of date -> top service
        date_to_top_service = {}
        for period in service_response['ResultsByTime']:
            date = period['TimePeriod']['Start']
            
            # Skip if no services in this period
            if not period.get('Groups'):
                continue
                
            # Get the service with highest cost
            services = sorted(
                period['Groups'], 
                key=lambda x: float(x['Metrics']['BlendedCost']['Amount']),
                reverse=True
            )
            
            if services and float(services[0]['Metrics']['BlendedCost']['Amount']) > 0:
                service_name = services[0]['Keys'][0]
                date_to_top_service[date] = service_name
        
        # Add the service information to the main response
        response['ServiceBreakdown'] = date_to_top_service
        
        return response
    
    def display_monthly_costs(self, months=3):
        """Display monthly costs for the last X months."""
        self.log(f"\n=== Monthly AWS Costs (Last {months} Months) ===")
        
        response = self.get_cost_and_usage(months_back=months)
        
        # Prepare table data
        table_data = []
        headers = ["Period", "Blended Cost", "Unblended Cost", "Usage Quantity"]
        
        for result in response['ResultsByTime']:
            period_start = result['TimePeriod']['Start']
            period_end = result['TimePeriod']['End']
            period = f"{period_start} to {period_end}"
            
            blended_cost = f"${float(result['Total']['BlendedCost']['Amount']):.2f}"
            unblended_cost = f"${float(result['Total']['UnblendedCost']['Amount']):.2f}"
            usage = f"{float(result['Total']['UsageQuantity']['Amount']):.2f}"
            
            table_data.append([period, blended_cost, unblended_cost, usage])
        
        # Display the table
        self.log(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def display_service_costs(self, months=1):
        """Display costs by service for the last X months."""
        self.log(f"\n=== AWS Costs by Service (Last {months} Months) ===")
        
        response = self.get_service_costs(months_back=months)
        
        # Prepare table data
        table_data = []
        headers = ["Service", "Blended Cost", "Usage Quantity"]
        
        for result in response['ResultsByTime']:
            # Skip periods with no data
            if not result.get('Groups'):
                continue
                
            # Sort groups by cost in descending order
            sorted_groups = sorted(
                result['Groups'], 
                key=lambda x: float(x['Metrics']['BlendedCost']['Amount']),
                reverse=True
            )
            
            for group in sorted_groups:
                service = group['Keys'][0]
                blended_cost = f"${float(group['Metrics']['BlendedCost']['Amount']):.2f}"
                usage = f"{float(group['Metrics']['UsageQuantity']['Amount']):.2f}"
                
                # Only add services with non-zero costs
                if float(group['Metrics']['BlendedCost']['Amount']) > 0:
                    table_data.append([service, blended_cost, usage])
        
        if table_data:
            # Display the table
            self.log(tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            self.log("No service cost data available for the specified period.")
    
    def display_usage_type_costs(self, months=1):
        """Display costs by usage type for the last X months."""
        self.log(f"\n=== AWS Costs by Usage Type (Last {months} Months) ===")
        
        response = self.get_usage_type_costs(months_back=months)
        
        # Prepare table data
        table_data = []
        headers = ["Usage Type", "Blended Cost", "Usage Quantity"]
        
        for result in response['ResultsByTime']:
            # Skip periods with no data
            if not result.get('Groups'):
                continue
                
            # Sort groups by cost in descending order
            sorted_groups = sorted(
                result['Groups'], 
                key=lambda x: float(x['Metrics']['BlendedCost']['Amount']),
                reverse=True
            )
            
            for group in sorted_groups:
                usage_type = group['Keys'][0]
                blended_cost = f"${float(group['Metrics']['BlendedCost']['Amount']):.2f}"
                usage = f"{float(group['Metrics']['UsageQuantity']['Amount']):.2f}"
                
                # Only add usage types with non-zero costs
                if float(group['Metrics']['BlendedCost']['Amount']) > 0:
                    table_data.append([usage_type, blended_cost, usage])
        
        if table_data:
            # Display the table
            self.log(tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            self.log("No usage type cost data available for the specified period.")
    
    def display_daily_costs(self, days=14):
        """Display daily costs for the last X days."""
        self.log(f"\n=== Daily AWS Costs (Last {days} Days) ===")
        
        response = self.get_daily_costs(days_back=days)
        
        # Prepare table data
        table_data = []
        headers = ["Date", "Blended Cost", "Top Service"]
        
        # Extract cost data for analysis
        daily_costs = []
        
        for result in response['ResultsByTime']:
            date = result['TimePeriod']['Start']
            cost = float(result['Total']['BlendedCost']['Amount'])
            blended_cost = f"${cost:.2f}"
            
            # Get the top service for this day
            top_service = response['ServiceBreakdown'].get(date, "Unknown")
            
            table_data.append([date, blended_cost, top_service])
            daily_costs.append((date, cost))
        
        # Display the table
        self.log(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # Return the daily costs for anomaly detection
        return daily_costs
    
    def detect_cost_anomalies(self, daily_costs):
        """Detect anomalies in daily costs.
        
        Uses statistical methods to identify unusual spikes or drops in costs.
        """
        self.log("\n=== Cost Anomaly Detection ===")
        
        # Need at least 3 days of data for meaningful analysis
        if len(daily_costs) < 3:
            self.log("Insufficient data for anomaly detection. Need at least 3 days of cost data.")
            return
        
        # Extract just the cost values
        cost_values = [cost for _, cost in daily_costs]
        
        # Calculate basic statistics
        mean_cost = statistics.mean(cost_values)
        
        # If we have enough data points, use standard deviation
        if len(cost_values) >= 5:
            try:
                stdev_cost = statistics.stdev(cost_values)
                threshold = max(2 * stdev_cost, 0.5)  # At least $0.50 or 2 standard deviations
                
                self.log(f"Average daily cost: ${mean_cost:.2f}")
                self.log(f"Standard deviation: ${stdev_cost:.2f}")
                self.log(f"Anomaly threshold: ${threshold:.2f} deviation from mean")
                
                # Look for anomalies
                anomalies = []
                for date, cost in daily_costs:
                    if abs(cost - mean_cost) > threshold:
                        anomalies.append((date, cost, cost - mean_cost))
                
                if anomalies:
                    self.log("\nDetected Cost Anomalies:")
                    for date, cost, deviation in anomalies:
                        deviation_str = f"+${deviation:.2f}" if deviation > 0 else f"-${abs(deviation):.2f}"
                        self.log(f"  {date}: ${cost:.2f} ({deviation_str} from average)")
                else:
                    self.log("\nNo cost anomalies detected.")
            
            except statistics.StatisticsError:
                # Fall back to simpler method if stdev fails
                self._simple_anomaly_detection(daily_costs, mean_cost)
        else:
            # Use simpler method for small datasets
            self._simple_anomaly_detection(daily_costs, mean_cost)
    
    def _simple_anomaly_detection(self, daily_costs, mean_cost):
        """Simple anomaly detection for small datasets."""
        # Use 50% deviation from mean as anomaly threshold
        threshold = max(mean_cost * 0.5, 0.5)  # At least $0.50 or 50% of mean
        
        self.log(f"Average daily cost: ${mean_cost:.2f}")
        self.log(f"Anomaly threshold: ${threshold:.2f} deviation from mean")
        
        # Look for anomalies
        anomalies = []
        for date, cost in daily_costs:
            if abs(cost - mean_cost) > threshold:
                anomalies.append((date, cost, cost - mean_cost))
        
        if anomalies:
            self.log("\nDetected Cost Anomalies:")
            for date, cost, deviation in anomalies:
                deviation_str = f"+${deviation:.2f}" if deviation > 0 else f"-${abs(deviation):.2f}"
                self.log(f"  {date}: ${cost:.2f} ({deviation_str} from average)")
        else:
            self.log("\nNo cost anomalies detected.")
    
    def check_cost_threshold_alerts(self, daily_costs):
        """Check if any daily costs exceed the alert threshold."""
        self.log(f"\n=== Cost Threshold Alerts (>${self.alert_threshold:.2f}/day) ===")
        
        alerts = []
        for date, cost in daily_costs:
            if cost > self.alert_threshold:
                alerts.append((date, cost))
        
        if alerts:
            self.log("⚠️ ALERT: The following days exceeded your cost threshold:")
            for date, cost in alerts:
                self.log(f"  {date}: ${cost:.2f} (threshold: ${self.alert_threshold:.2f})")
        else:
            self.log(f"✓ No days exceeded your cost threshold of ${self.alert_threshold:.2f}")
        
        return alerts
    
    def display_cost_forecast(self, days=30):
        """Display cost forecast for the next X days."""
        self.log(f"\n=== AWS Cost Forecast (Next {days} Days) ===")
        
        # Get the AWS-provided forecast if available
        aws_forecast = self.get_cost_forecast(days_forward=days)
        
        if aws_forecast and 'Total' in aws_forecast:
            # AWS forecast is available
            forecast_total = float(aws_forecast['Total']['Amount'])
            forecast_start = aws_forecast['TimePeriod']['Start']
            forecast_end = aws_forecast['TimePeriod']['End']
            
            self.log(f"Period: {forecast_start} to {forecast_end}")
            self.log(f"AWS Forecasted Cost: ${forecast_total:.2f}")
            
            if 'MeanValue' in aws_forecast:
                self.log(f"Mean Value: ${float(aws_forecast['MeanValue']):.2f}")
            
            if 'PredictionIntervalLowerBound' in aws_forecast and 'PredictionIntervalUpperBound' in aws_forecast:
                lower_bound = float(aws_forecast['PredictionIntervalLowerBound'])
                upper_bound = float(aws_forecast['PredictionIntervalUpperBound'])
                self.log(f"Prediction Interval: ${lower_bound:.2f} to ${upper_bound:.2f}")
        else:
            # AWS forecast not available, use our own calculation
            self.log("Generating simple forecast based on your recent daily costs:")
            
            # Get daily costs for last 7 days
            response = self.get_daily_costs(days_back=7)
            
            # Calculate average daily cost
            total_cost = 0.0
            days_with_data = 0
            
            for result in response['ResultsByTime']:
                cost = float(result['Total']['BlendedCost']['Amount'])
                if cost > 0:
                    total_cost += cost
                    days_with_data += 1
            
            if days_with_data > 0:
                avg_daily_cost = total_cost / days_with_data
                forecast_total = avg_daily_cost * days
                
                today = datetime.now()
                forecast_end = (today + timedelta(days=days)).strftime("%Y-%m-%d")
                
                self.log(f"Period: {today.strftime('%Y-%m-%d')} to {forecast_end}")
                self.log(f"Average Daily Cost: ${avg_daily_cost:.2f}")
                self.log(f"Simple Forecast (next {days} days): ${forecast_total:.2f}")
                
                # Show monthly estimate
                monthly_estimate = avg_daily_cost * 30
                self.log(f"Monthly Estimate: ${monthly_estimate:.2f}")
            else:
                self.log("Insufficient recent cost data to generate a simple forecast.")
                self.log("Please check back when you have more cost history.")
    
    def send_email_report(self, subject=None):
        """Send the cost report via email."""
        if not self.report_content:
            print("No report content to send.")
            return False
        
        # Default subject if none provided
        if not subject:
            subject = f"AWS Cost Analysis Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = self.notify_email  # Using same email for From and To
        msg['To'] = self.notify_email
        msg['Subject'] = subject
        
        # Convert the report content to plain text
        body = "\n".join(self.report_content)
        
        # Attach the body to the email
        msg.attach(MIMEText(body, 'plain'))
        
        try:
            # Send email using AWS SES if available
            try:
                ses = self.session.client('ses', region_name='us-east-1')
                response = ses.send_email(
                    Source=self.notify_email,
                    Destination={'ToAddresses': [self.notify_email]},
                    Message={
                        'Subject': {'Data': subject},
                        'Body': {'Text': {'Data': body}}
                    }
                )
                print(f"Email sent via AWS SES: {response['MessageId']}")
                return True
            except Exception as e:
                print(f"AWS SES email failed: {str(e)}")
                print("Falling back to SMTP...")
                
                # Fall back to regular SMTP if AWS SES fails
                # Note: This requires SMTP credentials to be set in environment variables
                smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
                smtp_port = int(os.environ.get("SMTP_PORT", 587))
                smtp_username = os.environ.get("SMTP_USERNAME", "")
                smtp_password = os.environ.get("SMTP_PASSWORD", "")
                
                if not smtp_username or not smtp_password:
                    print("SMTP credentials not found in environment variables.")
                    print("Add SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, and SMTP_PASSWORD to your .env file.")
                    return False
                
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(smtp_username, smtp_password)
                    server.send_message(msg)
                
                print(f"Email sent via SMTP to {self.notify_email}")
                return True
                
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    def run_cost_analysis(self, months=1, days=14, forecast_days=30, send_email=False, alert_only_email=False):
        """Run comprehensive cost analysis.
        
        Args:
            months: Number of months to analyze for monthly reports
            days: Number of days to show in daily cost report
            forecast_days: Number of days to forecast costs
            send_email: Whether to send the report via email
            alert_only_email: If True, only send email when charges exceed threshold
        """
        # Clear previous report content
        self.report_content = []
        
        # Start the report
        self.log("\n*** AWS Cost Analysis Report ***")
        self.log(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Account: {self.get_account_id()}")
        
        # Monthly costs overview
        self.display_monthly_costs(months=months)
        
        # Service breakdown
        self.display_service_costs(months=months)
        
        # Usage type breakdown
        self.display_usage_type_costs(months=months)
        
        # Daily costs and anomaly detection
        daily_costs = self.display_daily_costs(days=days)
        
        # Anomaly detection
        self.detect_cost_anomalies(daily_costs)
        
        # Cost threshold alerts
        alerts = self.check_cost_threshold_alerts(daily_costs)
        
        # Cost forecast
        self.display_cost_forecast(days=forecast_days)
        
        # End of report
        self.log("\n*** End of AWS Cost Analysis Report ***")
        
        # Send email if requested
        if send_email:
            # If alert_only_email is True, only send if there are alerts
            if alert_only_email:
                if alerts:
                    subject = f"⚠️ AWS Cost Alert - Threshold of ${self.alert_threshold:.2f} Exceeded - {datetime.now().strftime('%Y-%m-%d')}"
                    self.send_email_report(subject=subject)
                    self.log(f"\nAlert email sent to {self.notify_email}")
                else:
                    self.log(f"\nNo alerts found. Email not sent (alert_only_email=True)")
            else:
                # Always send email
                self.send_email_report()
                self.log(f"\nEmail report sent to {self.notify_email}")
            
        return daily_costs
    
    def schedule_daily_email(self):
        """Information about scheduling the script to run daily."""
        self.log("\n=== How to Schedule Daily Email Reports ===")
        self.log("To receive this report daily via email, set up a cron job or scheduled task:")
        
        # For Unix/Linux/macOS
        self.log("\nOn Unix/Linux/macOS (crontab):")
        script_path = os.path.abspath(__file__)
        self.log(f"# Daily full report at 8 AM:")
        self.log(f"0 8 * * * cd {os.path.dirname(script_path)} && python3 {script_path} --send_email=True")
        self.log(f"\n# Alert emails only when costs exceed ${self.alert_threshold:.2f}:")
        self.log(f"0 8 * * * cd {os.path.dirname(script_path)} && python3 {script_path} --send_email=True --alert_only_email=True")
        
        # For Windows
        self.log("\nOn Windows (Task Scheduler):")
        self.log("1. Create a batch file with this command for daily full reports:")
        self.log(f"   python \"{script_path}\" --send_email=True")
        self.log("\n   OR for alert emails only when costs exceed threshold:")
        self.log(f"   python \"{script_path}\" --send_email=True --alert_only_email=True")
        self.log("2. Use Task Scheduler to run this batch file daily")
    
    def get_account_id(self):
        """Get the AWS account ID."""
        sts = self.session.client('sts')
        return sts.get_caller_identity()["Account"]


def main(months=1, days=14, forecast=30, alert_threshold=1.0, notify_email=None, send_email=False, alert_only_email=False, schedule_info=False):
    """Run AWS cost monitoring with optional parameters.
    
    Args:
        months: Number of months to analyze for monthly reports (default: 1)
        days: Number of days to show in daily cost report (default: 14)
        forecast: Number of days to forecast costs (default: 30)
        alert_threshold: Dollar amount for cost alerts (default: 1.0)
        notify_email: Email address for notifications (uses .env setting or default if not specified)
        send_email: Whether to send the report via email (default: False)
        alert_only_email: If True, only send email when charges exceed threshold (default: False)
        schedule_info: Show information about scheduling daily reports (default: False)
    """
    monitor = AWSCostMonitor(alert_threshold=alert_threshold, notify_email=notify_email)
    daily_costs = monitor.run_cost_analysis(months=months, days=days, forecast_days=forecast, send_email=send_email, alert_only_email=alert_only_email)
    
    if schedule_info:
        monitor.schedule_daily_email()


if __name__ == "__main__":
    fire.Fire(main)

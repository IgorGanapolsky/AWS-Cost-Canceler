#!/usr/bin/env python3
"""
Focused test suite for AWS Cost Dashboard functionality improvements.
Tests the recently added features using static code analysis:
1. Service cancellation persistence using localStorage
2. Cost Explorer information modal
"""

import os
import sys
import json
from pathlib import Path

class DashboardTest:
    def __init__(self):
        self.repo_root = Path(__file__).parent.parent
        self.report_js = self.repo_root / "src" / "nova_cost" / "templates" / "static" / "js" / "report.js"
        self.template_html = self.repo_root / "src" / "nova_cost" / "templates" / "report_template.html"
        self.results = []
        
    def test_js_cancellation_functions(self):
        """Test that the JS file contains the cancellation functions we implemented."""
        with open(self.report_js, 'r') as f:
            js_content = f.read()
        
        # Check for localStorage functions
        test_cases = [
            ('localStorage.setItem(\'cancelledServices\'', "Setting cancelled services in localStorage"),
            ('localStorage.getItem(\'cancelledServices\'', "Getting cancelled services from localStorage"),
            ('function loadCancelledServices', "Function to load cancelled services exists"),
            ('statusCell.innerHTML', "UI update for service status"),
            ('cancelledServices', "Managing cancelled services object")
        ]
        
        for pattern, description in test_cases:
            if pattern in js_content:
                self.results.append(f"✓ PASS: {description}")
            else:
                self.results.append(f"✗ FAIL: {description} - pattern '{pattern}' not found")
    
    def test_html_cost_explorer_modal(self):
        """Test that the HTML contains the Cost Explorer info modal with all required elements."""
        with open(self.template_html, 'r') as f:
            html_content = f.read()
        
        # Check for modal elements
        test_cases = [
            ('id="costExplorerInfoModal"', "Cost Explorer info modal exists"),
            ('Understanding AWS Cost Explorer Charges', "Modal has correct title"),
            ('What', "Modal has 'What's causing these charges' section"),
            ('How to investigate', "Modal has 'How to investigate' section"),
            ('How to reduce', "Modal has 'How to reduce' section"),
            ('Boto3', "Modal includes Boto3 information"),
            ('CloudTrail', "Modal includes CloudTrail information"),
            ('Investigate API Usage', "Modal has 'Investigate API Usage' button")
        ]
        
        for pattern, description in test_cases:
            if pattern in html_content:
                self.results.append(f"✓ PASS: {description}")
            else:
                self.results.append(f"✗ FAIL: {description} - pattern '{pattern}' not found")
    
    def test_html_pay_as_you_go_services(self):
        """Test that the HTML contains the Pay-As-You-Go service handling."""
        with open(self.template_html, 'r') as f:
            html_content = f.read()
        
        # Check for pay-as-you-go elements
        test_cases = [
            ('Pay-As-You-Go', "Pay-As-You-Go service status label exists"),
            ('showPayAsYouGoInfo', "Pay-As-You-Go info modal function exists"),
            ('Managing Amazon Rekognition Usage', "Rekognition specific guidance exists"),
            ('Managing Amazon Transcribe Usage', "Transcribe specific guidance exists"),
            ('Manage Usage', "Manage Usage button for pay-as-you-go services exists")
        ]
        
        for pattern, description in test_cases:
            if pattern in html_content:
                self.results.append(f"✓ PASS: {description}")
            else:
                self.results.append(f"✗ FAIL: {description} - pattern '{pattern}' not found")
    
    def test_integration_of_features(self):
        """Test that all features are properly integrated together."""
        try:
            # Generate a fresh report
            print("Generating AWS Cost Dashboard report...")
            result = os.system(f"cd {self.repo_root} && python3 run_report.py")
            
            if result == 0:
                self.results.append("✓ PASS: Dashboard report generation successful")
                
                # Check for any report file
                report_dir = self.repo_root / "data" / "reports"
                report_files = list(report_dir.glob("aws_cost_report_*.html"))
                
                if report_files:
                    latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
                    self.results.append(f"✓ PASS: Dashboard report created at {latest_report}")
                    print(f"To view the report and manually test features: open {latest_report}")
                else:
                    self.results.append(f"✗ FAIL: No dashboard reports found in {report_dir}")
            else:
                self.results.append("✗ FAIL: Dashboard report generation failed")
        
        except Exception as e:
            self.results.append(f"✗ FAIL: Error during integration test - {str(e)}")
    
    def run_tests(self):
        """Run all dashboard tests and print results."""
        print("=== AWS Cost Dashboard Feature Tests ===\n")
        
        print("Testing cancellation persistence implementation...")
        self.test_js_cancellation_functions()
        
        print("Testing Cost Explorer information modal...")
        self.test_html_cost_explorer_modal()
        
        print("Testing Pay-As-You-Go service handling...")
        self.test_html_pay_as_you_go_services()
        
        print("Testing dashboard generation and integration...")
        self.test_integration_of_features()
        
        # Print results
        print("\n=== Test Results ===\n")
        
        passes = sum(1 for r in self.results if r.startswith("✓"))
        fails = sum(1 for r in self.results if r.startswith("✗"))
        
        for result in self.results:
            print(result)
        
        print(f"\nSummary: {passes} tests passed, {fails} tests failed")
        print("\nManual verification instructions:")
        print("1. Open the generated report in a browser")
        print("2. Try cancelling a service and refresh the page - the cancellation should persist")
        print("3. Find AWS Cost Explorer in the services list and click 'Investigate API Usage'")
        print("4. Verify the modal appears with all the expected content")
        print("5. Verify Pay-As-You-Go services are handled correctly")
        
        return passes, fails


if __name__ == '__main__':
    print("Running AWS Cost Dashboard tests...\n")
    test = DashboardTest()
    passes, fails = test.run_tests()
    
    # Return a proper exit code
    sys.exit(1 if fails > 0 else 0)

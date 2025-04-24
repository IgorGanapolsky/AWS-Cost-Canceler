#!/usr/bin/env python3
"""
Dashboard feature tests for the AWS Cost Dashboard.
Verifies core functionality using static code analysis.
"""

import sys
from pathlib import Path

# Add the parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent))

# Import test modules
from tests.test_dashboard_features import DashboardTest

def main():
    """Run the dashboard features tests"""
    print("Running AWS Cost Dashboard Feature Tests")
    print("=======================================")
    
    # Create test instance
    test = DashboardTest()
    
    # Run tests
    print("\nTesting JS cancellation functions...")
    test.test_js_cancellation_functions()
    print_test_results(test.results)
    test.results = []  # Clear results for next test
    
    print("\nTesting Cost Explorer modal...")
    test.test_html_cost_explorer_modal()
    print_test_results(test.results)
    test.results = []  # Clear results for next test
    
    print("\nAll tests completed!")
    return 0

def print_test_results(results):
    """Print test results in a readable format"""
    if not results:
        print("No results returned")
        return
        
    for result in results:
        print(f"  {result}")

if __name__ == "__main__":
    sys.exit(main())

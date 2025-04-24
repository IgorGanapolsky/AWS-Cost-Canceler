#!/usr/bin/env python3
"""
AWS Cost Report Runner

The main entry point for the AWS Cost Analysis tool.
Built using Hexagonal Architecture for clean separation of concerns.

Usage:
    python run_report.py [--days=30] [--output=path/to/report.html] [--open]
    python run_report.py --api --port=5000  # Run API server

Options:
    --days         Number of days to analyze (default: 30)
    --output       Custom output path for the report
    --open         Open the report in browser after generation
    --analyze      Analyze costs instead of generating a report
    --threshold    Cost threshold for analysis (default: 10.0)
    --api          Run the API server
    --port         Port to run the API server on (default: 5000)
    --host         Host to run the API server on (default: 0.0.0.0)
    --no-debug     Disable debug mode for API server
"""
import os
import sys
import argparse
import importlib.util
import traceback
import webbrowser


def import_from_path(module_name, file_path):
    """Import a module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_hexagonal_architecture(days=30, output=None, analyze=False, threshold=10.0, open_report=True,
                              run_api=False, api_host="0.0.0.0", api_port=5000, api_debug=True):
    """Run the new hexagonal architecture implementation."""
    try:
        # Add the project directory to the Python path
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, base_dir)
        
        # Import the nova_cost module
        print("Starting AWS Cost Report using Hexagonal Architecture...")
        
        try:
            from src.nova_cost import create_service, generate_report, analyze_costs, run_api as start_api_server
        except ImportError:
            print("Error importing nova_cost. Using relative import...")
            sys.path.insert(0, os.path.join(base_dir, 'src'))
            from nova_cost import create_service, generate_report, analyze_costs, run_api as start_api_server
        
        if run_api:
            # Run the API server
            print(f"Starting API server on {api_host}:{api_port}...")
            print("Press Ctrl+C to stop the server")
            try:
                app = start_api_server(host=api_host, port=api_port, debug=api_debug)
                return 0, app
            except KeyboardInterrupt:
                print("\nAPI server stopped")
                return 0, None
            except Exception as e:
                print(f"Error running API server: {str(e)}")
                traceback.print_exc()
                return 1, None
        elif analyze:
            # Analyze costs
            high_cost_services = analyze_costs(threshold=threshold, days_back=days)
            
            # Print analysis results
            if high_cost_services:
                print(f"\n=== Services above ${threshold:.2f} threshold ===")
                for service in high_cost_services:
                    print(f"{service['service']}: ${service['cost']:.2f}")
            else:
                print(f"\nNo services found above ${threshold:.2f} threshold")
            
            return 0, None
        else:
            # Generate report
            report_path = generate_report(days_back=days, output_path=output, open_report=open_report)
            
            if report_path:
                print(f"Report generated at: {report_path}")
                return 0, report_path
            else:
                print("Error: Report path not returned.")
                return 1, None
    
    except Exception as e:
        print(f"Error running AWS Cost Report with hexagonal architecture: {str(e)}")
        traceback.print_exc()
        return 1, None


def main():
    """Parse arguments and run the appropriate implementation."""
    parser = argparse.ArgumentParser(description="AWS Cost Report Runner")
    parser.add_argument("--days", type=int, default=30, help="Number of days to analyze")
    parser.add_argument("--output", help="Custom output path for the report")
    parser.add_argument("--open", action="store_true", default=True, help="Open report in browser")
    parser.add_argument("--analyze", action="store_true", help="Analyze costs instead of generating report")
    parser.add_argument("--threshold", type=float, default=10.0, help="Cost threshold for analysis")
    parser.add_argument("--api", action="store_true", help="Run the API server")
    parser.add_argument("--port", type=int, default=5000, help="Port to run the API server on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to run the API server on")
    parser.add_argument("--no-debug", action="store_true", help="Disable debug mode for API server")
    
    args = parser.parse_args()
    
    return run_hexagonal_architecture(
        days=args.days,
        output=args.output,
        analyze=args.analyze,
        threshold=args.threshold,
        open_report=args.open,
        run_api=args.api,
        api_host=args.host,
        api_port=args.port,
        api_debug=not args.no_debug
    )[0]


if __name__ == "__main__":
    sys.exit(main())

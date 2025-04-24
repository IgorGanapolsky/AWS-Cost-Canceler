#!/usr/bin/env python3
"""
Test Runner for Nova Cost

This script provides a convenient way to run all tests or specific test suites.
It supports running unit tests, integration tests, or all tests together.
"""
import os
import sys
import unittest
import argparse


def discover_and_run_tests(pattern=None, verbose=False):
    """
    Discover and run tests matching the specified pattern
    
    Args:
        pattern: Pattern to match for test discovery
        verbose: Whether to show verbose output
    
    Returns:
        True if all tests passed, False otherwise
    """
    # Determine verbosity level
    verbosity = 2 if verbose else 1
    
    # Create test loader
    loader = unittest.TestLoader()
    
    # Discover tests
    if pattern:
        suite = loader.discover('tests', pattern=f'test_{pattern}.py')
    else:
        suite = loader.discover('tests')
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Return True if all tests passed, False otherwise
    return result.wasSuccessful()


def run_specific_test_file(file_path, verbose=False):
    """
    Run a specific test file
    
    Args:
        file_path: Path to the test file
        verbose: Whether to show verbose output
    
    Returns:
        True if all tests passed, False otherwise
    """
    # Check if the file exists
    if not os.path.exists(file_path):
        print(f"Error: Test file '{file_path}' does not exist")
        return False
    
    # Determine verbosity level
    verbosity = 2 if verbose else 1
    
    # Import the file as a module
    import importlib.util
    spec = importlib.util.spec_from_file_location("test_module", file_path)
    test_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(test_module)
    
    # Run the tests in the file
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(test_module)
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    # Return True if all tests passed, False otherwise
    return result.wasSuccessful()


def main():
    """Parse command line arguments and run tests"""
    parser = argparse.ArgumentParser(description='Run Nova Cost tests')
    
    # Add options for test selection
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--unit', action='store_true', help='Run only unit tests')
    group.add_argument('--integration', action='store_true', help='Run only integration tests')
    group.add_argument('--file', help='Run a specific test file')
    
    # Add option for verbose output
    parser.add_argument('-v', '--verbose', action='store_true', help='Show verbose output')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Print header
    print("=" * 70)
    print("Nova Cost Test Runner")
    print("=" * 70)
    
    # Run the requested tests
    if args.unit:
        print("Running unit tests...\n")
        success = discover_and_run_tests('aws_adapter|html_adapter|cost_analysis_service|cli', args.verbose)
    elif args.integration:
        print("Running integration tests...\n")
        success = discover_and_run_tests('integration', args.verbose)
    elif args.file:
        print(f"Running tests from file: {args.file}\n")
        success = run_specific_test_file(args.file, args.verbose)
    else:
        print("Running all tests...\n")
        success = discover_and_run_tests(None, args.verbose)
    
    # Print summary
    print("\n" + "=" * 70)
    if success:
        print("All tests passed!")
    else:
        print("Some tests failed!")
    
    # Return exit code
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

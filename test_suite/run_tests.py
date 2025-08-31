#!/usr/bin/env python3
"""
Test runner script for caption generator verification.
Provides easy commands to run different test suites.
"""
import subprocess
import sys
import os


def run_command(cmd, description):
    """Run a command and print results."""
    print(f"\nTOOL: {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)
    
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    if result.returncode == 0:
        print(f"PASS: {description}")
    else:
        print(f"FAIL: {description}")
    
    return result.returncode == 0


def main():
    """Main test runner."""
    if len(sys.argv) < 2:
        print("Usage: python run_tests.py [test_type]")
        print("\nAvailable test types:")
        print("  all           - Run all tests")
        print("  blog          - Test blog content extraction only")
        print("  caption       - Test caption generation only") 
        print("  integration   - Test full integration pipeline")
        print("  quick         - Run quick tests (no live APIs)")
        print("  install       - Install test dependencies")
        sys.exit(1)
    
    test_type = sys.argv[1].lower()
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        if test_type != 'install':
            print("FAIL: pytest not found. Run: python run_tests.py install")
            sys.exit(1)
    
    if test_type == 'install':
        print("INSTALL: Installing test dependencies...")
        success = run_command([sys.executable, '-m', 'pip', 'install', '-r', 'test_requirements.txt'], 
                            "Installing test dependencies")
        if success:
            print("\nPASS: Test dependencies installed successfully!")
            print("You can now run tests with: python run_tests.py all")
        sys.exit(0 if success else 1)
    
    # Set environment variables for testing - parent directory should be in PYTHONPATH
    parent_dir = os.path.dirname(os.getcwd())
    os.environ['PYTHONPATH'] = parent_dir
    
    success = True
    
    if test_type == 'all':
        print("TEST: Running all tests...")
        success &= run_command([sys.executable, '-m', 'pytest', '-v'], "All tests")
        
    elif test_type == 'blog':
        print("WEB: Testing blog content extraction...")
        success &= run_command([sys.executable, '-m', 'pytest', 'test_blog_content_extractor.py', '-v'], 
                             "Blog content extraction tests")
        
    elif test_type == 'caption':
        print("CAPTION: Testing caption generation...")
        success &= run_command([sys.executable, '-m', 'pytest', 'test_caption_generator.py', '-v'], 
                             "Caption generation tests")
        
    elif test_type == 'integration':
        print("INTEGRATION: Testing integration pipeline...")
        success &= run_command([sys.executable, '-m', 'pytest', 'test_integration.py', '-v', '-s'], 
                             "Integration tests")
        
    elif test_type == 'quick':
        print("QUICK: Running quick tests (no live APIs)...")
        success &= run_command([sys.executable, '-m', 'pytest', '-v', '-k', 'not live'], 
                             "Quick tests")
        
    else:
        print(f"FAIL: Unknown test type: {test_type}")
        sys.exit(1)
    
    if success:
        print(f"\nSUCCESS: All {test_type} tests completed successfully!")
    else:
        print(f"\nERROR: Some {test_type} tests failed!")
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
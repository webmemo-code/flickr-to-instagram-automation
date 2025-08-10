#!/usr/bin/env python3
"""
Test script to verify the image retry mechanism works correctly.
"""
import os
import sys
import logging
from config import Config
from instagram_api import InstagramAPI

def setup_test_logging():
    """Setup logging for testing."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_image_validation_retry():
    """Test the image validation retry mechanism."""
    print("=== 🧪 Testing Image Validation Retry Mechanism ===\n")
    
    try:
        # Load config
        config = Config()
        instagram_api = InstagramAPI(config)
        
        # Test cases
        test_cases = [
            {
                'name': 'Valid Flickr Image (should succeed immediately)',
                'url': 'https://live.staticflickr.com/65535/54585395380_e5c8c5b8cb_c.jpg',  # Real Flickr image
                'expected': True,
                'test_retry': False  # Use normal retry settings
            },
            {
                'name': 'Invalid URL (should fail after retries)',
                'url': 'https://invalid-domain-that-does-not-exist.com/image.jpg',
                'expected': False,
                'test_retry': True,
                'max_retries': 2,
                'retry_delay': 3  # Shorter delay for testing
            },
            {
                'name': 'Valid domain but 404 image (should fail quickly)',
                'url': 'https://httpbin.org/status/404',
                'expected': False,
                'test_retry': True,
                'max_retries': 2,
                'retry_delay': 3
            }
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"📋 Test {i}: {test_case['name']}")
            print(f"   URL: {test_case['url']}")
            
            # Run the test
            if test_case.get('test_retry'):
                result = instagram_api.validate_image_url(
                    test_case['url'],
                    max_retries=test_case.get('max_retries', 2),
                    retry_delay=test_case.get('retry_delay', 60)
                )
            else:
                result = instagram_api.validate_image_url(test_case['url'])
            
            # Check result
            success = result == test_case['expected']
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   Result: {result} (expected: {test_case['expected']}) - {status}\n")
            
            results.append({
                'test': test_case['name'],
                'passed': success,
                'result': result,
                'expected': test_case['expected']
            })
        
        # Summary
        print("=== 📊 Test Summary ===")
        passed = sum(1 for r in results if r['passed'])
        total = len(results)
        
        for result in results:
            status = "✅" if result['passed'] else "❌"
            print(f"{status} {result['test']}")
        
        print(f"\n🎯 Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Retry mechanism is working correctly.")
            return True
        else:
            print("⚠️ Some tests failed. Please review the retry logic.")
            return False
            
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        print("Make sure you have a valid .env file with the required environment variables.")
        return False

if __name__ == "__main__":
    setup_test_logging()
    success = test_image_validation_retry()
    sys.exit(0 if success else 1)
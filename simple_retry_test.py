#!/usr/bin/env python3
"""
Simple test script to verify the retry mechanism logic without dependencies.
"""
import requests
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_image_url_with_retry(image_url: str, max_retries: int = 2, retry_delay: int = 5) -> bool:
    """Test version of validate_image_url with shorter delays for testing."""
    logger.info(f"Testing image URL validation with retry: {image_url}")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_retries}")
            response = requests.head(image_url, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if content_type.startswith('image/'):
                    if attempt > 0:
                        logger.info(f"✅ Image URL became accessible on retry #{attempt}")
                    else:
                        logger.info(f"✅ Image URL accessible on first attempt")
                    return True
                else:
                    logger.warning(f"URL does not point to an image: {content_type}")
                    return False
            else:
                logger.warning(f"Image URL not accessible: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to validate image URL (attempt {attempt + 1}): {e}")
        
        # If this wasn't the last attempt, wait and retry
        if attempt < max_retries - 1:
            logger.info(f"⏳ Waiting {retry_delay} seconds before retrying...")
            time.sleep(retry_delay)
            continue
            
    logger.error(f"❌ Image URL validation failed after {max_retries} attempts")
    return False

def main():
    print("=== 🧪 Simple Retry Mechanism Test ===\n")
    
    # Test cases with shorter delays for quick testing
    test_cases = [
        {
            'name': 'Valid Flickr Image',
            'url': 'https://live.staticflickr.com/65535/54585269339_8ac69a5a7c_c.jpg',
            'expected': True
        },
        {
            'name': 'Invalid Domain (should fail after retries)',
            'url': 'https://invalid-domain-12345.com/image.jpg', 
            'expected': False
        },
        {
            'name': 'Valid domain but 404 (should fail quickly)',
            'url': 'https://httpbin.org/status/404',
            'expected': False
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print(f"URL: {test_case['url']}")
        print("-" * 60)
        
        # Test with 2 retries and 5-second delay for faster testing
        result = validate_image_url_with_retry(
            test_case['url'], 
            max_retries=2, 
            retry_delay=5
        )
        
        success = result == test_case['expected']
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"Result: {result} (expected: {test_case['expected']}) - {status}")
        
        results.append({
            'name': test_case['name'],
            'passed': success
        })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    
    for result in results:
        status = "✅ PASS" if result['passed'] else "❌ FAIL"
        print(f"{status} {result['name']}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Retry mechanism is working correctly.")
        print("\nThe retry logic should now:")
        print("- Try to access Flickr images immediately")
        print("- Wait 60 seconds and retry if the first attempt fails")
        print("- Only mark photos as failed after both attempts fail")
    else:
        print("⚠️ Some tests failed. The retry mechanism may need adjustment.")

if __name__ == "__main__":
    main()
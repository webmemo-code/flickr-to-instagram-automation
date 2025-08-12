#!/usr/bin/env python3
"""
Minimal test to debug Flickr API response.
"""
import requests
import json
import os

def test_flickr_api():
    """Test the Flickr API call directly."""
    
    # Use the same parameters as the working code
    params = {
        'method': 'flickr.photosets.getPhotos',
        'api_key': os.getenv('FLICKR_API_KEY', 'missing'),
        'user_id': os.getenv('FLICKR_USER_ID', 'missing'),
        'photoset_id': os.getenv('FLICKR_ALBUM_ID', '72177720326837749'),
        'format': 'json',
        'nojsoncallback': '1'
    }
    
    print("=== 🔍 Testing Flickr API Call ===")
    print(f"API Key: {'SET' if params['api_key'] != 'missing' else 'MISSING'}")
    print(f"User ID: {params['user_id']}")
    print(f"Album ID: {params['photoset_id']}")
    print(f"URL: https://www.flickr.com/services/rest/")
    
    try:
        print("\n🌐 Making API request...")
        response = requests.get('https://www.flickr.com/services/rest/', params=params, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
        print(f"Response Length: {len(response.text)} characters")
        
        # Show first 300 characters of response
        print(f"\nFirst 300 chars of response:")
        print(f"'{response.text[:300]}...'")
        
        if response.text.strip():
            try:
                data = response.json()
                print(f"\n📊 JSON Data Structure:")
                print(f"Top-level keys: {list(data.keys())}")
                print(f"Stat: {data.get('stat', 'missing')}")
                
                if data.get('stat') == 'ok':
                    print("✅ API call successful!")
                    
                    if 'photoset' in data:
                        print(f"Photoset keys: {list(data['photoset'].keys())}")
                        if 'photo' in data['photoset']:
                            print(f"Photos found: {len(data['photoset']['photo'])}")
                        else:
                            print("❌ Missing 'photo' key in photoset")
                    else:
                        print("❌ Missing 'photoset' key in response")
                        
                else:
                    print(f"❌ API error: {data.get('message', 'Unknown')}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON decode error: {e}")
        else:
            print("❌ Empty response from API")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_flickr_api()
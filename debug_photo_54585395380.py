#!/usr/bin/env python3
"""
Debug script to investigate why photo 54585395380 keeps being selected.
"""

def debug_photo_selection():
    """Debug the specific photo selection issue."""
    print("=== 🔍 Debugging Photo 54585395380 ===\n")
    
    target_photo_id = "54585395380"
    
    # Simulate what the state manager should find
    print(f"🎯 Target Photo ID: {target_photo_id}")
    print(f"📝 This photo should be EXCLUDED if it has been posted")
    print(f"🔍 Issues to check:")
    print(f"   1. Does a GitHub Issue exist for this photo ID?")
    print(f"   2. Does it have the 'posted' or 'failed' label?")
    print(f"   3. Is it from the current album (72177720326837749)?")
    print(f"   4. Is the photo ID extraction working correctly?")
    print(f"   5. Is the album filtering working correctly?")
    
    print(f"\n📋 Expected GitHub Issue format:")
    print(f"   Title: Posted: [Photo Title] (#XX) - [Timestamp]")
    print(f"   Body should contain:")
    print(f"   **Photo ID:** {target_photo_id}")
    print(f"   **Album ID:** 72177720326837749")
    print(f"   Labels: ['automated-post', 'instagram', 'flickr-album', 'posted']")
    
    print(f"\n🔧 Debug steps to check manually:")
    print(f"   1. Search GitHub Issues for '{target_photo_id}'")
    print(f"   2. Check if issue has correct labels")
    print(f"   3. Verify Album ID in issue body")
    print(f"   4. Check if state_manager.get_posted_photo_ids() includes this ID")
    
    print(f"\n📝 If you find the issue:")
    print(f"   - Check if it has 'posted' label")
    print(f"   - Check if Album ID matches 72177720326837749") 
    print(f"   - Check exact format of Photo ID line")
    print(f"   - Check for any whitespace/formatting issues")

def simulate_state_manager_logic():
    """Simulate the state manager logic for debugging."""
    print("\n=== 🧪 Simulating State Manager Logic ===\n")
    
    target_photo_id = "54585395380"
    current_album_id = "72177720326837749"
    
    # Mock GitHub Issues data - what we might expect to find
    mock_issues = [
        {
            "number": 101,
            "body": f"**Photo ID:** {target_photo_id}\n**Album ID:** {current_album_id}\n**Title:** Muggia, Triest",
            "labels": ["automated-post", "instagram", "flickr-album", "posted"]
        },
        {
            "number": 100, 
            "body": f"**Photo ID:** 12345\n**Album ID:** {current_album_id}\n**Title:** Other Photo",
            "labels": ["automated-post", "instagram", "flickr-album", "posted"]
        }
    ]
    
    print("🔍 Mock GitHub Issues found:")
    for issue in mock_issues:
        print(f"   Issue #{issue['number']}: {issue['labels']}")
        
        # Extract photo ID (simulate state_manager._extract_photo_id)
        lines = issue["body"].split('\n')
        extracted_id = None
        for line in lines:
            if line.startswith('**Photo ID:**'):
                photo_id = line.split(':', 1)[1].strip()
                if photo_id.startswith('** '):
                    photo_id = photo_id[3:]
                elif photo_id.startswith('**'):
                    photo_id = photo_id[2:].strip()
                if photo_id:
                    extracted_id = str(photo_id).strip()
                    break
        
        print(f"      Extracted ID: '{extracted_id}'")
        
        # Check if it's the target photo
        if extracted_id == target_photo_id:
            has_posted_label = "posted" in issue["labels"]
            print(f"      🎯 FOUND TARGET PHOTO!")
            print(f"      Has 'posted' label: {has_posted_label}")
            if has_posted_label:
                print(f"      ✅ Should be EXCLUDED from next selection")
            else:
                print(f"      ❌ MISSING 'posted' label - will NOT be excluded!")

def test_photo_id_comparison():
    """Test photo ID comparison logic."""
    print("\n=== 🔍 Testing Photo ID Comparison ===\n")
    
    target_id = "54585395380"
    
    # Test different formats that might cause comparison issues
    test_cases = [
        "54585395380",           # Exact match
        " 54585395380",          # Leading space
        "54585395380 ",          # Trailing space  
        " 54585395380 ",         # Both spaces
        "** 54585395380",        # With prefix
        "**54585395380",         # With prefix no space
        54585395380,             # Integer (would be converted to string)
    ]
    
    print(f"Target ID: '{target_id}' (type: {type(target_id)})")
    print("\nTesting comparisons:")
    
    for test_id in test_cases:
        # Simulate the string conversion and stripping
        converted_id = str(test_id).strip()
        matches = converted_id == target_id
        print(f"   '{test_id}' (type: {type(test_id)}) -> '{converted_id}' -> Match: {matches}")

if __name__ == "__main__":
    debug_photo_selection()
    simulate_state_manager_logic()
    test_photo_id_comparison()
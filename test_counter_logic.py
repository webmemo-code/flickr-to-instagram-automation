#!/usr/bin/env python3
"""
Test script to verify the counter logic works correctly.
"""

def test_photo_selection():
    """Test the photo selection logic."""
    print("=== 🧪 Testing Counter Logic ===\n")
    
    # Simulate photo data (sorted by ID as per our fix)
    mock_photos = [
        {'id': '12345', 'title': 'Photo A', 'album_position': 1},
        {'id': '12346', 'title': 'Photo B', 'album_position': 2}, 
        {'id': '12347', 'title': 'Photo C', 'album_position': 3},
        {'id': '12348', 'title': 'Photo D', 'album_position': 4},
        {'id': '12349', 'title': 'Photo E', 'album_position': 5},
    ]
    
    # Test scenarios
    scenarios = [
        {
            'name': 'No photos posted yet',
            'posted_ids': [],
            'failed_ids': [],
            'expected_next': 1
        },
        {
            'name': 'First 2 photos posted',
            'posted_ids': ['12345', '12346'],
            'failed_ids': [],
            'expected_next': 3
        },
        {
            'name': 'Photo 1 posted, photo 2 failed',
            'posted_ids': ['12345'],
            'failed_ids': ['12346'],
            'expected_next': 3
        },
        {
            'name': 'Photos 1,3 posted, photo 2 failed',
            'posted_ids': ['12345', '12347'],
            'failed_ids': ['12346'],
            'expected_next': 4
        }
    ]
    
    for scenario in scenarios:
        print(f"📝 Scenario: {scenario['name']}")
        
        # Simulate the selection logic
        posted_ids = scenario['posted_ids']
        failed_ids = scenario['failed_ids']
        excluded_ids = posted_ids + failed_ids
        
        print(f"   Posted IDs: {posted_ids}")
        print(f"   Failed IDs: {failed_ids}")
        print(f"   Excluded IDs: {excluded_ids}")
        
        # Find next photo (same logic as state_manager.py)
        sorted_photos = sorted(mock_photos, key=lambda x: x.get('album_position', 0))
        next_photo = None
        
        for photo in sorted_photos:
            photo_id = str(photo['id'])
            if photo_id not in excluded_ids:
                next_photo = photo
                break
        
        if next_photo:
            actual_position = next_photo['album_position']
            expected_position = scenario['expected_next']
            status = "✅ PASS" if actual_position == expected_position else "❌ FAIL"
            print(f"   Next photo: #{actual_position} - {next_photo['title']} (ID: {next_photo['id']}) {status}")
            if actual_position != expected_position:
                print(f"   Expected: #{expected_position}")
        else:
            print(f"   Next photo: None (all photos processed)")
        
        print()

def test_sorting_fix():
    """Test that our sorting fix ensures deterministic ordering."""
    print("=== 🔧 Testing Sorting Fix ===\n")
    
    # Simulate photos in different API response orders
    photos_order1 = [
        {'id': '54585395380', 'title': 'Muggia, Triest'},
        {'id': '54585123456', 'title': 'Venice Canal'},
        {'id': '54585999999', 'title': 'Rome Forum'},
    ]
    
    photos_order2 = [
        {'id': '54585999999', 'title': 'Rome Forum'},
        {'id': '54585395380', 'title': 'Muggia, Triest'},
        {'id': '54585123456', 'title': 'Venice Canal'},
    ]
    
    # Apply our sorting logic (sort by ID)
    sorted1 = sorted(photos_order1, key=lambda x: x['id'])
    sorted2 = sorted(photos_order2, key=lambda x: x['id'])
    
    # Assign positions
    for i, photo in enumerate(sorted1):
        photo['album_position'] = i + 1
    for i, photo in enumerate(sorted2):
        photo['album_position'] = i + 1
    
    print("Order 1 after sorting:")
    for photo in sorted1:
        print(f"  #{photo['album_position']}: {photo['title']} (ID: {photo['id']})")
    
    print("\nOrder 2 after sorting:")
    for photo in sorted2:
        print(f"  #{photo['album_position']}: {photo['title']} (ID: {photo['id']})")
    
    # Check if they're identical
    identical = all(p1['id'] == p2['id'] and p1['album_position'] == p2['album_position'] 
                   for p1, p2 in zip(sorted1, sorted2))
    
    status = "✅ PASS" if identical else "❌ FAIL"
    print(f"\nDeterministic ordering: {status}")
    if identical:
        print("✅ Sorting fix ensures photos will always be processed in the same order!")

if __name__ == "__main__":
    test_photo_selection()
    test_sorting_fix()
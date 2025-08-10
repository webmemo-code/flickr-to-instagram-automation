#!/usr/bin/env python3
"""
Manual Instagram verification helper - creates a simple list of posts to check manually
"""

# Based on our verification script results, these 19 posts were "verified" by the API
# But if only 9 are actually visible on Instagram, we need to identify which 10 are missing

verified_posts = [
    {
        'photo_id': '54585260629',
        'issue': '101',
        'instagram_post_id': '17978579213728807',
        'link': 'https://www.instagram.com/p/DMCtfi6NjLM/',
        'title': 'Unknown (Issue #101)'
    },
    {
        'photo_id': '54585260659',
        'issue': '99',
        'instagram_post_id': '18070037645080036',
        'link': 'https://www.instagram.com/p/DMAIpoHsYFz/',
        'title': 'Wallfahrtkirche Monte Grisa in brutalistischen Architecturstil (#18)'
    },
    {
        'photo_id': '54585260649',
        'issue': '97',
        'instagram_post_id': '18081009052886966',
        'link': 'https://www.instagram.com/p/DL9j_UntVr7/',
        'title': 'Wallfahrtkirche Monte Grisa in brutalistischen Architecturstil (#17)'
    },
    {
        'photo_id': '54585408910',
        'issue': '83',
        'instagram_post_id': '18087789184737609',
        'link': 'https://www.instagram.com/p/DLzQ7zCAeWR/',
        'title': 'Pier Molo Audace in Triest (#10)'
    },
    {
        'photo_id': '54584228412',
        'issue': '81',
        'instagram_post_id': '17980823933710842',
        'link': 'https://www.instagram.com/p/DLwr3X8t9ni/',
        'title': 'Pier Molo Audace in Triest (#9)'
    },
    {
        'photo_id': '54585282639',
        'issue': '71',
        'instagram_post_id': '18129981364441005',
        'link': 'https://www.instagram.com/p/DLriWcwsQqV/',
        'title': 'Pier Molo Audace in Triest (#4)'
    },
    {
        'photo_id': '54585097056',
        'issue': '69',
        'instagram_post_id': '18302909575170701',
        'link': 'https://www.instagram.com/p/DLo9ojoNC1b/',
        'title': 'Canale Grande von Triest (#3)'
    },
    {
        'photo_id': '54585083611',
        'issue': '67',
        'instagram_post_id': '17862659037428025',
        'link': 'https://www.instagram.com/p/DLmY6phtx8P/',
        'title': 'Grignano Miramare Castle (#2)'
    },
    {
        'photo_id': '54585298228',
        'issue': '65',
        'instagram_post_id': '18043169993289156',
        'link': 'https://www.instagram.com/p/DLj0Gxmo1NK/',
        'title': 'Grignano Miramare Castle (#1)'
    },
    {
        'photo_id': '54585949671',
        'issue': '61',
        'instagram_post_id': '18109821790508454',
        'link': 'https://www.instagram.com/p/DLZguRxPJ9p/',
        'title': 'Agli Amici Rovinj gourmet dinner (#11)'
    },
    {
        'photo_id': '54586262055',
        'issue': '59',
        'instagram_post_id': '18407206489108480',
        'link': 'https://www.instagram.com/p/DLW7-ZBN4T6/',
        'title': 'Agli Amici Rovinj gourmet dinner (#10)'
    },
    {
        'photo_id': '54586165553',
        'issue': '57',
        'instagram_post_id': '17851475772474668',
        'link': 'https://www.instagram.com/p/DLUXR2ktrS8/',
        'title': 'Agli Amici Rovinj gourmet dinner pre-dessert (#9)'
    },
    {
        'photo_id': '54585949716',
        'issue': '55',
        'instagram_post_id': '17911461363118695',
        'link': 'https://www.instagram.com/p/DLRybIKt2TV/',
        'title': 'Agli Amici Rovinj gourmet dinner turbot (#8)'
    },
    {
        'photo_id': '54586139364',
        'issue': '53',
        'instagram_post_id': '17912059893036934',
        'link': 'https://www.instagram.com/p/DLPNuy0NnPq/',
        'title': 'Agli Amici Rovinj gourmet dinner open kitchen (#7)'
    },
    {
        'photo_id': '54585949691',
        'issue': '51',
        'instagram_post_id': '17944052471878549',
        'link': 'https://www.instagram.com/p/DLMooq7OsKq/',
        'title': 'Michela Scarello vom Agli Amici Rovinj (#6)'
    },
    {
        'photo_id': '54586165543',
        'issue': '49',
        'instagram_post_id': '18165391267347630',
        'link': 'https://www.instagram.com/p/DLKD0yAtc6t/',
        'title': 'Gourmet dinner pennoni at Agli Amici Rovinj (#5)'
    },
    {
        'photo_id': '54585078857',
        'issue': '43',
        'instagram_post_id': '18064878680126240',
        'link': 'https://www.instagram.com/p/DLHfI6JsZxg/',
        'title': 'Agli Amici Rovinj gourmet dinner langoustines and grilled peas (#4)'
    },
    {
        'photo_id': '54586139404',
        'issue': '41',
        'instagram_post_id': '17896958823233655',
        'link': 'https://www.instagram.com/p/DLF9KHGTapq/',
        'title': 'Agli Amici Rovinj gourmet dinner scallops (#3)'
    },
    {
        'photo_id': '54586139399',
        'issue': '29',
        'instagram_post_id': '18061595428952222',
        'link': 'https://www.instagram.com/p/DLE6YflvolJ/',
        'title': 'Agli Amici Rovinj Gourmet Sommelier (#2)'
    }
]

print("=== 📱 MANUAL INSTAGRAM VERIFICATION CHECKLIST ===")
print(f"Please check your Instagram account and mark which posts are ACTUALLY VISIBLE")
print(f"Our API verification found {len(verified_posts)} posts, but you see only 9.")
print(f"We need to identify which {len(verified_posts) - 9} posts are missing.\n")

print("Instructions:")
print("1. Visit each Instagram link below")
print("2. Mark '✅' if the post is visible, '❌' if it's missing/deleted")
print("3. Report back which Issue numbers should be re-labeled as 'failed'\n")

print("=" * 80)

missing_count = 0
for i, post in enumerate(verified_posts, 1):
    print(f"#{i:2d}. Issue #{post['issue']} - {post['title']}")
    print(f"     📸 Flickr Photo ID: {post['photo_id']}")
    print(f"     🔗 Instagram Link: {post['link']}")
    print(f"     📱 Post ID: {post['instagram_post_id']}")
    print(f"     Status: [ ] ✅ Visible  [ ] ❌ Missing")
    print()

print("=" * 80)
print(f"📊 SUMMARY:")
print(f"   • API says: {len(verified_posts)} posts exist")
print(f"   • You see: 9 posts actually visible")
print(f"   • Missing: {len(verified_posts) - 9} posts need to be re-labeled as 'failed'")
print()
print("💡 After checking, tell me which Issue numbers are missing")
print("   and I'll re-label them from 'posted' to 'failed'")

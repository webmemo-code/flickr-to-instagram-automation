#!/usr/bin/env python3
"""
Test script for multi-account configuration.
"""
import os
import sys

def test_config():
    """Test the multi-account configuration."""
    sys.path.append('.')
    from config import Config
    
    print("Testing multi-account configuration...")
    
    # Test primary account
    try:
        print("\n--- Primary Account ---")
        config_primary = Config(account='primary')
        print(f"Account: {config_primary.account}")
        print(f"Album Name: {config_primary.album_name}")
        print(f"Flickr Album ID: {config_primary.flickr_album_id or 'Not set'}")
        print("+ Primary account config loaded")
    except Exception as e:
        print(f"- Primary account config failed: {e}")
    
    # Test reisememo account
    try:
        print("\n--- Reisememo Account ---")
        config_reisememo = Config(account='reisememo')
        print(f"Account: {config_reisememo.account}")
        print(f"Album Name: {config_reisememo.album_name}")
        print(f"Flickr Album ID: {config_reisememo.flickr_album_id or 'Not set'}")
        print("+ Reisememo account config loaded")
    except Exception as e:
        print(f"- Reisememo account config failed: {e}")
    
    print("\n--- Required Environment Variables Check ---")
    
    # Common variables
    common_vars = ['FLICKR_API_KEY', 'FLICKR_USER_ID', 'FLICKR_USERNAME', 'ANTHROPIC_API_KEY', 'GITHUB_TOKEN']
    
    # Primary account variables
    primary_vars = ['FLICKR_ALBUM_ID', 'INSTAGRAM_ACCESS_TOKEN', 'INSTAGRAM_ACCOUNT_ID']
    
    # Reisememo account variables
    reisememo_vars = ['FLICKR_ALBUM_ID_REISEMEMO', 'INSTAGRAM_ACCESS_TOKEN_REISEMEMO', 'INSTAGRAM_ACCOUNT_ID_REISEMEMO']
    
    print("\nCommon variables:")
    for var in common_vars:
        status = "+" if os.getenv(var) else "-"
        print(f"  {status} {var}")
    
    print("\nPrimary account variables:")
    for var in primary_vars:
        status = "+" if os.getenv(var) else "-"
        print(f"  {status} {var}")
    
    print("\nReisememo account variables:")
    for var in reisememo_vars:
        status = "+" if os.getenv(var) else "-"
        print(f"  {status} {var}")
    
    print("\n--- Test Complete ---")
    print("Note: Missing environment variables are expected in local testing.")
    print("Set them up in GitHub repository settings for actual automation.")

if __name__ == "__main__":
    test_config()
#!/usr/bin/env python3
"""
Test script for the launcher updater functionality
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from launcher_updater import LauncherUpdateManager, check_launcher_updates

def test_launcher_updater():
    """Test the launcher updater functionality"""
    print("Testing Launcher Updater...")
    
    # Test repository URL (replace with your actual repository)
    test_repo_url = "https://github.com/quentin452/CatzLauncher"
    
    # Test 1: Check for updates
    print("\n1. Checking for launcher updates...")
    try:
        update_available, update_info = check_launcher_updates(test_repo_url)
        
        if update_available:
            print(f"✅ Update available!")
            print(f"   Current version: {update_info['current_version']}")
            print(f"   New version: {update_info['new_version']}")
            print(f"   Commit message: {update_info['commit_message']}")
        else:
            print("✅ No updates available")
            
    except Exception as e:
        print(f"❌ Error checking updates: {e}")
    
    # Test 2: Create updater instance
    print("\n2. Creating updater instance...")
    try:
        updater = LauncherUpdateManager(test_repo_url)
        print(f"✅ Updater created successfully")
        print(f"   Current version: {updater.current_version}")
        print(f"   Update file: {updater.update_file}")
        
    except Exception as e:
        print(f"❌ Error creating updater: {e}")
    
    # Test 3: Get GitHub commit info
    print("\n3. Getting GitHub commit info...")
    try:
        commit_info = updater.get_github_last_commit()
        if commit_info:
            print(f"✅ Latest commit: {commit_info['short_sha']}")
            print(f"   Date: {commit_info['date']}")
            print(f"   Message: {commit_info['message']}")
        else:
            print("❌ Could not get commit info")
            
    except Exception as e:
        print(f"❌ Error getting commit info: {e}")
    
    print("\n✅ Launcher updater test completed!")

if __name__ == "__main__":
    test_launcher_updater() 
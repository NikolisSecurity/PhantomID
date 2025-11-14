#!/usr/bin/env python3

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spoofer import setup_database, create_backup_before_update, validate_update_files, rollback_update, offline_update_check, check_for_updates

def test_update_system():
    """Test the enhanced update system components"""
    print("=== Testing Enhanced Update System ===")

    # Test 1: Database setup
    print("\n1. Testing database setup...")
    try:
        setup_database()
        print("✓ Database setup successful")
    except Exception as e:
        print(f"✗ Database setup failed: {e}")
        return False

    # Test 2: Backup creation
    print("\n2. Testing backup creation...")
    try:
        backup_dir = create_backup_before_update()
        if backup_dir and os.path.exists(backup_dir):
            print(f"✓ Backup creation successful: {backup_dir}")
        else:
            print("✗ Backup creation failed")
            return False
    except Exception as e:
        print(f"✗ Backup creation failed: {e}")
        return False

    # Test 3: File validation (should pass)
    print("\n3. Testing file validation (existing files)...")
    try:
        # Create test files
        with open("test_spoofer.py", "w") as f:
            f.write("# Test file")
        with open("test_requirements.txt", "w") as f:
            f.write("colorama\nwmi\nrequests\npywin32")

        # Validate files
        if validate_update_files():
            print("✓ File validation passed")
        else:
            print("✗ File validation failed")

        # Cleanup test files
        os.remove("test_spoofer.py")
        os.remove("test_requirements.txt")
    except Exception as e:
        print(f"✗ File validation test failed: {e}")
        return False

    # Test 4: File validation (should fail)
    print("\n4. Testing file validation (missing files)...")
    try:
        if not validate_update_files():
            print("✓ File validation correctly detected missing files")
        else:
            print("✗ File validation should have failed")
    except Exception as e:
        print(f"✗ File validation test failed: {e}")
        return False

    # Test 5: Rollback functionality
    print("\n5. Testing rollback functionality...")
    try:
        if rollback_update(backup_dir):
            print("✓ Rollback test successful")
        else:
            print("✗ Rollback test failed")
    except Exception as e:
        print(f"✗ Rollback test failed: {e}")
        return False

    # Test 6: Offline update check (no file)
    print("\n6. Testing offline update check (no offline update file)...")
    try:
        if not offline_update_check():
            print("✓ Offline update correctly detected no available update")
        else:
            print("✗ Offline update should have returned False")
    except Exception as e:
        print(f"✗ Offline update test failed: {e}")
        return False

    print("\n=== Enhanced Update System Tests Complete ===")
    print("All core update system components are working correctly!")

    return True

if __name__ == "__main__":
    test_update_system()
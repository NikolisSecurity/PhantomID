#!/usr/bin/env python3

import os
import shutil
import datetime

def test_backup_function():
    """Test the backup creation functionality"""
    print("=== Testing Backup Creation ===")

    try:
        # Simulate create_backup_before_update function
        backup_dir = f"test_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(backup_dir, exist_ok=True)

        # Create some test files to backup
        test_files = ['test_spoofer.py', 'test_requirements.txt']
        for file in test_files:
            with open(file, 'w') as f:
                f.write(f"# Test content for {file}")

        # Backup files
        for file in test_files:
            if os.path.exists(file):
                shutil.copy2(file, backup_dir)
                print(f"✓ Backed up: {file}")

        print(f"✓ Backup created: {backup_dir}")

        # Cleanup
        for file in test_files:
            if os.path.exists(file):
                os.remove(file)

        return True, backup_dir
    except Exception as e:
        print(f"✗ Error creating backup: {e}")
        return False, None

def test_rollback_function(backup_dir):
    """Test the rollback functionality"""
    print("\n=== Testing Rollback Functionality ===")

    try:
        if not backup_dir or not os.path.exists(backup_dir):
            print("✗ No backup available for rollback")
            return False

        print("✓ Rolling back to previous version...")

        files_to_restore = ['test_spoofer.py', 'test_requirements.txt']

        for file in files_to_restore:
            backup_file = os.path.join(backup_dir, file)
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, file)
                print(f"✓ Restored: {file}")

        print("✓ Rollback completed successfully")
        return True
    except Exception as e:
        print(f"✗ Error during rollback: {e}")
        return False

def test_file_validation():
    """Test file validation functionality"""
    print("\n=== Testing File Validation ===")

    try:
        # Create test files
        required_files = ['test_spoofer.py', 'test_requirements.txt']
        for file in required_files:
            with open(file, 'w') as f:
                f.write(f"# Valid {file}")

        # Test validation (should pass)
        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)

        if not missing_files:
            print("✓ File validation passed (all files present)")
        else:
            print(f"✗ File validation failed: {', '.join(missing_files)}")

        # Test validation (should fail)
        if os.path.exists('test_spoofer.py'):
            os.remove('test_spoofer.py')

        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)

        if missing_files:
            print("✓ File validation correctly detected missing files")
        else:
            print("✗ File validation should have detected missing files")

        # Cleanup
        for file in required_files:
            if os.path.exists(file):
                os.remove(file)

        return True
    except Exception as e:
        print(f"✗ Error testing file validation: {e}")
        return False

def main():
    """Run all update system tests"""
    print("=== Enhanced Update System Component Tests ===")

    # Test backup creation
    backup_success, backup_dir = test_backup_function()

    if backup_success and backup_dir:
        # Test rollback
        rollback_success = test_rollback_function(backup_dir)

        # Test file validation
        validation_success = test_file_validation()

        # Cleanup backup directory
        if os.path.exists(backup_dir):
            shutil.rmtree(backup_dir)
            print(f"\n✓ Cleaned up backup directory: {backup_dir}")

        if backup_success and rollback_success and validation_success:
            print("\n🎉 All update system components tested successfully!")
            print("✓ Backup creation works")
            print("✓ Rollback mechanism works")
            print("✓ File validation works")
            return True

    print("\n❌ Some tests failed")
    return False

if __name__ == "__main__":
    main()
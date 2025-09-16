import os
import time
from typing import Dict

def get_directory_size(path: str) -> float:
    """Calculates the total size of a directory in megabytes (MB)."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size / (1024 * 1024) # Convert bytes to MB

def clear_old_files(folder_path: str, max_age_hours: int = 24) -> int:
    """
    Deletes files in a specified folder that are older than max_age_hours.

    Args:
        folder_path: The path to the folder to clean.
        max_age_hours: The maximum age of files in hours to keep.

    Returns:
        The number of files deleted.
    """
    deleted_files_count = 0
    if not os.path.isdir(folder_path):
        return 0

    now = time.time()
    cutoff = now - (max_age_hours * 60 * 60)

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) and os.path.getmtime(file_path) < cutoff:
                os.remove(file_path)
                deleted_files_count += 1
                print(f"Deleted old file: {file_path}")
        except OSError as e:
            print(f"Error deleting file {file_path}: {e}")
    
    return deleted_files_count

def run_cleanup_if_needed():
    """
    Checks storage usage and runs cleanup if it exceeds the configured limit.
    This function is designed to be called by a scheduler.
    """
    print("Running scheduled cleanup check...")
    
    # Get configuration from environment variables with sensible defaults
    max_storage_mb = int(os.getenv("MAX_STORAGE_MB", 500)) # Default to 500 MB
    cleanup_age_hours = 24 # Files older than 24 hours are eligible for deletion

    uploads_path = "static/uploads"
    edited_path = "static/edited_images"

    # Ensure directories exist
    os.makedirs(uploads_path, exist_ok=True)
    os.makedirs(edited_path, exist_ok=True)

    # Calculate current size
    uploads_size = get_directory_size(uploads_path)
    edited_size = get_directory_size(edited_path)
    total_size = uploads_size + edited_size

    print(f"Current storage usage: {total_size:.2f} MB / {max_storage_mb} MB")

    if total_size > max_storage_mb:
        print(f"Storage limit ({max_storage_mb} MB) exceeded. Starting cleanup...")
        
        uploads_cleared = clear_old_files(uploads_path, cleanup_age_hours)
        edited_cleared = clear_old_files(edited_path, cleanup_age_hours)
        
        print(f"Cleanup finished. Deleted {uploads_cleared} uploaded files and {edited_cleared} edited images.")
        
        new_size = get_directory_size(uploads_path) + get_directory_size(edited_path)
        print(f"New storage usage: {new_size:.2f} MB")
    else:
        print("Storage usage is within limits. No cleanup needed.")

if __name__ == '__main__':
    # This block allows for testing the cleanup service directly.
    # To run this test:
    # 1. Set MAX_STORAGE_MB in your .env file to a low number (e.g., 1)
    # 2. Add some files to static/uploads and static/edited_images
    # 3. Run `python cleanup_service.py`
    
    print("--- Testing Cleanup Service ---")
    # Make sure you have a .env file
    from dotenv import load_dotenv
    load_dotenv()
    run_cleanup_if_needed()

    print("--- Cleanup Service Test Completed ---")
#!/usr/bin/env python3
"""
Script to clean up ChromaDB data to resolve embedding function interface issues.
This script will delete all ChromaDB data and restart the application with a clean state.
"""

import os
import shutil
import sys
import subprocess
import time

def cleanup_chroma_db():
    """Clean up ChromaDB data."""
    print("🧹 Cleaning up ChromaDB data...")
    
    # Path to ChromaDB data
    chroma_db_path = os.path.join(os.getcwd(), "persistent_state", "chroma_db")
    
    if os.path.exists(chroma_db_path):
        print(f"📂 Found ChromaDB data at: {chroma_db_path}")
        
        # List contents before deletion
        print("📋 Current contents:")
        for item in os.listdir(chroma_db_path):
            item_path = os.path.join(chroma_db_path, item)
            if os.path.isdir(item_path):
                print(f"  📁 Directory: {item}")
            else:
                size_mb = os.path.getsize(item_path) / (1024 * 1024)
                print(f"  📄 File: {item} ({size_mb:.2f} MB)")
        
        # Confirm deletion
        confirm = input("⚠️ Are you sure you want to delete all ChromaDB data? (y/n): ")
        if confirm.lower() != 'y':
            print("❌ Cleanup cancelled.")
            return False
        
        # Delete the directory
        try:
            # First try to remove just the contents
            for item in os.listdir(chroma_db_path):
                item_path = os.path.join(chroma_db_path, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    print(f"🗑️ Deleted directory: {item}")
                else:
                    os.remove(item_path)
                    print(f"🗑️ Deleted file: {item}")
            
            print("✅ Successfully cleaned up ChromaDB data.")
            return True
        except Exception as e:
            print(f"❌ Error cleaning up ChromaDB data: {str(e)}")
            
            # If that fails, try to remove the entire directory and recreate it
            try:
                shutil.rmtree(chroma_db_path)
                os.makedirs(chroma_db_path, exist_ok=True)
                print("✅ Successfully removed and recreated ChromaDB directory.")
                return True
            except Exception as e2:
                print(f"❌ Error removing ChromaDB directory: {str(e2)}")
                return False
    else:
        print(f"⚠️ ChromaDB data directory not found at: {chroma_db_path}")
        
        # Create the directory
        try:
            os.makedirs(chroma_db_path, exist_ok=True)
            print(f"✅ Created ChromaDB directory at: {chroma_db_path}")
            return True
        except Exception as e:
            print(f"❌ Error creating ChromaDB directory: {str(e)}")
            return False

def restart_application():
    """Restart the application."""
    print("🔄 Restarting the application...")
    
    try:
        # Start the application in a new process
        subprocess.Popen(["python", "-m", "src.server.app"])
        print("✅ Application restarted successfully.")
        return True
    except Exception as e:
        print(f"❌ Error restarting application: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧹 ChromaDB Cleanup Utility 🧹")
    print("This script will delete all ChromaDB data and restart the application with a clean state.")
    print("This is useful when there are issues with the embedding function interface.")
    
    if cleanup_chroma_db():
        print("✅ ChromaDB data cleaned up successfully.")
        
        # Ask if user wants to restart the application
        restart = input("🔄 Do you want to restart the application now? (y/n): ")
        if restart.lower() == 'y':
            restart_application()
        else:
            print("ℹ️ You can restart the application manually with: python -m src.server.app")
    else:
        print("❌ Failed to clean up ChromaDB data.") 
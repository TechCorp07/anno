#!/usr/bin/env python3
"""
Image Renaming Script for Cognitive Assessment System
Renames: Q001_CT_LEFT_PULMONARY_ARTERY_Q.png → Q001.png
Range: Q001 to Q229
"""

import os
import re
from pathlib import Path


def rename_images(folder_path, dry_run=True):
    """
    Rename image files from Q###_*_Q.ext to Q###.ext
    
    Args:
        folder_path: Path to folder containing images
        dry_run: If True, only shows what would be renamed (default: True)
    
    Returns:
        Tuple of (success_count, error_count)
    """
    # Pattern to match: Q###_anything.ext
    pattern = re.compile(r'^(Q\d{3})_.+\.(png|jpg|jpeg|gif|bmp|dcm)$', re.IGNORECASE)
    
    folder = Path(folder_path)
    if not folder.exists():
        print(f"❌ Folder not found: {folder_path}")
        return 0, 0
    
    if not folder.is_dir():
        print(f"❌ Path is not a directory: {folder_path}")
        return 0, 0
    
    # Find all matching files
    files_to_rename = []
    for file in folder.iterdir():
        if file.is_file():
            match = pattern.match(file.name)
            if match:
                q_number = match.group(1)  # e.g., "Q001"
                extension = match.group(2)  # e.g., "png"
                new_name = f"{q_number}.{extension}"
                files_to_rename.append((file, new_name))
    
    if not files_to_rename:
        print("⚠️  No files found matching pattern Q###_*.ext")
        return 0, 0
    
    # Display mode
    mode = "DRY RUN" if dry_run else "RENAMING"
    print(f"\n{'='*60}")
    print(f"  {mode} MODE - Found {len(files_to_rename)} files")
    print(f"{'='*60}\n")
    
    success_count = 0
    error_count = 0
    
    for old_path, new_name in files_to_rename:
        new_path = old_path.parent / new_name
        
        # Check if target already exists
        if new_path.exists() and new_path != old_path:
            print(f"⚠️  SKIP: {old_path.name} → {new_name} (target exists)")
            error_count += 1
            continue
        
        if dry_run:
            print(f"✓ WOULD RENAME: {old_path.name} → {new_name}")
            success_count += 1
        else:
            try:
                old_path.rename(new_path)
                print(f"✓ RENAMED: {old_path.name} → {new_name}")
                success_count += 1
            except Exception as e:
                print(f"❌ ERROR: {old_path.name} → {str(e)}")
                error_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY: {success_count} successful, {error_count} errors")
    print(f"{'='*60}\n")
    
    if dry_run:
        print("ℹ️  This was a DRY RUN. No files were renamed.")
        print("   Run with dry_run=False to actually rename files.\n")
    
    return success_count, error_count


def main():
    """Main execution with user prompts"""
    print("=" * 60)
    print("  COGNITIVE ASSESSMENT - IMAGE RENAMING TOOL")
    print("=" * 60)
    print("\nConverts: Q001_CT_LEFT_PULMONARY_ARTERY_Q.png → Q001.png")
    print("Range: Q001 to Q229\n")
    
    # Get folder path
    folder_path = input("Enter folder path (or press Enter for current directory): ").strip()
    if not folder_path:
        folder_path = "."
    
    # First, do a dry run
    print("\n🔍 Running dry run first...\n")
    success, errors = rename_images(folder_path, dry_run=True)
    
    if success == 0:
        print("\n❌ No files to rename. Exiting.")
        return
    
    # Ask for confirmation
    print("\n" + "=" * 60)
    response = input("Proceed with actual renaming? (yes/no): ").strip().lower()
    
    if response in ['yes', 'y']:
        print("\n🚀 Starting actual rename...\n")
        rename_images(folder_path, dry_run=False)
        print("✅ Renaming complete!\n")
    else:
        print("\n❌ Cancelled by user.\n")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Migration script to organize processed content into separate folders.

This script moves existing .questions.json and .summary.json files from
processed_content/ into organized subdirectories:
- processed_content/questions/
- processed_content/summaries/
"""

import os
import shutil
from pathlib import Path


def migrate_processed_content(base_dir: str = "processed_content"):
    """
    Migrate processed content files to organized subdirectories.
    
    Args:
        base_dir: Base directory containing processed content files
    """
    base_path = Path(base_dir)
    
    if not base_path.exists():
        print(f"❌ Directory {base_dir} does not exist")
        return False
    
    # Create subdirectories
    questions_dir = base_path / "questions"
    summaries_dir = base_path / "summaries"
    
    questions_dir.mkdir(exist_ok=True)
    summaries_dir.mkdir(exist_ok=True)
    
    print(f"📁 Created directories:")
    print(f"   - {questions_dir}")
    print(f"   - {summaries_dir}")
    
    # Find files to migrate
    questions_files = list(base_path.glob("*.questions.json"))
    summary_files = list(base_path.glob("*.summary.json"))
    
    # Move questions files
    moved_questions = 0
    for file_path in questions_files:
        destination = questions_dir / file_path.name
        if not destination.exists():
            shutil.move(str(file_path), str(destination))
            moved_questions += 1
            print(f"   ✅ Moved {file_path.name} → questions/")
        else:
            print(f"   ⚠️  {file_path.name} already exists in questions/")
    
    # Move summary files
    moved_summaries = 0
    for file_path in summary_files:
        destination = summaries_dir / file_path.name
        if not destination.exists():
            shutil.move(str(file_path), str(destination))
            moved_summaries += 1
            print(f"   ✅ Moved {file_path.name} → summaries/")
        else:
            print(f"   ⚠️  {file_path.name} already exists in summaries/")
    
    print(f"\n📊 Migration Summary:")
    print(f"   Questions files moved: {moved_questions}")
    print(f"   Summary files moved: {moved_summaries}")
    
    # Show final structure
    print(f"\n📂 Final structure:")
    questions_count = len(list(questions_dir.glob("*.questions.json")))
    summaries_count = len(list(summaries_dir.glob("*.summary.json")))
    
    print(f"   {base_dir}/")
    print(f"   ├── questions/ ({questions_count} files)")
    print(f"   └── summaries/ ({summaries_count} files)")
    
    return True


def verify_structure(base_dir: str = "processed_content"):
    """
    Verify the processed content directory structure.
    
    Args:
        base_dir: Base directory to verify
    """
    base_path = Path(base_dir)
    
    if not base_path.exists():
        print(f"❌ Directory {base_dir} does not exist")
        return False
    
    questions_dir = base_path / "questions"
    summaries_dir = base_path / "summaries"
    
    print(f"🔍 Verifying structure of {base_dir}/")
    
    # Check questions directory
    if questions_dir.exists():
        questions_files = list(questions_dir.glob("*.questions.json"))
        print(f"   ✅ questions/ directory exists ({len(questions_files)} files)")
        for file_path in questions_files[:3]:  # Show first 3 files
            print(f"      - {file_path.name}")
        if len(questions_files) > 3:
            print(f"      ... and {len(questions_files) - 3} more")
    else:
        print(f"   ❌ questions/ directory missing")
    
    # Check summaries directory
    if summaries_dir.exists():
        summary_files = list(summaries_dir.glob("*.summary.json"))
        print(f"   ✅ summaries/ directory exists ({len(summary_files)} files)")
        for file_path in summary_files[:3]:  # Show first 3 files
            print(f"      - {file_path.name}")
        if len(summary_files) > 3:
            print(f"      ... and {len(summary_files) - 3} more")
    else:
        print(f"   ❌ summaries/ directory missing")
    
    # Check for any remaining files in root
    remaining_questions = list(base_path.glob("*.questions.json"))
    remaining_summaries = list(base_path.glob("*.summary.json"))
    
    if remaining_questions or remaining_summaries:
        print(f"\n⚠️  Files still in root directory:")
        for file_path in remaining_questions + remaining_summaries:
            print(f"      - {file_path.name}")
        print(f"   Run migration again to move these files.")
    else:
        print(f"\n✅ All files properly organized!")
    
    return True


def main():
    """Main function to run migration and verification."""
    print("🚀 Processed Content Migration Tool")
    print("=" * 50)
    
    # Check current structure
    print("\n📋 Current structure:")
    verify_structure()
    
    # Ask user if they want to migrate
    print(f"\n❓ Do you want to migrate files to organized subdirectories? (y/n): ", end="")
    response = input().lower().strip()
    
    if response in ['y', 'yes']:
        print(f"\n🔄 Starting migration...")
        success = migrate_processed_content()
        
        if success:
            print(f"\n🎉 Migration completed successfully!")
            print(f"\n📋 Verifying new structure:")
            verify_structure()
            
            print(f"\n💡 Next steps:")
            print(f"   - New questions will be saved to processed_content/questions/")
            print(f"   - New summaries will be saved to processed_content/summaries/")
            print(f"   - Chrome extension should load files from questions/ folder")
        else:
            print(f"\n❌ Migration failed!")
    else:
        print(f"\n👍 Migration skipped. Current structure maintained.")


if __name__ == "__main__":
    main()

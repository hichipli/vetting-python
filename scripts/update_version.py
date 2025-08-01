#!/usr/bin/env python3
"""
Version management script for vetting-python package.
Updates version across all relevant files.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def update_version_in_file(file_path: Path, old_version: str, new_version: str) -> bool:
    """Update version in a specific file."""
    if not file_path.exists():
        print(f"Warning: {file_path} does not exist")
        return False
    
    content = file_path.read_text(encoding='utf-8')
    original_content = content
    
    if file_path.name == 'pyproject.toml':
        # Update version in pyproject.toml
        content = re.sub(
            r'version = "[^"]*"',
            f'version = "{new_version}"',
            content
        )
    elif file_path.name == '__init__.py':
        # Update __version__ in __init__.py
        content = re.sub(
            r'__version__ = "[^"]*"',
            f'__version__ = "{new_version}"',
            content
        )
    elif file_path.name == 'CHANGELOG.md':
        # Add new entry to changelog
        unreleased_pattern = r'## \[Unreleased\]'
        if re.search(unreleased_pattern, content):
            new_entry = f"""## [Unreleased]

### Added
- Preparation for next release

## [{new_version}] - {get_current_date()}

### Changed
- Version bump to {new_version}
"""
            content = re.sub(
                r'## \[Unreleased\]\s*\n',
                new_entry,
                content
            )
    
    if content != original_content:
        file_path.write_text(content, encoding='utf-8')
        print(f"Updated {file_path}")
        return True
    else:
        print(f"No changes needed in {file_path}")
        return False


def get_current_date() -> str:
    """Get current date in YYYY-MM-DD format."""
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%d')


def get_current_version() -> str:
    """Get current version from pyproject.toml."""
    pyproject_path = Path('pyproject.toml')
    if not pyproject_path.exists():
        print("Error: pyproject.toml not found")
        sys.exit(1)
    
    content = pyproject_path.read_text()
    version_match = re.search(r'version = "([^"]*)"', content)
    if not version_match:
        print("Error: Could not find version in pyproject.toml")
        sys.exit(1)
    
    return version_match.group(1)


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python update_version.py <new_version>")
        print(f"Current version: {get_current_version()}")
        sys.exit(1)
    
    new_version = sys.argv[1]
    old_version = get_current_version()
    
    if new_version == old_version:
        print(f"Version is already {new_version}")
        sys.exit(0)
    
    print(f"Updating version from {old_version} to {new_version}")
    
    # Files to update
    files_to_update = [
        Path('pyproject.toml'),
        Path('vetting_python/__init__.py'),
        Path('CHANGELOG.md'),
    ]
    
    updated_files = []
    for file_path in files_to_update:
        if update_version_in_file(file_path, old_version, new_version):
            updated_files.append(file_path)
    
    if updated_files:
        print(f"\nSuccessfully updated version to {new_version} in:")
        for file_path in updated_files:
            print(f"  - {file_path}")
        
        print(f"\nNext steps:")
        print(f"1. Review changes: git diff")
        print(f"2. Commit changes: git add -A && git commit -m 'Bump version to {new_version}'")
        print(f"3. Create tag: git tag v{new_version}")
        print(f"4. Push: git push && git push --tags")
        print(f"5. Create GitHub release or run workflow")
    else:
        print("No files were updated")


if __name__ == '__main__':
    main()
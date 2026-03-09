#!/usr/bin/env python3
"""
Validate that all files in the site directory are under Cloudflare's 25MB limit.
Run this before deployment to catch any oversized files.
"""

from pathlib import Path

MAX_SIZE_MB = 25
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

def check_directory(directory: Path) -> tuple[bool, list[tuple[Path, float]]]:
    """
    Check all files in directory for size violations.

    Returns:
        (all_valid, large_files) where large_files is a list of (path, size_mb)
    """
    large_files = []

    for file_path in directory.rglob('*'):
        if file_path.is_file():
            size = file_path.stat().st_size
            if size > MAX_SIZE_BYTES:
                size_mb = size / (1024 * 1024)
                large_files.append((file_path, size_mb))

    return len(large_files) == 0, large_files


def main():
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    site_dir = project_root / "site"

    if not site_dir.exists():
        print(f"❌ Error: {site_dir} does not exist")
        return 1

    print(f"Validating files in {site_dir}...")
    print(f"Maximum file size: {MAX_SIZE_MB}MB")
    print()

    all_valid, large_files = check_directory(site_dir)

    if all_valid:
        print("✅ All files are under 25MB - safe to deploy!")
        return 0
    else:
        print(f"❌ Found {len(large_files)} file(s) that exceed {MAX_SIZE_MB}MB:")
        print()
        for file_path, size_mb in sorted(large_files, key=lambda x: x[1], reverse=True):
            rel_path = file_path.relative_to(site_dir)
            print(f"  {rel_path}")
            print(f"    Size: {size_mb:.2f} MB")
        print()
        print("These files will cause deployment to fail on Cloudflare Pages.")
        print("Please remove them from the site directory or add them to .cfignore")
        return 1


if __name__ == "__main__":
    exit(main())

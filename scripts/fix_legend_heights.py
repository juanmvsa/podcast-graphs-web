#!/usr/bin/env python3
"""Fix the legend dot/line heights that were accidentally changed."""

import re
from pathlib import Path


def fix_html_file(file_path: Path) -> bool:
    """Fix legend heights in a single HTML file."""
    try:
        html = file_path.read_text(encoding="utf-8")

        # Fix legend dots that have wrong height
        # Pattern: width: 12px; height: 85vh (or similar)
        html = re.sub(
            r'(width:\s*12px;)\s*height:\s*85vh[^;]*;',
            r'\1 height: 12px;',
            html
        )

        # Fix legend dots that might have other wrong heights
        html = re.sub(
            r'(width:\s*12px;)\s*height:\s*\d+vh[^;]*;',
            r'\1 height: 12px;',
            html
        )

        # Fix legend lines with wrong heights
        html = re.sub(
            r'(width:\s*20px;)\s*height:\s*85vh[^;]*;',
            r'\1 height: 3px;',
            html
        )

        html = re.sub(
            r'(width:\s*20px;)\s*height:\s*\d+vh[^;]*;',
            r'\1 height: 3px;',
            html
        )

        # Also fix in the improved CSS section
        html = re.sub(
            r'(width:\s*18px)\s*!\s*important;\s*height:\s*18px',
            r'\1 !important;\n                height: 18px',
            html
        )

        file_path.write_text(html, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def main():
    """Fix all HTML graph files."""
    graphs_dir = Path("site/graphs")

    if not graphs_dir.exists():
        print(f"Directory {graphs_dir} not found!")
        return

    html_files = list(graphs_dir.rglob("*.html"))
    print(f"Found {len(html_files)} HTML files to fix")

    fixed = 0
    for file_path in html_files:
        if fix_html_file(file_path):
            fixed += 1
            if fixed % 1000 == 0:
                print(f"Fixed {fixed} files...")

    print(f"\n✓ Fixed {fixed}/{len(html_files)} files successfully!")


if __name__ == "__main__":
    main()

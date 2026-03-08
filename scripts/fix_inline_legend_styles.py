#!/usr/bin/env python3
"""Remove incorrect min-height/max-height from inline legend styles."""

import re
from pathlib import Path


def fix_html_file(file_path: Path) -> bool:
    """Fix inline legend styles in a single HTML file."""
    try:
        html = file_path.read_text(encoding="utf-8")

        # Remove min-height and max-height from legend dot inline styles
        # Pattern: width: 12px; height: 12px; min-height: XXX;
        html = re.sub(
            r'(width:\s*12px;\s*height:\s*12px;)\s*min-height:\s*[^;]+;',
            r'\1',
            html
        )

        html = re.sub(
            r'(width:\s*12px;\s*height:\s*12px;)\s*max-height:\s*[^;]+;',
            r'\1',
            html
        )

        # Remove from legend lines too
        html = re.sub(
            r'(width:\s*20px;\s*height:\s*3px;)\s*min-height:\s*[^;]+;',
            r'\1',
            html
        )

        html = re.sub(
            r'(width:\s*20px;\s*height:\s*3px;)\s*max-height:\s*[^;]+;',
            r'\1',
            html
        )

        # Also handle cases where order might be different
        html = re.sub(
            r'(display:\s*inline-block;\s*width:\s*12px;\s*height:\s*12px;)\s*min-height:\s*[^;]+;',
            r'\1',
            html
        )

        html = re.sub(
            r'(display:\s*inline-block;\s*width:\s*12px;\s*height:\s*12px;)\s*max-height:\s*[^;]+;',
            r'\1',
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

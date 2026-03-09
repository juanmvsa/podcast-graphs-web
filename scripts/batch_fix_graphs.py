#!/usr/bin/env python3
"""Batch fix accessibility issues in existing graph HTML files."""

import re
from pathlib import Path

GRAPHS_DIR = Path(__file__).resolve().parent.parent / "graphs"


def fix_file(filepath: Path) -> dict:
    """Apply all fixes to a single graph HTML file. Returns dict of fix counts."""
    content = filepath.read_text(encoding="utf-8")
    original = content
    fixes = {}

    # 1. Fix progress bar width: 100% -> 0% (scoped to .loading-progress-bar block)
    new_content = re.sub(
        r"(\.loading-progress-bar\s*\{[^}]*?)width:\s*100%",
        r"\1width: 0%",
        content,
    )
    if new_content != content:
        fixes["progress_bar"] = True
        content = new_content

    # 2. Fix .toggle-header: remove duplicate display: inline-block (keep display: none)
    # The pattern has "display: none;" ... then later "display: inline-block;"
    # We need to remove the second display: inline-block line within .toggle-header
    new_content = re.sub(
        r"(\.toggle-header\s*\{[^}]*?display:\s*none;[^}]*?)display:\s*inline-block;\s*\n",
        r"\1",
        content,
    )
    if new_content != content:
        fixes["toggle_display"] = True
        content = new_content

    # 2b. Add border: none; font-family: inherit; to .toggle-header
    if "border: none;\n            font-family: inherit;" not in content:
        new_content = re.sub(
            r"(\.toggle-header\s*\{[^}]*?)(transition:\s*all\s*0\.2s\s*ease;)",
            r"\1\2\n            border: none;\n            font-family: inherit;",
            content,
        )
        if new_content != content:
            fixes["toggle_button_reset"] = True
            content = new_content

    # 3. Color contrast: #9e9e9e -> #b0b0b0
    new_content = content.replace("#9e9e9e", "#b0b0b0")
    if new_content != content:
        fixes["color_contrast"] = True
        content = new_content

    # 4. Convert <span class="toggle-header" onclick="toggleDetails()"> to <button>
    old_toggle = '<span class="toggle-header" onclick="toggleDetails()">'
    new_toggle = '<button class="toggle-header" aria-expanded="false" aria-controls="headerDetails" onclick="toggleDetails()">'
    if old_toggle in content:
        content = content.replace(old_toggle, new_toggle)
        # Also fix the closing tag
        # The closing </span> right after the toggle text
        # Pattern: "▼ Show Details\n        </span>"
        content = content.replace(
            "▼ Show Details\n        </span>",
            "▼ Show Details\n        </button>",
        )
        fixes["toggle_to_button"] = True

    # 5. Add aria-label to entity search input
    old_search = 'id="entitySearch"\n            placeholder='
    new_search = 'id="entitySearch"\n            placeholder='
    # More reliable: target the input by its id
    if 'aria-label="Search entities by name"' not in content:
        content = content.replace(
            'id="entitySearch"',
            'id="entitySearch"\n            aria-label="Search entities by name"',
        )
        fixes["search_aria"] = True

    # 6. Add id="headerDetails" to header-details div
    if 'id="headerDetails"' not in content:
        content = content.replace(
            '<div class="header-details">',
            '<div class="header-details" id="headerDetails">',
        )
        fixes["header_details_id"] = True

    # 7. Add color names to legend items and aria-hidden on swatches
    legend_replacements = [
        (
            'style="background: #4FC3F7;"></span>\n                        <span>Person</span>',
            'style="background: #4FC3F7;" aria-hidden="true"></span>\n                        <span>Person (blue)</span>',
        ),
        (
            'style="background: #FF8A65;"></span>\n                        <span>Place</span>',
            'style="background: #FF8A65;" aria-hidden="true"></span>\n                        <span>Place (orange)</span>',
        ),
        (
            'style="background: #66BB6A;"></span>\n                        <span>😊 Positive</span>',
            'style="background: #66BB6A;" aria-hidden="true"></span>\n                        <span>😊 Positive (green)</span>',
        ),
        (
            'style="background: #EF5350;"></span>\n                        <span>😞 Negative</span>',
            'style="background: #EF5350;" aria-hidden="true"></span>\n                        <span>😞 Negative (red)</span>',
        ),
        (
            'style="background: #90A4AE;"></span>\n                        <span>😐 Neutral</span>',
            'style="background: #90A4AE;" aria-hidden="true"></span>\n                        <span>😐 Neutral (gray)</span>',
        ),
    ]
    for old, new in legend_replacements:
        if old in content:
            content = content.replace(old, new)
            fixes["legend_colors"] = True

    # 8. Update toggleDetails() JS to manage aria-expanded
    old_toggle_js = """toggle.textContent = details.classList.contains('expanded')
                ? '▲ Hide Details'
                : '▼ Show Details';"""
    new_toggle_js = """var isExpanded = details.classList.contains('expanded');
            toggle.textContent = isExpanded
                ? '▲ Hide Details'
                : '▼ Show Details';
            toggle.setAttribute('aria-expanded', String(isExpanded));"""
    if old_toggle_js in content:
        content = content.replace(old_toggle_js, new_toggle_js)
        fixes["toggle_aria_js"] = True

    # 9. Add focus-visible CSS (before mobile touch enhancements)
    focus_css = """        /* === Focus Styles === */
        .toggle-header:focus-visible,
        .control-button:focus-visible,
        .entity-search:focus-visible,
        .breadcrumb-nav a:focus-visible {
            outline: 2px solid #4FC3F7;
            outline-offset: 2px;
        }

"""
    if ":focus-visible" not in content and "/* === Mobile Touch Enhancements === */" in content:
        content = content.replace(
            "        /* === Mobile Touch Enhancements === */",
            focus_css + "        /* === Mobile Touch Enhancements === */",
        )
        fixes["focus_visible"] = True

    # 10. Fix mobile graph height
    old_height = "height: calc(100vh - 80px) !important;"
    new_height = "height: calc(100vh - 200px) !important;\n                height: calc(100dvh - 200px) !important;"
    if old_height in content:
        content = content.replace(old_height, new_height)
        fixes["mobile_height"] = True

    if content != original:
        filepath.write_text(content, encoding="utf-8")

    return fixes


def main():
    all_html = list(GRAPHS_DIR.rglob("*.html"))
    print(f"Found {len(all_html)} HTML files in {GRAPHS_DIR}")

    total_fixes = {}
    files_modified = 0

    for filepath in sorted(all_html):
        fixes = fix_file(filepath)
        if fixes:
            files_modified += 1
            rel = filepath.relative_to(GRAPHS_DIR)
            print(f"  Fixed {rel}: {', '.join(fixes.keys())}")
            for key in fixes:
                total_fixes[key] = total_fixes.get(key, 0) + 1

    print(f"\nDone! Modified {files_modified}/{len(all_html)} files")
    print("Fix summary:")
    for key, count in sorted(total_fixes.items()):
        print(f"  {key}: {count} files")


if __name__ == "__main__":
    main()

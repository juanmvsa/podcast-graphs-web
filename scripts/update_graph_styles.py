#!/usr/bin/env python3
"""Update existing graph HTML files with improved CSS for mobile responsiveness."""

import re
from pathlib import Path


def get_improved_css() -> str:
    """Return the improved CSS styles."""
    return """
        /* === Reset and Base === */
        * {
            box-sizing: border-box;
        }

        html, body {
            margin: 0;
            padding: 0;
            width: 100%;
            overflow-x: hidden;
        }

        body {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }

        /* Improved info boxes with better visibility */
        .info-box, [style*="background: rgba(255,255,255,0.05)"] {
            background: rgba(255,255,255,0.08) !important;
            border: 1px solid rgba(255,255,255,0.15) !important;
            border-radius: 10px !important;
            padding: 16px 20px !important;
        }

        /* Improved legend items - larger and more readable */
        [style*="width: 12px; height: 12px"] {
            width: 18px !important;
            height: 18px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
        }

        [style*="width: 20px; height: 3px"] {
            width: 30px !important;
            height: 5px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
        }

        /* Better text sizing */
        [style*="font-size: 0.75em"] {
            font-size: 0.9em !important;
            color: #4FC3F7 !important;
            font-weight: 700 !important;
        }

        [style*="font-size: 0.85em; line-height: 1.8"] {
            font-size: 1rem !important;
            line-height: 2.2 !important;
            color: #e8e8e8 !important;
        }

        /* Mobile Responsive Improvements */
        @media (max-width: 768px) {
            #graph-header {
                padding: 20px 16px !important;
            }

            #graph-header h1 {
                font-size: 1.4em !important;
                line-height: 1.3 !important;
            }

            #graph-header [style*="display: flex"] {
                flex-direction: column !important;
                gap: 12px !important;
            }

            /* Make info boxes full width on mobile */
            [style*="min-width: 220px"], [style*="min-width: 180px"] {
                min-width: 100% !important;
                width: 100% !important;
            }

            /* Larger legend items on mobile */
            [style*="width: 12px; height: 12px"] {
                width: 20px !important;
                height: 20px !important;
            }

            [style*="width: 20px; height: 3px"] {
                width: 35px !important;
                height: 6px !important;
            }

            /* Increase font sizes on mobile */
            [style*="font-size: 0.75em"] {
                font-size: 1em !important;
            }

            [style*="font-size: 0.85em; line-height: 1.8"] {
                font-size: 1.1rem !important;
                line-height: 2.5 !important;
            }

            /* Make graph take full viewport height */
            #mynetwork {
                height: calc(100vh - 100px) !important;
                min-height: 500px !important;
            }
        }

        /* Tablet optimization */
        @media (min-width: 769px) and (max-width: 1024px) {
            [style*="width: 12px; height: 12px"] {
                width: 16px !important;
                height: 16px !important;
            }

            [style*="width: 20px; height: 3px"] {
                width: 26px !important;
                height: 4px !important;
            }
        }

        /* Improve touch targets */
        @media (hover: none) and (pointer: coarse) {
            * {
                -webkit-tap-highlight-color: transparent;
            }
        }
    """


def update_html_file(file_path: Path) -> bool:
    """Update a single HTML file with improved CSS."""
    try:
        html = file_path.read_text(encoding="utf-8")

        # Add viewport meta tag if not present
        if '<meta name="viewport"' not in html:
            viewport_meta = '    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">'
            html = html.replace("<head>", f"<head>\n{viewport_meta}", 1)

        # Add improved CSS before closing </style> tag
        improved_css = get_improved_css()
        if improved_css not in html:
            html = html.replace("</style>", f"{improved_css}\n        </style>", 1)

        # Update network container height to be more responsive
        # Only target the #mynetwork rule, not all height values
        html = re.sub(
            r'(#mynetwork\s*\{[^}]*?)height:\s*\d+px;',
            r'\1height: 85vh; min-height: 450px;',
            html
        )

        # Write updated HTML
        file_path.write_text(html, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False


def main():
    """Update all HTML graph files in site/graphs/."""
    graphs_dir = Path("site/graphs")

    if not graphs_dir.exists():
        print(f"Directory {graphs_dir} not found!")
        return

    html_files = list(graphs_dir.rglob("*.html"))
    print(f"Found {len(html_files)} HTML files to update")

    updated = 0
    for file_path in html_files:
        if update_html_file(file_path):
            updated += 1
            print(f"✓ Updated: {file_path.relative_to(graphs_dir)}")

    print(f"\nUpdated {updated}/{len(html_files)} files successfully!")


if __name__ == "__main__":
    main()

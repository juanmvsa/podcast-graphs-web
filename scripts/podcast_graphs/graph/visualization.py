"""Interactive graph visualization using pyvis.

Generates self-contained HTML files with custom styles, scripts,
and navigation for entity relationship graphs.
"""

from __future__ import annotations

import re
from pathlib import Path

import networkx as nx
from pyvis.network import Network

from podcast_graphs.constants import (
    MAX_CONTEXT_DISPLAY_TEXT,
    MAX_CONTEXTS_DISPLAY,
    PERSON_COLOR,
    PLACE_COLOR,
    SENTIMENT_EMOJI,
    SENTIMENT_NEGATIVE_COLOR,
    SENTIMENT_NEUTRAL_COLOR,
    SENTIMENT_POSITIVE_COLOR,
    TEMPORAL_LABELS,
    TITLE_MINOR_WORDS,
)


def humanize_title(snake_text: str) -> str:
    """Convert a snake_case string to a human-readable title.

    Applies title-case rules: capitalizes major words, lowercases minor words
    (articles, conjunctions, prepositions) unless first or last.
    """
    words = snake_text.replace("_", " ").split()
    if not words:
        return snake_text

    result: list[str] = []
    for i, word in enumerate(words):
        if i == 0 or i == len(words) - 1 or word.lower() not in TITLE_MINOR_WORDS:
            result.append(word.capitalize())
        else:
            result.append(word.lower())
    return " ".join(result)


def _dominant_sentiment(contexts: list[dict[str, object]]) -> str:
    """Determine the dominant sentiment from a list of edge contexts."""
    sentiments = [
        ctx.get("sentiment", {}).get("label", "NEUTRAL")
        for ctx in contexts
        if ctx.get("sentiment")
    ]
    if not sentiments:
        return "NEUTRAL"
    pos = sentiments.count("POSITIVE")
    neg = sentiments.count("NEGATIVE")
    if pos > neg:
        return "POSITIVE"
    elif neg > pos:
        return "NEGATIVE"
    return "NEUTRAL"



def _build_enhanced_styles() -> str:
    """build enhanced CSS styles for improved UI/UX."""
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

        /* === Breadcrumb Navigation === */
        .breadcrumb-nav {
            background: rgba(26, 26, 46, 0.95);
            padding: 12px 32px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            font-size: 0.9rem;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }

        .breadcrumb-nav a {
            color: #4FC3F7;
            text-decoration: none;
            transition: color 0.2s ease;
        }

        .breadcrumb-nav a:hover {
            color: #ffffff;
        }

        .breadcrumb-separator {
            color: #b0b0b0;
            margin: 0 8px;
        }

        .breadcrumb-current {
            color: #e0e0e0;
        }

        /* === Graph Header === */
        #graph-header {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            padding: 24px 32px 20px;
            border-bottom: 1px solid #333;
        }

        #graph-header h1 {
            margin: 0 0 4px 0;
            font-size: 1.6em;
            font-weight: 600;
            color: #ffffff;
            letter-spacing: -0.02em;
        }

        #graph-header .subtitle {
            margin: 0 0 16px 0;
            font-size: 0.95em;
            color: #b0b0b0;
        }

        .toggle-header {
            display: none;
            cursor: pointer;
            color: #4FC3F7;
            font-size: 1rem;
            margin-top: 8px;
            user-select: none;
            padding: 8px 12px;
            background: rgba(79, 195, 247, 0.15);
            border-radius: 6px;
            transition: all 0.2s ease;
            border: none;
            font-family: inherit;
        }

        .toggle-header:hover {
            background: rgba(79, 195, 247, 0.25);
        }

        .toggle-header:active {
            transform: scale(0.98);
        }

        .header-details {
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
            align-items: stretch;
            margin-top: 16px;
        }

        .info-box {
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 10px;
            padding: 16px 20px;
            min-width: 200px;
            flex: 1 1 auto;
        }

        .info-box-title {
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: #4FC3F7;
            margin-bottom: 12px;
            font-weight: 700;
        }

        .legend-items, .stats-items, .controls-items {
            font-size: 0.95em;
            line-height: 2;
            color: #e8e8e8;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 4px 0;
        }

        .legend-dot {
            display: inline-block;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            flex-shrink: 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }

        .legend-line {
            display: inline-block;
            width: 28px;
            height: 4px;
            border-radius: 2px;
            flex-shrink: 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }

        .stat-number {
            font-weight: 700;
            font-size: 1.1em;
        }

        .controls-items div {
            color: #d0d0d0;
        }

        /* === Entity Search === */
        .entity-search-container {
            margin: 16px 32px;
        }

        .entity-search {
            width: 100%;
            max-width: 600px;
            background: rgba(255,255,255,0.08);
            border: 2px solid rgba(255,255,255,0.2);
            color: #ffffff;
            padding: 12px 18px;
            border-radius: 10px;
            font-size: 1rem;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            transition: all 0.2s ease;
        }

        .entity-search:focus {
            outline: none;
            border-color: #4FC3F7;
            background: rgba(255,255,255,0.12);
            box-shadow: 0 0 0 3px rgba(79, 195, 247, 0.1);
        }

        .entity-search::placeholder {
            color: #a0a0a0;
        }

        /* === Graph Controls === */
        .graph-controls {
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 10px;
            padding: 14px 18px;
            margin: 0 32px 16px;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            align-items: center;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }

        .control-group {
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }

        .control-label {
            color: #b0b0b0;
            font-size: 0.9rem;
            margin-right: 6px;
            font-weight: 500;
        }

        .control-button {
            background: rgba(79, 195, 247, 0.15);
            border: 1px solid rgba(79, 195, 247, 0.4);
            color: #4FC3F7;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.2s ease;
            font-family: inherit;
            white-space: nowrap;
        }

        .control-button:hover {
            background: rgba(79, 195, 247, 0.25);
            border-color: rgba(79, 195, 247, 0.6);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        .control-button:active {
            transform: translateY(0);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        /* === Loading Overlay === */
        .graph-loading {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(30, 30, 30, 0.95);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            transition: opacity 0.3s ease;
        }

        .graph-loading.hidden {
            opacity: 0;
            pointer-events: none;
        }

        .loading-spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(79, 195, 247, 0.2);
            border-top-color: #4FC3F7;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .loading-text {
            color: #4FC3F7;
            margin-top: 16px;
            font-size: 0.9rem;
        }

        .loading-progress {
            width: 200px;
            height: 4px;
            background: rgba(79, 195, 247, 0.2);
            border-radius: 2px;
            margin-top: 12px;
            overflow: hidden;
        }

        .loading-progress-bar {
            height: 100%;
            background: #4FC3F7;
            width: 0%;
            transition: width 0.3s ease;
        }

        /* === Mobile Responsive === */
        @media (max-width: 768px) {
            .breadcrumb-nav {
                padding: 12px 16px;
                font-size: 0.9rem;
                overflow-x: auto;
                white-space: nowrap;
            }

            #graph-header {
                padding: 20px 16px;
            }

            #graph-header h1 {
                font-size: 1.35em;
                line-height: 1.3;
            }

            #graph-header .subtitle {
                font-size: 0.9em;
            }

            .toggle-header {
                display: inline-block;
                width: 100%;
                text-align: center;
                margin-top: 12px;
                padding: 12px;
                font-size: 1rem;
            }

            .header-details {
                display: none;
                margin-top: 16px;
                gap: 12px;
            }

            .header-details.expanded {
                display: flex;
            }

            .info-box {
                min-width: 100%;
                width: 100%;
                padding: 16px;
                flex: 1 1 100%;
            }

            .info-box-title {
                font-size: 0.9em;
                margin-bottom: 12px;
            }

            .legend-items, .stats-items, .controls-items {
                font-size: 1rem;
                line-height: 2.2;
            }

            .legend-item {
                gap: 14px;
                padding: 6px 0;
            }

            .legend-dot {
                width: 18px;
                height: 18px;
            }

            .legend-line {
                width: 32px;
                height: 5px;
            }

            .stat-number {
                font-size: 1.2em;
            }

            .entity-search-container {
                margin: 16px;
            }

            .graph-controls {
                margin: 0 16px 16px;
                padding: 12px;
                gap: 12px;
            }

            .control-group {
                width: 100%;
                justify-content: center;
            }

            #mynetwork {
                height: calc(100vh - 200px) !important;
                height: calc(100dvh - 200px) !important;
                min-height: 400px !important;
            }

            /* Make graph container take full width */
            .card {
                margin: 0 !important;
                border-radius: 0 !important;
            }
        }

        /* === Tablet Responsive === */
        @media (min-width: 769px) and (max-width: 1024px) {
            .header-details {
                gap: 20px;
            }

            .info-box {
                min-width: 220px;
                flex: 1 1 calc(50% - 10px);
            }

            .legend-items, .stats-items, .controls-items {
                font-size: 0.9em;
            }

            .legend-dot {
                width: 14px;
                height: 14px;
            }

            .legend-line {
                width: 24px;
            }
        }

        /* === Large Screen Optimization === */
        @media (min-width: 1440px) {
            #graph-header {
                padding: 28px 48px 24px;
            }

            .breadcrumb-nav {
                padding: 14px 48px;
            }

            .header-details {
                gap: 24px;
            }

            .info-box {
                padding: 18px 22px;
            }

            .entity-search-container {
                margin: 20px 48px;
            }

            .graph-controls {
                margin: 0 48px 20px;
            }
        }

        /* === Sentiment Distribution Chart === */
        .sentiment-chart {
            font-size: 0.95em;
        }

        .sentiment-bar-container {
            display: flex;
            width: 100%;
            height: 28px;
            border-radius: 6px;
            overflow: hidden;
            margin-bottom: 14px;
            background: rgba(0,0,0,0.3);
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
        }

        .sentiment-bar {
            height: 100%;
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
        }

        .sentiment-bar:hover {
            opacity: 0.85;
            transform: scaleY(1.1);
        }

        .sentiment-legend {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .sentiment-stat {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.95em;
            padding: 4px 0;
        }

        .sentiment-stat span {
            font-weight: 700;
        }

        /* === Focus Styles === */
        .toggle-header:focus-visible,
        .control-button:focus-visible,
        .entity-search:focus-visible,
        .breadcrumb-nav a:focus-visible {
            outline: 2px solid #4FC3F7;
            outline-offset: 2px;
        }

        /* === Mobile Touch Enhancements === */
        @media (hover: none) and (pointer: coarse) {
            /* Larger touch targets for mobile */
            .control-button {
                padding: 14px 20px;
                font-size: 1rem;
                min-height: 44px;
            }

            .toggle-header {
                min-height: 48px;
                padding: 14px;
            }

            .sentiment-bar-container {
                height: 36px;
            }

            /* Prevent text selection on interactive elements */
            .control-button, .toggle-header, .legend-item {
                -webkit-user-select: none;
                user-select: none;
                -webkit-tap-highlight-color: transparent;
            }

            .entity-search {
                font-size: 16px; /* Prevent zoom on iOS */
            }
        }
    """

def _build_enhanced_scripts() -> str:
    """build enhanced JavaScript for improved interactivity."""
    return """
    <script>
        // === Global Variables ===
        let physicsEnabled = true;

        // === Header Toggle (Mobile) ===
        function toggleDetails() {
            const details = document.querySelector('.header-details');
            const toggle = document.querySelector('.toggle-header');
            details.classList.toggle('expanded');
            const isExpanded = details.classList.contains('expanded');
            toggle.textContent = isExpanded
                ? '▲ Hide Details'
                : '▼ Show Details';
            toggle.setAttribute('aria-expanded', String(isExpanded));
        }

        // === Graph Control Functions ===
        function resetView() {
            if (typeof network !== 'undefined') {
                network.moveTo({ scale: 1, position: {x: 0, y: 0}, animation: true });
            }
        }

        function fitToView() {
            if (typeof network !== 'undefined') {
                network.fit({ animation: true });
            }
        }

        function togglePhysics() {
            if (typeof network !== 'undefined') {
                physicsEnabled = !physicsEnabled;
                network.setOptions({ physics: { enabled: physicsEnabled } });
                document.getElementById('physicsLabel').textContent =
                    physicsEnabled ? 'Pause' : 'Resume';
            }
        }

        function showPersonOnly() {
            if (typeof nodes === 'undefined') return;
            const nodeIds = nodes.getIds();
            nodeIds.forEach(id => {
                const node = nodes.get(id);
                nodes.update({
                    id: id,
                    hidden: node.color !== '#4FC3F7'
                });
            });
        }

        function showPlaceOnly() {
            if (typeof nodes === 'undefined') return;
            const nodeIds = nodes.getIds();
            nodeIds.forEach(id => {
                const node = nodes.get(id);
                nodes.update({
                    id: id,
                    hidden: node.color !== '#FF8A65'
                });
            });
        }

        function showAll() {
            if (typeof nodes === 'undefined') return;
            const nodeIds = nodes.getIds();
            nodeIds.forEach(id => {
                nodes.update({ id: id, hidden: false });
            });
            // Reset search
            document.getElementById('entitySearch').value = '';
        }

        // === Entity Search ===
        function searchEntities(query) {
            if (typeof nodes === 'undefined') return;

            if (!query) {
                showAll();
                return;
            }

            const lowerQuery = query.toLowerCase();
            const nodeIds = nodes.getIds();
            const matchingIds = [];

            nodeIds.forEach(id => {
                const node = nodes.get(id);
                const matches = node.label.toLowerCase().includes(lowerQuery);
                nodes.update({
                    id: id,
                    hidden: !matches,
                    borderWidth: matches ? 3 : 1,
                    color: {
                        background: node.color,
                        border: matches ? '#FFD700' : node.color
                    }
                });
                if (matches) matchingIds.push(id);
            });

            // Focus on matching nodes
            if (matchingIds.length > 0 && typeof network !== 'undefined') {
                network.fit({
                    nodes: matchingIds,
                    animation: true
                });
            }
        }

        // === Loading State Management ===
        document.addEventListener('DOMContentLoaded', function() {
            // Wait for network to be defined
            const checkNetwork = setInterval(function() {
                if (typeof network !== 'undefined') {
                    clearInterval(checkNetwork);

                    // Setup loading progress
                    network.on('stabilizationProgress', function(params) {
                        const progress = Math.round((params.iterations / params.total) * 100);
                        const progressBar = document.getElementById('loadingProgress');
                        const loadingText = document.querySelector('.loading-text');
                        if (progressBar) progressBar.style.width = progress + '%';
                        if (loadingText) loadingText.textContent = `Stabilizing layout... ${progress}%`;
                    });

                    network.on('stabilizationIterationsDone', function() {
                        const loadingText = document.querySelector('.loading-text');
                        if (loadingText) loadingText.textContent = 'Complete!';
                        setTimeout(() => {
                            const loading = document.getElementById('graphLoading');
                            if (loading) loading.classList.add('hidden');
                        }, 300);
                    });

                    // Enable navigation buttons for mobile
                    network.setOptions({
                        interaction: {
                            navigationButtons: window.innerWidth <= 768,
                            keyboard: {
                                enabled: true,
                                bindToWindow: false
                            }
                        }
                    });
                }
            }, 100);
        });

        // === Mobile Touch Enhancements ===
        if ('ontouchstart' in window) {
            window.addEventListener('load', function() {
                const networkDiv = document.getElementById('mynetwork');
                if (networkDiv) {
                    // Prevent pull-to-refresh when panning graph
                    let lastY = 0;
                    networkDiv.addEventListener('touchmove', function(e) {
                        const currentY = e.touches[0].clientY;
                        if (lastY < currentY && window.scrollY === 0) {
                            e.preventDefault();
                        }
                        lastY = currentY;
                    }, { passive: false });

                    // Disable double-tap zoom on network canvas
                    networkDiv.addEventListener('touchstart', function(e) {
                        if (e.touches.length > 1) {
                            e.preventDefault();
                        }
                    }, { passive: false });
                }
            });
        }

        // === Responsive Navigation Buttons ===
        window.addEventListener('resize', function() {
            if (typeof network !== 'undefined') {
                network.setOptions({
                    interaction: {
                        navigationButtons: window.innerWidth <= 768
                    }
                });
            }
        });
    </script>
    """

def _build_legend_html(
    title: str,
    subtitle: str,
    person_count: int,
    place_count: int,
    edge_count: int,
    sentiment_counts: dict,
    total_edges: int,
) -> str:
    """build the html header with title, stats, sentiment distribution, and color legend."""
    # calculate percentages
    positive_pct = (sentiment_counts["POSITIVE"] / total_edges * 100) if total_edges > 0 else 0
    negative_pct = (sentiment_counts["NEGATIVE"] / total_edges * 100) if total_edges > 0 else 0
    neutral_pct = (sentiment_counts["NEUTRAL"] / total_edges * 100) if total_edges > 0 else 0
    return f"""
    <!-- Breadcrumb Navigation -->
    <div class="breadcrumb-nav">
        <a href="../../index.html">🏠 Home</a>
        <span class="breadcrumb-separator">/</span>
        <span class="breadcrumb-current">{subtitle}</span>
        <span class="breadcrumb-separator">/</span>
        <span class="breadcrumb-current">{title}</span>
    </div>

    <!-- Graph Header -->
    <div id="graph-header">
        <h1>{title}</h1>
        <p class="subtitle">{subtitle}</p>
        <button class="toggle-header" aria-expanded="false" aria-controls="headerDetails" onclick="toggleDetails()">
            ▼ Show Details
        </button>

        <div class="header-details" id="headerDetails">
            <!-- Legend -->
            <div class="info-box">
                <div class="info-box-title">Legend</div>
                <div class="legend-items">
                    <div class="legend-item">
                        <span class="legend-dot" style="background: {PERSON_COLOR};" aria-hidden="true"></span>
                        <span>Person (blue)</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot" style="background: {PLACE_COLOR};" aria-hidden="true"></span>
                        <span>Place (orange)</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-line" style="background: {SENTIMENT_POSITIVE_COLOR};" aria-hidden="true"></span>
                        <span>😊 Positive (green)</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-line" style="background: {SENTIMENT_NEGATIVE_COLOR};" aria-hidden="true"></span>
                        <span>😞 Negative (red)</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-line" style="background: {SENTIMENT_NEUTRAL_COLOR};" aria-hidden="true"></span>
                        <span>😐 Neutral (gray)</span>
                    </div>
                </div>
            </div>

            <!-- Stats -->
            <div class="info-box">
                <div class="info-box-title">Stats</div>
                <div class="stats-items">
                    <div><span class="stat-number" style="color: {PERSON_COLOR};">{person_count}</span> people</div>
                    <div><span class="stat-number" style="color: {PLACE_COLOR};">{place_count}</span> places</div>
                    <div><span class="stat-number">{edge_count}</span> connections</div>
                </div>
            </div>

            <!-- Sentiment Distribution -->
            <div class="info-box">
                <div class="info-box-title">Sentiment Distribution</div>
                <div class="sentiment-chart">
                    <div class="sentiment-bar-container">
                        <div class="sentiment-bar" style="width: {positive_pct:.1f}%; background: {SENTIMENT_POSITIVE_COLOR};" title="Positive: {positive_pct:.1f}%"></div>
                        <div class="sentiment-bar" style="width: {negative_pct:.1f}%; background: {SENTIMENT_NEGATIVE_COLOR};" title="Negative: {negative_pct:.1f}%"></div>
                        <div class="sentiment-bar" style="width: {neutral_pct:.1f}%; background: {SENTIMENT_NEUTRAL_COLOR};" title="Neutral: {neutral_pct:.1f}%"></div>
                    </div>
                    <div class="sentiment-legend">
                        <div class="sentiment-stat">
                            <span style="color: {SENTIMENT_POSITIVE_COLOR};">😊 {sentiment_counts['POSITIVE']}</span> ({positive_pct:.1f}%)
                        </div>
                        <div class="sentiment-stat">
                            <span style="color: {SENTIMENT_NEGATIVE_COLOR};">😞 {sentiment_counts['NEGATIVE']}</span> ({negative_pct:.1f}%)
                        </div>
                        <div class="sentiment-stat">
                            <span style="color: {SENTIMENT_NEUTRAL_COLOR};">😐 {sentiment_counts['NEUTRAL']}</span> ({neutral_pct:.1f}%)
                        </div>
                    </div>
                </div>
            </div>

            <!-- Controls -->
            <div class="info-box">
                <div class="info-box-title">Controls</div>
                <div class="controls-items">
                    <div>🖱️ Drag nodes to rearrange</div>
                    <div>🔍 Scroll to zoom in/out</div>
                    <div>💬 Hover for details</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Entity Search -->
    <div class="entity-search-container">
        <input
            type="text"
            class="entity-search"
            id="entitySearch"
            placeholder="🔍 Search entities (people, places)..."
            aria-label="Search entities by name"
            oninput="searchEntities(this.value)"
        >
    </div>

    <!-- Graph Controls -->
    <div class="graph-controls">
        <div class="control-group">
            <span class="control-label">View:</span>
            <button class="control-button" onclick="resetView()">Reset Zoom</button>
            <button class="control-button" onclick="fitToView()">Fit All</button>
            <button class="control-button" onclick="togglePhysics()">
                <span id="physicsLabel">Pause</span> Physics
            </button>
        </div>

        <div class="control-group">
            <span class="control-label">Filter:</span>
            <button class="control-button" onclick="showPersonOnly()">People Only</button>
            <button class="control-button" onclick="showPlaceOnly()">Places Only</button>
            <button class="control-button" onclick="showAll()">Show All</button>
        </div>
    </div>
    """

def visualize_graph(
    graph: nx.DiGraph,
    output_path: Path,
    title: str = "",
    subtitle: str = "",
) -> None:
    """render an interactive pyvis html visualization of a graph."""
    net = Network(
        height="85vh",  # Responsive height
        width="100%",
        directed=True,
        bgcolor="#1e1e1e",
        font_color="white",
        notebook=False,
    )
    net.barnes_hut(gravity=-3000, central_gravity=0.3, spring_length=150)

    for node, attrs in graph.nodes(data=True):
        entity_type = attrs.get("entity_type", "UNKNOWN")
        color = PERSON_COLOR if entity_type == "PERSON" else PLACE_COLOR
        size = 15 + graph.degree(node) * 2
        label = node
        hover = f"{node}\nType: {entity_type}\nConnections: {graph.degree(node)}"
        net.add_node(node, label=label, title=hover, color=color, size=min(size, 60))

    for u, v, data in graph.edges(data=True):
        relation = data.get("relation", "")
        weight = data.get("weight", 1)
        contexts = data.get("contexts", [])
        speakers = data.get("speakers", [])

        # calculate dominant sentiment from contexts
        dominant_sentiment = _dominant_sentiment(contexts)

        # determine edge color based on sentiment
        if dominant_sentiment == "POSITIVE":
            color = SENTIMENT_POSITIVE_COLOR
        elif dominant_sentiment == "NEGATIVE":
            color = SENTIMENT_NEGATIVE_COLOR
        else:
            color = SENTIMENT_NEUTRAL_COLOR

        # build rich tooltip with narrative context
        dominant_emoji = SENTIMENT_EMOJI.get(dominant_sentiment, "😐")

        hover_parts = [
            f"📍 {u} → {v}",
            "━━━━━━━━━━━━━━━━━━━━",
            f"Relationship: {relation.replace('_', ' ').title()}",
            f"Mentions: {weight}",
            f"Overall Sentiment: {dominant_sentiment} {dominant_emoji}",
        ]

        if speakers:
            hover_parts.append(f"Discussed by: {', '.join(set(speakers))}")

        # add narrative context snippets
        if contexts:
            hover_parts.append("\n💬 Context:")
            for idx, ctx in enumerate(contexts[:MAX_CONTEXTS_DISPLAY], 1):
                temporal = ctx.get("temporal", "")
                speaker = ctx.get("speaker", "Unknown")
                text = ctx.get("text", "")
                person_ctx = ctx.get("person", "")
                sentiment = ctx.get("sentiment", {})
                sentiment_emoji = sentiment.get("emoji", "")

                # truncate text at word boundary if too long
                if len(text) > MAX_CONTEXT_DISPLAY_TEXT:
                    text = text[:MAX_CONTEXT_DISPLAY_TEXT].rsplit(" ", 1)[0] + "…"

                temporal_label = TEMPORAL_LABELS.get(temporal, "")
                sentiment_str = f" {sentiment_emoji}" if sentiment_emoji else ""
                speaker_line = f"  🗣 {speaker}"
                if person_ctx:
                    speaker_line += f" (about {person_ctx})"

                hover_parts.append(f"\n{temporal_label}{sentiment_str}")
                hover_parts.append(speaker_line)
                hover_parts.append(f'  "{text}"')

        net.add_edge(u, v, value=weight, color=color, title="\n".join(hover_parts))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    net.save_graph(str(output_path))

    # calculate sentiment statistics
    sentiment_counts = {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0}
    total_edges = 0
    for _, _, data in graph.edges(data=True):
        sentiment_counts[_dominant_sentiment(data.get("contexts", []))] += 1
        total_edges += 1

    # inject custom header with legend into the generated html.
    person_count = sum(
        1 for _, d in graph.nodes(data=True) if d.get("entity_type") == "PERSON"
    )
    place_count = sum(
        1 for _, d in graph.nodes(data=True) if d.get("entity_type") == "PLACE"
    )
    legend_html = _build_legend_html(
        title=title or "Entity Graph",
        subtitle=subtitle,
        person_count=person_count,
        place_count=place_count,
        edge_count=graph.number_of_edges(),
        sentiment_counts=sentiment_counts,
        total_edges=total_edges,
    )

    # build enhanced CSS styles
    enhanced_styles = _build_enhanced_styles()

    # build enhanced JavaScript
    enhanced_scripts = _build_enhanced_scripts()

    html = output_path.read_text(encoding="utf-8")

    # remove the default pyvis heading.
    html = re.sub(
        r"<center>\s*<h1>.*?</h1>\s*</center>",
        "",
        html,
        flags=re.DOTALL,
    )

    # inject enhanced styles in <head>
    html = html.replace("</style>", f"{enhanced_styles}\n</style>", 1)

    # inject viewport meta tag if not present for mobile responsiveness
    if '<meta name="viewport"' not in html:
        viewport_meta = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">'
        html = html.replace("<head>", f"<head>\n    {viewport_meta}", 1)

    # inject legend and controls after <body> tag.
    html = html.replace("<body>", f"<body>\n{legend_html}", 1)

    # add loading overlay to #mynetwork div
    loading_overlay = """
    <div class="graph-loading" id="graphLoading">
        <div class="loading-spinner"></div>
        <div class="loading-text">Initializing graph...</div>
        <div class="loading-progress">
            <div class="loading-progress-bar" id="loadingProgress"></div>
        </div>
    </div>
    """
    html = html.replace(
        '<div id="mynetwork"',
        '<div id="mynetwork" style="position: relative;">' + loading_overlay + '<div style="width: 100%; height: 100%;"',
        1
    )
    # close the wrapper div before the original closing div
    html = re.sub(
        r'(</div>\s*</body>)',
        r'</div>\1',
        html,
        count=1
    )

    # inject enhanced scripts before </body>
    html = html.replace("</body>", f"{enhanced_scripts}\n</body>", 1)

    output_path.write_text(html, encoding="utf-8")

// application entry point: load catalog data and render the show list.

import { loadAllData } from './api';
import { getState, getVisibleShows, setState, subscribe } from './state';
import { $, createElement, escapeHTML } from './utils/dom';

// render the current state into the #app container.
function render(): void {
  const app = $('#app');
  if (!app) return;

  app.replaceChildren();

  if (getState().isLoading) {
    app.appendChild(createElement('p', {}, ['Loading…']));
    return;
  }

  const shows = getVisibleShows();
  if (shows.length === 0) {
    app.appendChild(createElement('p', {}, ['No shows found.']));
    return;
  }

  for (const show of shows) {
    app.appendChild(
      createElement('section', { className: 'show-card' }, [
        createElement('h2', {}, [escapeHTML(show.displayName)]),
        createElement('p', {}, [`${show.episodeCount} episodes`]),
      ])
    );
  }
}

// load the catalog and update state, surfacing any error in the ui.
async function main(): Promise<void> {
  subscribe(render);
  render();

  try {
    const { index, topics } = await loadAllData();
    setState({
      shows: index.shows,
      topicsData: topics,
      // -1 is the "all shows" sentinel for getVisibleShows.
      currentShowIdx: -1,
      isLoading: false,
    });
  } catch (err) {
    setState({ isLoading: false });
    const app = $('#app');
    if (app) {
      const message = err instanceof Error ? err.message : String(err);
      app.replaceChildren(
        createElement('p', { className: 'error' }, [`Failed to load data: ${message}`])
      );
    }
  }
}

void main();

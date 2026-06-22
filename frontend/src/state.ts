// centralized state management for the application.

import type { Show, TopicsData, FilterType } from './types';

export interface AppState {
  shows: Show[];
  currentShowIdx: number;
  currentFilter: FilterType;
  currentSearch: string;
  topicsData: TopicsData | null;
  currentTopicFilter: number | null;
  isLoading: boolean;
}

// initial state.
const state: AppState = {
  shows: [],
  currentShowIdx: 0,
  currentFilter: 'all',
  currentSearch: '',
  topicsData: null,
  currentTopicFilter: null,
  isLoading: true,
};

// subscribers for state changes.
type Subscriber = (state: AppState) => void;
const subscribers: Subscriber[] = [];

// get current state (readonly).
export function getState(): Readonly<AppState> {
  return state;
}

// update state and notify subscribers.
export function setState(updates: Partial<AppState>): void {
  Object.assign(state, updates);
  notifySubscribers();
}

// subscribe to state changes.
export function subscribe(fn: Subscriber): () => void {
  subscribers.push(fn);
  return () => {
    const idx = subscribers.indexOf(fn);
    if (idx > -1) subscribers.splice(idx, 1);
  };
}

function notifySubscribers(): void {
  subscribers.forEach((fn) => fn(state));
}

// computed getters.
export function getVisibleShows(): Show[] {
  const { shows, currentShowIdx } = state;
  if (currentShowIdx === -1) return shows;
  return shows[currentShowIdx] ? [shows[currentShowIdx]] : [];
}

export function getTotalEpisodeCount(): number {
  return state.shows.reduce((sum, show) => sum + show.episodeCount, 0);
}

export function getTopicLabel(topicId: number): string {
  const { topicsData } = state;
  if (!topicsData?.topics) return `Topic ${topicId}`;
  const topic = topicsData.topics.find((t) => t.topic_id === topicId);
  return topic?.curated_label || topic?.topic_label || `Topic ${topicId}`;
}

export function isFiltered(): boolean {
  const { currentSearch, currentFilter, currentTopicFilter } = state;
  return currentSearch !== '' || currentFilter !== 'all' || currentTopicFilter !== null;
}

// data fetching functions.

import type { IndexData, TopicsData } from './types';

const INDEX_URL = 'index.json';
const TOPICS_URL = 'graphs/topics.json';

export async function fetchIndex(): Promise<IndexData> {
  const response = await fetch(INDEX_URL);
  if (!response.ok) {
    throw new Error(`Failed to load index.json: ${response.status}`);
  }
  return response.json();
}

export async function fetchTopics(): Promise<TopicsData | null> {
  try {
    const response = await fetch(TOPICS_URL);
    if (!response.ok) return null;
    return response.json();
  } catch {
    // topics are optional, fail silently.
    return null;
  }
}

export async function loadAllData(): Promise<{
  index: IndexData;
  topics: TopicsData | null;
}> {
  const [topics, index] = await Promise.all([fetchTopics(), fetchIndex()]);
  return { index, topics };
}

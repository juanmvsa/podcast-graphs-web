// core data types for the podcast graphs application.

export interface Episode {
  path: string;
  title: string;
  filename: string;
}

export interface TopicSummary {
  path: string;
  title: string;
  topicId: number;
}

export interface Show {
  name: string;
  displayName: string;
  episodeCount: number;
  summaryPath?: string;
  topicSummaries?: TopicSummary[];
  episodes: Episode[];
}

export interface IndexData {
  totalShows: number;
  totalEpisodes: number;
  shows: Show[];
}

export interface Topic {
  topic_id: number;
  topic_words?: string[];
  topic_label?: string;
  curated_label?: string;
  episode_count?: number;
  episodes?: string[];
}

export interface EpisodeTopic {
  topic_id: number;
  topic_words?: string[];
  topic_label?: string;
  curated_label?: string;
}

export interface TopicsData {
  topics: Topic[];
  episode_topics: Record<string, EpisodeTopic>;
}

export type FilterType = 'all' | 'summary' | 'episode';

export type CardType = 'episode' | 'summary' | 'topic-summary';

// per-graph edge data, matching the backend SerializedEdge json shape.
export interface Sentiment {
  label: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL';
  score: number;
  emoji: string;
}

export interface Context {
  text: string;
  speaker: string;
  temporal: 'early' | 'middle' | 'late';
  timestamp: number;
  sentiment: Sentiment;
  person?: string | null;
}

export interface Edge {
  source: string;
  target: string;
  weight: number;
  relation: string;
  speakers: string[];
  contexts: Context[];
}

// API Types - shared across the application

export interface Sentiment {
  positive: number;
  neutral: number;
  negative: number;
}

export interface Tool {
  id: string;
  rank: number;
  name: string;
  company: string;
  logo?: string;
  sentiment: Sentiment;
  mentions: number;
  trend: "up" | "down" | "stable";
  type: "llm" | "tool";
}

export interface TrendDataPoint {
  date: string;
  mentions: number;
  sentiment: number;
}

export interface Mention {
  id: string;
  source: string;
  text: string;
  date: string;
  sentiment: "positive" | "neutral" | "negative";
}

export interface ToolDetail extends Tool {
  description: string;
  versions: string[];
  currentVersion: string;
  bestFor: string[];
  rating: number;
  trendData: TrendDataPoint[];
  recentMentions: Mention[];
}

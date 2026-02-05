// API Service - Replace mock data with real API calls when ready
// TODO: Replace BASE_URL with your actual API endpoint
// const BASE_URL = "https://your-api.example.com";

import type { Tool, ToolDetail } from "@/types/api";

// =============================================================================
// MOCK DATA - Remove this section when connecting to real API
// =============================================================================

const mockTools: Tool[] = [
  {
    id: "chatgpt",
    rank: 1,
    name: "ChatGPT",
    company: "OpenAI",
    sentiment: { positive: 72, neutral: 20, negative: 8 },
    mentions: 45230,
    trend: "up",
    type: "llm",
  },
  {
    id: "claude",
    rank: 2,
    name: "Claude",
    company: "Anthropic",
    sentiment: { positive: 78, neutral: 18, negative: 4 },
    mentions: 32150,
    trend: "up",
    type: "llm",
  },
  {
    id: "gemini",
    rank: 3,
    name: "Gemini",
    company: "Google",
    sentiment: { positive: 65, neutral: 25, negative: 10 },
    mentions: 28400,
    trend: "stable",
    type: "llm",
  },
  {
    id: "cursor",
    rank: 4,
    name: "Cursor",
    company: "Cursor Inc.",
    sentiment: { positive: 85, neutral: 12, negative: 3 },
    mentions: 18750,
    trend: "up",
    type: "tool",
  },
  {
    id: "copilot",
    rank: 5,
    name: "GitHub Copilot",
    company: "GitHub",
    sentiment: { positive: 70, neutral: 22, negative: 8 },
    mentions: 24300,
    trend: "stable",
    type: "tool",
  },
  {
    id: "midjourney",
    rank: 6,
    name: "Midjourney",
    company: "Midjourney",
    sentiment: { positive: 82, neutral: 13, negative: 5 },
    mentions: 35600,
    trend: "down",
    type: "tool",
  },
];

const mockToolDetails: Record<string, ToolDetail> = {
  chatgpt: {
    id: "chatgpt",
    rank: 1,
    name: "ChatGPT",
    company: "OpenAI",
    description: "Ein leistungsstarkes LLM für natürliche Sprachverarbeitung und Konversation.",
    versions: ["GPT-4o", "GPT-4", "GPT-3.5"],
    currentVersion: "GPT-4o",
    sentiment: { positive: 72, neutral: 20, negative: 8 },
    mentions: 45230,
    trend: "up",
    type: "llm",
    bestFor: ["Konversation", "Code-Generierung", "Textanalyse", "Kreatives Schreiben"],
    rating: 4.5,
    trendData: [
      { date: "Jan", mentions: 35000, sentiment: 68 },
      { date: "Feb", mentions: 38000, sentiment: 70 },
      { date: "Mär", mentions: 42000, sentiment: 71 },
      { date: "Apr", mentions: 40000, sentiment: 69 },
      { date: "Mai", mentions: 43000, sentiment: 72 },
      { date: "Jun", mentions: 45230, sentiment: 72 },
    ],
    recentMentions: [
      {
        id: "1",
        source: "Twitter",
        text: "ChatGPT hat mir gerade geholfen, einen komplexen Bug zu finden. Unglaublich nützlich!",
        date: "vor 2 Stunden",
        sentiment: "positive",
      },
      {
        id: "2",
        source: "Reddit",
        text: "Die neuen GPT-4o Funktionen sind wirklich beeindruckend.",
        date: "vor 5 Stunden",
        sentiment: "positive",
      },
      {
        id: "3",
        source: "Hacker News",
        text: "Interessante Diskussion über die Grenzen von ChatGPT bei mathematischen Problemen.",
        date: "vor 1 Tag",
        sentiment: "neutral",
      },
    ],
  },
};

// =============================================================================
// API FUNCTIONS - Update these to use real fetch calls when API is ready
// =============================================================================

/**
 * Fetch all tools/LLMs
 * TODO: Replace with: return fetch(`${BASE_URL}/tools`).then(res => res.json())
 */
export async function fetchTools(): Promise<Tool[]> {
  // Simulate network delay
  await new Promise((resolve) => setTimeout(resolve, 300));
  return mockTools;
}

/**
 * Fetch tool/LLM details by ID
 * TODO: Replace with: return fetch(`${BASE_URL}/tools/${id}`).then(res => res.json())
 */
export async function fetchToolDetail(id: string): Promise<ToolDetail | null> {
  // Simulate network delay
  await new Promise((resolve) => setTimeout(resolve, 300));
  
  // Return specific mock or generate a generic one based on the tool
  if (mockToolDetails[id]) {
    return mockToolDetails[id];
  }
  
  // Find the tool in the list and create a detail object
  const tool = mockTools.find((t) => t.id === id);
  if (!tool) return null;
  
  return {
    ...tool,
    description: `${tool.name} ist ein führendes ${tool.type === "llm" ? "Sprachmodell" : "AI-Tool"} von ${tool.company}.`,
    versions: ["v1.0", "v2.0"],
    currentVersion: "v2.0",
    bestFor: ["Produktivität", "Automatisierung"],
    rating: 4.2,
    trendData: [
      { date: "Jan", mentions: Math.round(tool.mentions * 0.7), sentiment: tool.sentiment.positive - 5 },
      { date: "Feb", mentions: Math.round(tool.mentions * 0.8), sentiment: tool.sentiment.positive - 3 },
      { date: "Mär", mentions: Math.round(tool.mentions * 0.85), sentiment: tool.sentiment.positive - 2 },
      { date: "Apr", mentions: Math.round(tool.mentions * 0.9), sentiment: tool.sentiment.positive - 1 },
      { date: "Mai", mentions: Math.round(tool.mentions * 0.95), sentiment: tool.sentiment.positive },
      { date: "Jun", mentions: tool.mentions, sentiment: tool.sentiment.positive },
    ],
    recentMentions: [
      {
        id: "1",
        source: "Twitter",
        text: `${tool.name} wird immer beliebter in der Community.`,
        date: "vor 3 Stunden",
        sentiment: "positive",
      },
      {
        id: "2",
        source: "Reddit",
        text: `Diskussion über ${tool.name} Features und Anwendungsfälle.`,
        date: "vor 1 Tag",
        sentiment: "neutral",
      },
    ],
  };
}

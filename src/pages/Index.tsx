import { useState } from "react";
import Header from "@/components/Header";
import TabFilter from "@/components/TabFilter";
import ToolCard, { ToolData } from "@/components/ToolCard";

// Placeholder data - will be replaced with API fetch
const mockTools: ToolData[] = [
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

const Index = () => {
  const [activeTab, setActiveTab] = useState("all");

  const filteredTools = mockTools.filter((tool) => {
    if (activeTab === "all") return true;
    if (activeTab === "llms") return tool.type === "llm";
    if (activeTab === "tools") return tool.type === "tool";
    return true;
  });

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="container mx-auto px-6 pt-24 pb-12">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-semibold tracking-tight mb-2">AI Radar</h1>
          <p className="text-muted-foreground">
            Verfolge die Stimmung und Trends führender AI Tools und LLMs
          </p>
        </div>

        {/* Tabs */}
        <div className="mb-8">
          <TabFilter activeTab={activeTab} onTabChange={setActiveTab} />
        </div>

        {/* Card Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {filteredTools.map((tool) => (
            <ToolCard key={tool.id} tool={tool} />
          ))}
        </div>
      </main>
    </div>
  );
};

export default Index;

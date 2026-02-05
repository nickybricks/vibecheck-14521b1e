import { Link } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import SentimentBar from "./SentimentBar";
import TrendIndicator from "./TrendIndicator";
import type { Tool } from "@/types/api";

// Re-export for backwards compatibility
export type ToolData = Tool;

interface ToolCardProps {
  tool: ToolData;
}

const ToolCard = ({ tool }: ToolCardProps) => {
  return (
    <Link to={`/detail/${tool.id}`}>
      <Card className="card-hover cursor-pointer bg-card border-border/50 rounded-2xl overflow-hidden">
        <CardContent className="p-5">
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-secondary flex items-center justify-center overflow-hidden">
                {tool.logo ? (
                  <img src={tool.logo} alt={tool.name} className="w-8 h-8 object-contain" />
                ) : (
                  <span className="text-lg font-semibold text-muted-foreground">
                    {tool.name.charAt(0)}
                  </span>
                )}
              </div>
              <div>
                <h3 className="font-semibold text-foreground">{tool.name}</h3>
                <p className="text-sm text-muted-foreground">{tool.company}</p>
              </div>
            </div>
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-secondary">
              <span className="text-sm font-semibold text-foreground">#{tool.rank}</span>
            </div>
          </div>

          {/* Sentiment Bar */}
          <SentimentBar 
            positive={tool.sentiment.positive}
            neutral={tool.sentiment.neutral}
            negative={tool.sentiment.negative}
            className="mb-4"
          />

          {/* Stats */}
          <div className="flex items-center justify-between">
            <div className="text-sm">
              <span className="text-muted-foreground">Mentions: </span>
              <span className="font-medium text-foreground">{tool.mentions.toLocaleString()}</span>
            </div>
            <TrendIndicator trend={tool.trend} />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
};

export default ToolCard;

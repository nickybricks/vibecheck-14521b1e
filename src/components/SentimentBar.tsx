import { cn } from "@/lib/utils";

interface SentimentBarProps {
  positive: number;
  neutral: number;
  negative: number;
  className?: string;
}

const SentimentBar = ({ positive, neutral, negative, className }: SentimentBarProps) => {
  const total = positive + neutral + negative;
  const positivePercent = total > 0 ? (positive / total) * 100 : 0;
  const neutralPercent = total > 0 ? (neutral / total) * 100 : 0;
  const negativePercent = total > 0 ? (negative / total) * 100 : 0;

  return (
    <div className={cn("w-full", className)}>
      <div className="flex h-2 rounded-full overflow-hidden bg-secondary">
        <div 
          className="bg-[hsl(var(--sentiment-positive))] transition-all duration-300"
          style={{ width: `${positivePercent}%` }}
        />
        <div 
          className="bg-[hsl(var(--sentiment-neutral))] transition-all duration-300"
          style={{ width: `${neutralPercent}%` }}
        />
        <div 
          className="bg-[hsl(var(--sentiment-negative))] transition-all duration-300"
          style={{ width: `${negativePercent}%` }}
        />
      </div>
      <div className="flex justify-between mt-1 text-xs text-muted-foreground">
        <span>{positivePercent.toFixed(0)}% positiv</span>
        <span>{negativePercent.toFixed(0)}% negativ</span>
      </div>
    </div>
  );
};

export default SentimentBar;

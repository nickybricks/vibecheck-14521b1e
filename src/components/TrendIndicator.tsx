import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface TrendIndicatorProps {
  trend: "up" | "down" | "stable";
  value?: string;
  className?: string;
}

const TrendIndicator = ({ trend, value, className }: TrendIndicatorProps) => {
  const config = {
    up: {
      icon: TrendingUp,
      color: "text-[hsl(var(--trend-up))]",
      label: "Steigend",
    },
    down: {
      icon: TrendingDown,
      color: "text-[hsl(var(--trend-down))]",
      label: "Fallend",
    },
    stable: {
      icon: Minus,
      color: "text-[hsl(var(--trend-stable))]",
      label: "Stabil",
    },
  };

  const { icon: Icon, color, label } = config[trend];

  return (
    <div className={cn("flex items-center gap-1.5", color, className)}>
      <Icon className="w-4 h-4" />
      <span className="text-sm font-medium">{value || label}</span>
    </div>
  );
};

export default TrendIndicator;

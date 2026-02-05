import { cn } from "@/lib/utils";

interface MiniSparklineProps {
  data: number[];
  className?: string;
  color?: string;
}

const MiniSparkline = ({ data, className, color = "hsl(var(--primary))" }: MiniSparklineProps) => {
  if (!data || data.length < 2) return null;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  
  const width = 80;
  const height = 24;
  const padding = 2;
  
  const points = data.map((value, index) => {
    const x = padding + (index / (data.length - 1)) * (width - padding * 2);
    const y = height - padding - ((value - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  }).join(" ");

  return (
    <svg 
      viewBox={`0 0 ${width} ${height}`}
      className={cn("w-20 h-6", className)}
      preserveAspectRatio="none"
    >
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

export default MiniSparkline;

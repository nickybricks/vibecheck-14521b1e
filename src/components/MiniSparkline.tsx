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
  
  // Generate points
  const points = data.map((value, index) => ({
    x: padding + (index / (data.length - 1)) * (width - padding * 2),
    y: height - padding - ((value - min) / range) * (height - padding * 2),
  }));

  // Create smooth bezier curve path
  const path = points.reduce((acc, point, index) => {
    if (index === 0) {
      return `M ${point.x},${point.y}`;
    }
    
    const prev = points[index - 1];
    const tension = 0.3;
    const cpx1 = prev.x + (point.x - prev.x) * tension;
    const cpx2 = point.x - (point.x - prev.x) * tension;
    
    return `${acc} C ${cpx1},${prev.y} ${cpx2},${point.y} ${point.x},${point.y}`;
  }, "");

  return (
    <svg 
      viewBox={`0 0 ${width} ${height}`}
      className={cn("w-20 h-6", className)}
      preserveAspectRatio="none"
    >
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
};

export default MiniSparkline;

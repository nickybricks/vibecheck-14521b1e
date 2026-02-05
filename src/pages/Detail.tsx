import { useParams, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import Header from "@/components/Header";
import SentimentBar from "@/components/SentimentBar";
import TrendIndicator from "@/components/TrendIndicator";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useToolDetail } from "@/hooks/useTools";

const Detail = () => {
  const { id } = useParams<{ id: string }>();
  const { data: tool, isLoading, error } = useToolDetail(id);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="container mx-auto px-6 pt-24 pb-12">
          <Skeleton className="h-5 w-40 mb-6" />
          <div className="flex items-center gap-4 mb-8">
            <Skeleton className="w-16 h-16 rounded-2xl" />
            <div>
              <Skeleton className="h-7 w-32 mb-2" />
              <Skeleton className="h-5 w-20" />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24 rounded-2xl" />
            ))}
          </div>
          <Skeleton className="h-80 rounded-2xl" />
        </main>
      </div>
    );
  }

  if (error || !tool) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="container mx-auto px-6 pt-24 pb-12">
          <Link 
            to="/" 
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 mb-6"
          >
            <ArrowLeft className="w-4 h-4" />
            Zurück zum Dashboard
          </Link>
          <div className="text-center py-12">
            <p className="text-destructive">Tool nicht gefunden.</p>
          </div>
        </main>
      </div>
    );
  }

  const sentimentPercent = Math.round(
    (tool.sentiment.positive / 
      (tool.sentiment.positive + tool.sentiment.neutral + tool.sentiment.negative)) * 100
  );

  return (
    <div className="min-h-screen bg-background">
      <Header />
      
      <main className="container mx-auto px-6 pt-24 pb-12">
        {/* Back Link */}
        <Link 
          to="/" 
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors duration-200 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Zurück zum Dashboard
        </Link>

        {/* Header Section */}
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-6 mb-8">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-secondary flex items-center justify-center">
              {tool.logo ? (
                <img src={tool.logo} alt={tool.name} className="w-10 h-10 object-contain" />
              ) : (
                <span className="text-2xl font-semibold text-muted-foreground">
                  {tool.name.charAt(0)}
                </span>
              )}
            </div>
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">{tool.name}</h1>
              <p className="text-muted-foreground">{tool.company}</p>
            </div>
          </div>

          <Select defaultValue={tool.currentVersion}>
            <SelectTrigger className="w-40 rounded-xl">
              <SelectValue placeholder="Version" />
            </SelectTrigger>
            <SelectContent>
              {tool.versions.map((version) => (
                <SelectItem key={version} value={version}>
                  {version}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <Card className="rounded-2xl border-border/50">
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground mb-1">Sentiment</p>
              <p className="text-2xl font-semibold text-[hsl(var(--sentiment-positive))]">
                {sentimentPercent}% positiv
              </p>
            </CardContent>
          </Card>
          <Card className="rounded-2xl border-border/50">
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground mb-1">Mentions</p>
              <p className="text-2xl font-semibold">{tool.mentions.toLocaleString()}</p>
            </CardContent>
          </Card>
          <Card className="rounded-2xl border-border/50">
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground mb-1">Trend</p>
              <TrendIndicator trend={tool.trend} className="text-xl" />
            </CardContent>
          </Card>
        </div>

        {/* Trend Chart */}
        <Card className="rounded-2xl border-border/50 mb-8">
          <CardHeader>
            <CardTitle className="text-lg font-semibold">Trend der letzten 6 Monate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={tool.trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis 
                    dataKey="date" 
                    stroke="hsl(var(--muted-foreground))"
                    fontSize={12}
                  />
                  <YAxis 
                    stroke="hsl(var(--muted-foreground))"
                    fontSize={12}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: "12px",
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="mentions"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={{ fill: "hsl(var(--primary))", strokeWidth: 0, r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Best For + Rating */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Card className="rounded-2xl border-border/50">
            <CardHeader>
              <CardTitle className="text-lg font-semibold">Best For</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {tool.bestFor.map((tag) => (
                  <Badge 
                    key={tag} 
                    variant="secondary"
                    className="rounded-full px-3 py-1 text-sm"
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
          <Card className="rounded-2xl border-border/50">
            <CardHeader>
              <CardTitle className="text-lg font-semibold">Rating</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <span className="text-3xl font-semibold">{tool.rating}</span>
                <span className="text-muted-foreground">/ 5.0</span>
              </div>
              <SentimentBar 
                positive={tool.sentiment.positive}
                neutral={tool.sentiment.neutral}
                negative={tool.sentiment.negative}
                className="mt-4"
              />
            </CardContent>
          </Card>
        </div>

        {/* Recent Mentions */}
        <Card className="rounded-2xl border-border/50">
          <CardHeader>
            <CardTitle className="text-lg font-semibold">Recent Mentions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {tool.recentMentions.map((mention) => (
                <div 
                  key={mention.id}
                  className="p-4 rounded-xl bg-secondary/50 border border-border/30"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="rounded-full text-xs">
                        {mention.source}
                      </Badge>
                      <Badge 
                        variant="secondary"
                        className={`rounded-full text-xs ${
                          mention.sentiment === "positive" 
                            ? "bg-[hsl(var(--sentiment-positive)/0.1)] text-[hsl(var(--sentiment-positive))]"
                            : mention.sentiment === "negative"
                            ? "bg-[hsl(var(--sentiment-negative)/0.1)] text-[hsl(var(--sentiment-negative))]"
                            : ""
                        }`}
                      >
                        {mention.sentiment}
                      </Badge>
                    </div>
                    <span className="text-xs text-muted-foreground">{mention.date}</span>
                  </div>
                  <p className="text-sm text-foreground">{mention.text}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default Detail;

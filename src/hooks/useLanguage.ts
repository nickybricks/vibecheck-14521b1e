import { useMemo } from "react";

type TranslationKey = 
  | "backToDashboard"
  | "sentiment"
  | "mentions"
  | "trend"
  | "trendUp"
  | "trendDown"
  | "trendStable"
  | "positive"
  | "negative"
  | "neutral"
  | "positivePercent"
  | "trendLast6Months"
  | "bestFor"
  | "rating"
  | "recentMentions"
  | "toolNotFound"
  | "selectModel"
  | "all"
  | "llms"
  | "tools"
  | "errorLoading"
  | "search"
  | "searchPlaceholder"
  | "noResults"
  | "days7"
  | "outOf"
  | "recentlySearched"
  | "trending"
  | "remove";

type Translations = Record<TranslationKey, string>;

const translations: Record<string, Translations> = {
  en: {
    backToDashboard: "Back to Dashboard",
    sentiment: "Sentiment",
    mentions: "Mentions",
    trend: "Trend",
    trendUp: "Rising",
    trendDown: "Falling",
    trendStable: "Stable",
    positive: "Positive",
    negative: "Negative",
    neutral: "Neutral",
    positivePercent: "positive",
    trendLast6Months: "Trend over the last 6 months",
    bestFor: "Best For",
    rating: "Rating",
    recentMentions: "Recent Mentions",
    toolNotFound: "Tool not found.",
    selectModel: "Select model",
    all: "All",
    llms: "🧠 LLMs",
    tools: "🔧 Tools",
    errorLoading: "Error loading data.",
    search: "Search",
    searchPlaceholder: "Search tools...",
    noResults: "No results found.",
    days7: "7d",
    outOf: "out of",
    recentlySearched: "Recently searched",
    trending: "Trending",
    remove: "Remove",
  },
  de: {
    backToDashboard: "Zurück zum Dashboard",
    sentiment: "Sentiment",
    mentions: "Mentions",
    trend: "Trend",
    trendUp: "Steigend",
    trendDown: "Fallend",
    trendStable: "Stabil",
    positive: "Positiv",
    negative: "Negativ",
    neutral: "Neutral",
    positivePercent: "positiv",
    trendLast6Months: "Trend der letzten 6 Monate",
    bestFor: "Best For",
    rating: "Rating",
    recentMentions: "Letzte Erwähnungen",
    toolNotFound: "Tool nicht gefunden.",
    selectModel: "Modell wählen",
    all: "Alle",
    llms: "🧠 LLMs",
    tools: "🔧 Tools",
    errorLoading: "Fehler beim Laden der Daten.",
    search: "Suche",
    searchPlaceholder: "Tools suchen...",
    noResults: "Keine Ergebnisse gefunden.",
    days7: "7T",
    outOf: "von",
    recentlySearched: "Zuletzt gesucht",
    trending: "Trending",
    remove: "Entfernen",
  },
};

export const useLanguage = () => {
  const language = useMemo(() => {
    const browserLang = navigator.language.split("-")[0];
    return translations[browserLang] ? browserLang : "en";
  }, []);

  const t = useMemo(() => {
    return (key: TranslationKey): string => {
      return translations[language]?.[key] || translations.en[key] || key;
    };
  }, [language]);

  return { language, t };
};

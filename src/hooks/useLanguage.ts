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
  | "tools";

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
    recentMentions: "Recent Mentions",
    toolNotFound: "Tool nicht gefunden.",
    selectModel: "Modell wählen",
    all: "Alle",
    llms: "🧠 LLMs",
    tools: "🔧 Tools",
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

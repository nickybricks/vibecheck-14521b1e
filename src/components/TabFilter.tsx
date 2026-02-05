import { cn } from "@/lib/utils";
import { useLanguage } from "@/hooks/useLanguage";

interface TabFilterProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const TabFilter = ({ activeTab, onTabChange }: TabFilterProps) => {
  const { t } = useLanguage();

  const tabs = [
    { id: "all", label: t("all") },
    { id: "llms", label: t("llms") },
    { id: "tools", label: t("tools") },
  ];

  return (
    <div className="flex items-center gap-2 p-1 bg-secondary rounded-full">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          className={cn(
            "px-4 py-2 text-sm font-medium rounded-full transition-all duration-200",
            activeTab === tab.id
              ? "bg-primary text-primary-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
};

export default TabFilter;

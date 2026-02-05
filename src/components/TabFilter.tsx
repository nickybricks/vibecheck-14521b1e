import { cn } from "@/lib/utils";

interface TabFilterProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
}

const tabs = [
  { id: "all", label: "All" },
  { id: "llms", label: "🧠 LLMs" },
  { id: "tools", label: "🔧 Tools" },
];

const TabFilter = ({ activeTab, onTabChange }: TabFilterProps) => {
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

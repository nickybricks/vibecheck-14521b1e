import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Clock, X } from "lucide-react";
import { useTools } from "@/hooks/useTools";
import { ScrollArea } from "@/components/ui/scroll-area";

const RECENT_SEARCHES_KEY = "vibecheck_recent_searches";
const MAX_RECENT_SEARCHES = 5;

interface RecentSearch {
  id: string;
  name: string;
  company: string;
  logo?: string;
}

const getRecentSearches = (): RecentSearch[] => {
  try {
    const stored = localStorage.getItem(RECENT_SEARCHES_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
};

const saveRecentSearch = (search: RecentSearch) => {
  const recent = getRecentSearches();
  const filtered = recent.filter((s) => s.id !== search.id);
  const updated = [search, ...filtered].slice(0, MAX_RECENT_SEARCHES);
  localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(updated));
};

const removeRecentSearch = (id: string) => {
  const recent = getRecentSearches();
  const filtered = recent.filter((s) => s.id !== id);
  localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(filtered));
};

const SearchDropdown = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [imageErrors, setImageErrors] = useState<Record<string, boolean>>({});
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { data: tools } = useTools();

  // Load recent searches on mount
  useEffect(() => {
    setRecentSearches(getRecentSearches());
  }, []);

  const filteredTools = tools?.filter((tool) =>
    tool.name.toLowerCase().includes(query.toLowerCase())
  ) ?? [];

  const showRecent = query === "" && recentSearches.length > 0;

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Keyboard shortcut "/"
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "/" && document.activeElement !== inputRef.current) {
        event.preventDefault();
        inputRef.current?.focus();
        setIsOpen(true);
      }
      if (event.key === "Escape") {
        setIsOpen(false);
        inputRef.current?.blur();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleSelect = (tool: { id: string; name: string; company: string; logo?: string }) => {
    saveRecentSearch({
      id: tool.id,
      name: tool.name,
      company: tool.company,
      logo: tool.logo,
    });
    setRecentSearches(getRecentSearches());
    navigate(`/detail/${tool.id}`);
    setIsOpen(false);
    setQuery("");
  };

  const handleRemoveRecent = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    removeRecentSearch(id);
    setRecentSearches(getRecentSearches());
  };

  const handleImageError = (toolId: string) => {
    setImageErrors(prev => ({ ...prev, [toolId]: true }));
  };

  const renderToolItem = (tool: { id: string; name: string; company: string; logo?: string }, isRecent = false) => (
    <button
      key={tool.id}
      onClick={() => handleSelect(tool)}
      className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-accent transition-colors duration-150 text-left group"
    >
      <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center shrink-0">
        {tool.logo && !imageErrors[tool.id] ? (
          <img
            src={tool.logo}
            alt={tool.name}
            onError={() => handleImageError(tool.id)}
            className="w-5 h-5 object-contain"
          />
        ) : (
          <span className="text-sm font-semibold text-muted-foreground">
            {tool.name.charAt(0)}
          </span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">{tool.name}</p>
        <p className="text-xs text-muted-foreground truncate">{tool.company}</p>
      </div>
      {isRecent && (
        <button
          onClick={(e) => handleRemoveRecent(e, tool.id)}
          className="opacity-0 group-hover:opacity-100 p-1 rounded-md hover:bg-secondary transition-all duration-150"
          aria-label="Entfernen"
        >
          <X className="w-3.5 h-3.5 text-muted-foreground" />
        </button>
      )}
    </button>
  );

  return (
    <div ref={dropdownRef} className="relative flex-1 max-w-md">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <input
          ref={inputRef}
          type="text"
          placeholder="Search vibecheck"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsOpen(true)}
          className="w-full h-10 pl-10 pr-10 rounded-xl bg-secondary/60 border-0 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-all duration-200"
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground font-medium bg-background/80 px-1.5 py-0.5 rounded border border-border">
          /
        </div>
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-popover border border-border rounded-xl shadow-lg z-50 overflow-hidden">
          <ScrollArea className="max-h-80">
            {/* Recent Searches */}
            {showRecent && (
              <div className="py-2">
                <div className="px-4 py-2 flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Zuletzt gesucht
                  </span>
                </div>
                {recentSearches.map((search) => renderToolItem(search, true))}
              </div>
            )}

            {/* Search Results */}
            {query !== "" && (
              <>
                {filteredTools.length > 0 ? (
                  <div className="py-2">
                    {filteredTools.map((tool) => renderToolItem(tool))}
                  </div>
                ) : (
                  <div className="py-6 text-center text-sm text-muted-foreground">
                    Keine Ergebnisse gefunden
                  </div>
                )}
              </>
            )}

            {/* Empty state when no query and no recent */}
            {query === "" && recentSearches.length === 0 && (
              <div className="py-6 text-center text-sm text-muted-foreground">
                Beginne mit der Suche...
              </div>
            )}
          </ScrollArea>
        </div>
      )}
    </div>
  );
};

export default SearchDropdown;

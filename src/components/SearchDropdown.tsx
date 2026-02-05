import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { useTools } from "@/hooks/useTools";
import { ScrollArea } from "@/components/ui/scroll-area";

const SearchDropdown = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [imageErrors, setImageErrors] = useState<Record<string, boolean>>({});
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { data: tools } = useTools();

  const filteredTools = tools?.filter((tool) =>
    tool.name.toLowerCase().includes(query.toLowerCase())
  ) ?? [];

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

  const handleSelect = (id: string) => {
    navigate(`/detail/${id}`);
    setIsOpen(false);
    setQuery("");
  };

  const handleImageError = (toolId: string) => {
    setImageErrors(prev => ({ ...prev, [toolId]: true }));
  };

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
            {filteredTools.length > 0 ? (
              <div className="py-2">
                {filteredTools.map((tool) => (
                  <button
                    key={tool.id}
                    onClick={() => handleSelect(tool.id)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-accent transition-colors duration-150 text-left"
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
                    <div>
                      <p className="text-sm font-medium text-foreground">{tool.name}</p>
                      <p className="text-xs text-muted-foreground">{tool.company}</p>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="py-6 text-center text-sm text-muted-foreground">
                Keine Ergebnisse gefunden
              </div>
            )}
          </ScrollArea>
        </div>
      )}
    </div>
  );
};

export default SearchDropdown;

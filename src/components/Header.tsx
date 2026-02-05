import { Link } from "react-router-dom";
import { Search } from "lucide-react";

const Header = () => {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 glass-effect">
      <div className="container mx-auto px-6 h-16 flex items-center gap-6">
        <Link to="/" className="flex items-center gap-3 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground text-sm font-semibold">V</span>
          </div>
          <span className="text-lg font-semibold tracking-tight">Vibecheck</span>
        </Link>
        
        {/* Search Bar - Disabled */}
        <div className="flex-1 max-w-md">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search vibecheck"
              disabled
              className="w-full h-10 pl-10 pr-10 rounded-xl bg-secondary/60 border-0 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
            />
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground font-medium bg-background/80 px-1.5 py-0.5 rounded border border-border">
              /
            </div>
          </div>
        </div>

      </div>
    </header>
  );
};

export default Header;

"""Application constants for VibeCheck.

Defines curated entity list for controlled API costs and consistent tracking.
"""

# Fixed curated entity list for controlled API costs and consistent tracking (from PROJECT.md)
# AI Models: GPT-4o, Claude, Gemini, Llama, Mistral
# AI Tools: Cursor, Lovable, v0, GitHub Copilot, Replit
CURATED_ENTITIES = [
    {"name": "GPT-4o", "category": "model"},
    {"name": "Claude", "category": "model"},
    {"name": "Gemini", "category": "model"},
    {"name": "Llama", "category": "model"},
    {"name": "Mistral", "category": "model"},
    {"name": "Cursor", "category": "tool"},
    {"name": "Lovable", "category": "tool"},
    {"name": "v0", "category": "tool"},
    {"name": "GitHub Copilot", "category": "tool"},
    {"name": "Replit", "category": "tool"},
]

# Quick access list of entity names for AskNews API filters
ENTITY_NAMES = [e["name"] for e in CURATED_ENTITIES]

# Entity name variations mapping for normalization
# Maps common variations/mentions to canonical entity names
ENTITY_VARIATIONS = {
    "GPT-4o": [
        "gpt-4o",
        "gpt 4o",
        "gpt4o",
        "gpt-4 omni",
        "openai gpt-4o",
        "chatgpt-4o",
        "openai's gpt-4o",
        "gpt-4 turbo",
    ],
    "Claude": [
        "claude",
        "claude ai",
        "anthropic claude",
        "claude 3",
        "claude 3.5",
        "claude sonnet",
        "claude opus",
        "claude haiku",
        "anthropic's claude",
    ],
    "Gemini": [
        "gemini",
        "google gemini",
        "gemini pro",
        "gemini ultra",
        "gemini advanced",
        "gemini ai",
        "google's gemini",
        "bard gemini",
    ],
    "Llama": [
        "llama",
        "meta llama",
        "llama 2",
        "llama 3",
        "llama 3.1",
        "llama 3.2",
        "llama 3.3",
        "meta's llama",
        "meta ai llama",
    ],
    "Mistral": [
        "mistral",
        "mistral ai",
        "mistral 7b",
        "mistral large",
        "mistral medium",
        "mistral small",
        "mixtral",
        "mistral's models",
    ],
    "Cursor": [
        "cursor",
        "cursor ai",
        "cursor editor",
        "cursor ide",
        "cursor.sh",
        "cursor.so",
        "anysphere cursor",
    ],
    "Lovable": [
        "lovable",
        "lovable.dev",
        "lovable ai",
        "gptengineer",
        "gpt engineer",
        "gpt-engineer",
    ],
    "v0": [
        "v0",
        "v0.dev",
        "vercel v0",
        "v0 by vercel",
        "v zero",
        "vercel's v0",
    ],
    "GitHub Copilot": [
        "github copilot",
        "copilot",
        "gh copilot",
        "github's copilot",
        "copilot x",
        "copilot chat",
        "microsoft copilot",
    ],
    "Replit": [
        "replit",
        "repl.it",
        "replit ai",
        "replit ghostwriter",
        "ghostwriter",
        "replit agent",
    ],
}

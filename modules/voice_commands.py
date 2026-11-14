PAGE_COMMANDS = {
    "command center": "Command Center",
    "home": "Command Center",
    "go home": "Command Center",
    "dashboard": "Command Center",
    "market information": "Command Center",
    "market info": "Command Center",
    "stock intelligence": "Stock Intelligence",
    "stock analysis": "Stock Intelligence",
    "stocks": "Stock Intelligence",
    "market screener": "Market Screener",
    "stock screener": "Market Screener",
    "screener": "Market Screener",
    "backtesting": "Backtesting Lab",
    "backtesting lab": "Backtesting Lab",
    "strategy research": "Backtesting Lab",
    "strategy lab": "Backtesting Lab",
    "galaxy radar": "Galaxy Radar",
    "radar": "Galaxy Radar",
    "portfolio": "Portfolio Analytics",
    "portfolio analytics": "Portfolio Analytics",
    "my portfolio": "Portfolio Analytics",
    "study": "Study Studio",
    "study studio": "Study Studio",
    "study assistant": "Study Studio",
    "homework assistant": "Study Studio",
    "my homework assistant": "Study Studio",
    "homework": "Study Studio",
    "tutor": "Study Studio",
    "system information": "System Information",
    "system settings": "System Information",
    "settings": "System Information",
}


def parse_voice_command(transcript: str, current_page: str) -> tuple[str, str]:
    original = " ".join(str(transcript).strip().split())
    normalized = original.casefold()
    if not normalized:
        return "asset", ""

    for phrase, destination in PAGE_COMMANDS.items():
        if normalized in {
            phrase,
            f"open {phrase}",
            f"open the {phrase}",
            f"go to {phrase}",
            f"go to the {phrase}",
            f"show {phrase}",
            f"show my {phrase}",
            f"navigate to {phrase}",
        }:
            return "navigate", destination

    for prefix in ("research ", "analyze ", "look up ", "lookup "):
        if normalized.startswith(prefix):
            query = original[len(prefix):].strip()
            if query:
                return "research", query

    if current_page == "Study Studio":
        return "study", original
    return "asset", original

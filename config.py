import os
import sys
from pathlib import Path

# Resolve the data directory (DB + screenshots) to a fixed, installation-wide
# location rather than "next to the running exe" — the service EXE and the
# dashboard EXE live in different install subfolders, so anchoring to their
# own directory would make them read/write two different databases. Never
# use the process' current working directory either, since a Windows Service
# or a desktop-shortcut launch won't have the project folder as CWD.
if getattr(sys, "frozen", False):
    _DATA_DIR = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "AIMonitor" / "data"
else:
    _DATA_DIR = Path(__file__).resolve().parent / "data"

# AI domains to monitor - extend as needed
AI_DOMAINS = [
    # Major AI Chatbots
    "chat.openai.com",
    "chatgpt.com",
    "openai.com",
    "claude.ai",
    "anthropic.com",
    "gemini.google.com",
    "bard.google.com",
    "aistudio.google.com",
    # Microsoft Copilot - NICHT das nackte "bing.com": Windows 11, Edge, die
    # Widgets und die Windows-Suche kontaktieren bing.com permanent, voellig
    # ohne KI-Nutzung (war die Ursache fuer "Chrome/Bing als KI erkannt").
    "copilot.microsoft.com",
    "bing.com/chat",
    "bing.com/copilot",
    # AI Search
    "perplexity.ai",
    "you.com",
    "phind.com",
    "kagi.com",
    # Other AI Services
    "mistral.ai",
    "chat.mistral.ai",
    "groq.com",
    "together.ai",
    "deepseek.com",
    "chat.deepseek.com",
    "grok.x.ai",
    "x.ai",
    "poe.com",
    "character.ai",
    "meta.ai",
    "llama.meta.com",
    "huggingface.co",
    "replicate.com",
    "cohere.com",
    "writesonic.com",
    "jasper.ai",
    "copy.ai",
    # Coding AI
    "cursor.sh",
    "cursor.so",
    "codeium.com",
    "tabnine.com",
    "v0.dev",
    "bolt.new",
    "lovable.dev",
    "replit.com",
    "copilot.github.com",
    "aider.chat",
    "continue.dev",
    "windsurf.com",
    # GitHub Copilot - actual API endpoints (NOT github.com/... paths, those
    # never appear in a connection hostname and never matched anything)
    "copilot-proxy.githubusercontent.com",
    "copilot-telemetry.githubusercontent.com",
    "githubcopilot.com",
    "individual.githubcopilot.com",
    "business.githubcopilot.com",
    "enterprise.githubcopilot.com",
    # JetBrains AI Assistant (Grazie platform)
    "grazie.ai",
    "jetbrains.ai",
    # Amazon Q Developer / CodeWhisperer
    "codewhisperer",
    "amazon-q",
    # Sourcegraph Cody
    "sourcegraph.com",
    "cody-gateway.sourcegraph.com",
    # Supermaven
    "supermaven.com",
    # Image AI
    "midjourney.com",
    "stability.ai",
    "ideogram.ai",
    "leonardo.ai",
    "runwayml.com",
    # Additional
    "inflection.ai",
    "coze.com",
    "dify.ai",
    "n8n.io",
]

# Local AI process names. Diese werden gegen den *exakten* Prozess-/Datei-
# namen geprueft (ohne .exe), NICHT als Teilstring gegen den ganzen Pfad -
# sonst wuerde z.B. "jan" jeden Prozess des Windows-Benutzers "Jan" als
# KI-Programm melden (Pfad C:\Users\Jan\...).
AI_PROCESSES = [
    # AI Desktop Apps
    "claude",           # Claude Desktop App (Anthropic)
    "chatgpt",          # ChatGPT Desktop App (OpenAI)
    "copilot",          # Microsoft Copilot App
    "perplexity",       # Perplexity Desktop
    "cursor",           # Cursor AI IDE
    "windsurf",         # Windsurf AI IDE
    "supermaven",       # Supermaven autocomplete
    # Local LLM Runtimes
    "ollama",
    "ollama_llama_server",
    "lmstudio",
    "lm studio",
    "jan",
    "koboldcpp",
    "koboldcpp_nocuda",
    "gpt4all",
    "text-generation-webui",
    "oobabooga",
    "localai",
    "llamafile",
    "llm",
    "comfyui",
    "stable-diffusion-webui",
    "automatic1111",
    "pinokio",
]

# Keywords checked against window titles to catch self-built AI apps (e.g.
# compiled with Flutter/Electron) whose executable name isn't in AI_PROCESSES.
AI_WINDOW_KEYWORDS = [
    "chatgpt", "gpt", "claude", "gemini", "copilot", "perplexity",
    "openai", "anthropic", "ki-assistent", "ki assistent", "ai assistant",
    "ai chat", "ki chat", "chatbot", "llm",
]

# Clipboard patterns that suggest AI-generated text (German + English)
AI_CLIPBOARD_PATTERNS = [
    "as an ai", "as an ai language model", "i'm an ai",
    "ich bin eine ki", "als ki-assistent", "als sprachmodell",
    "als großes sprachmodell", "als ki bin ich",
    "certainly! ", "certainly,",
    "of course! ", "absolutely! ",
    "i'd be happy to help",
    "here's a comprehensive",
    "here is a comprehensive",
    "natürlich! ", "selbstverständlich! ",
    "gerne helfe ich",
    "## ", "### ",  # Markdown headers (common in AI output)
]

# Nach welcher Zeit dieselbe App / Domain / URL als *neue* Nutzung gilt und
# erneut protokolliert wird. Innerhalb dieses Fensters zaehlt wiederholte
# Aktivitaet als ein Ereignis; danach entsteht ein neuer Eintrag - so wird
# auch mehrfache Nutzung derselben laufenden Sitzung sichtbar (mit zeitlicher
# Luecke dazwischen). Kleiner = jede Nutzung einzeln (laengere Liste),
# groesser = weniger Wiederholungs-Eintraege.
REDETECT_AFTER = 300            # seconds (5 Minuten)

# Monitoring intervals
NETWORK_CHECK_INTERVAL = 8       # seconds
PROCESS_CHECK_INTERVAL = 10      # seconds
BROWSER_CHECK_INTERVAL = 20      # seconds
CLIPBOARD_CHECK_INTERVAL = 4     # seconds

# Screenshots on detection
SCREENSHOT_ON_DETECTION = True

# Database file (shared between monitor and viewer)
DB_PATH = str(_DATA_DIR / "ai_monitor.db")

# Screenshot directory
SCREENSHOT_DIR = str(_DATA_DIR / "screenshots")

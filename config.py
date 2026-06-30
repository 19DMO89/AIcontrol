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
    # Microsoft AI
    "copilot.microsoft.com",
    "bing.com",
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
    "github.com/features/copilot",
    "copilot.github.com",
    "aider.chat",
    "continue.dev",
    "windsurf.com",
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

# Local AI process names (executables)
AI_PROCESSES = [
    # AI Desktop Apps
    "claude",           # Claude Desktop App (Anthropic)
    "chatgpt",          # ChatGPT Desktop App (OpenAI)
    "copilot",          # Microsoft Copilot App
    "perplexity",       # Perplexity Desktop
    "cursor",           # Cursor AI IDE
    "windsurf",         # Windsurf AI IDE
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

# Monitoring intervals
NETWORK_CHECK_INTERVAL = 8       # seconds
PROCESS_CHECK_INTERVAL = 10      # seconds
BROWSER_CHECK_INTERVAL = 20      # seconds
CLIPBOARD_CHECK_INTERVAL = 4     # seconds

# Screenshots on detection
SCREENSHOT_ON_DETECTION = True

# Database file (shared between monitor and viewer)
DB_PATH = "ai_monitor.db"

# Screenshot directory
SCREENSHOT_DIR = "screenshots"

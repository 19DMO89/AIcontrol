import os
import sys
from pathlib import Path

# Single source of truth for the version. Shown in the dashboard/login UI and
# read (via regex or the bundled VERSION.txt) by Install-AIMonitor.ps1 for the
# "Apps & Features" entry. Bump this on every release.
VERSION = "3.2.0"

# Default UI / event language ("en" or "de"). The active language is stored
# per installation in the database (settings table) and can be switched in
# the dashboard; this is only the value used before anything is stored.
DEFAULT_LANGUAGE = "en"

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

# ─────────────────────────────────────────────────────────────────────────────
# AI domains to monitor.
#
# IMPORTANT - what a domain list can and cannot do: this is a blocklist, and a
# blocklist of AI services is never complete. New models and front-ends appear
# weekly, any "bring your own key" chat client reaches all of them, and a
# browser using DNS-over-HTTPS hides the lookups from the DNS-cache monitor
# entirely. The only control that covers "every model in the world" is the
# reverse: an ALLOW-list at the competition firewall/proxy (only approved
# hosts resolve, everything else is dead). Treat this list as the audit log
# that catches the careless and documents attempts - not as the lock.
#
# Matching is on a real label boundary ("x.ai" matches "api.x.ai" but not
# "climax.airlines.com"); an entry containing "/" is a plain substring test
# against browser-history URLs (never against a bare connection hostname).
# ─────────────────────────────────────────────────────────────────────────────
AI_DOMAINS = [
    # ── OpenAI ──────────────────────────────────────────────────────────────
    "chat.openai.com",
    "chatgpt.com",
    "openai.com",
    "api.openai.com",
    "platform.openai.com",
    "sora.com",
    "sora.chatgpt.com",
    "operator.chatgpt.com",
    "oai.azure.com",
    "openai.azure.com",
    # ── Anthropic (Claude) ──────────────────────────────────────────────────
    "claude.ai",
    "claude.com",
    "anthropic.com",
    "api.anthropic.com",
    "console.anthropic.com",
    # ── Google (Gemini / AI Studio / etc.) ──────────────────────────────────
    "gemini.google.com",
    "bard.google.com",
    "aistudio.google.com",
    "makersuite.google.com",
    "notebooklm.google.com",
    "generativelanguage.googleapis.com",
    "labs.google",
    "aitestkitchen.withgoogle.com",
    "deepmind.google",
    # ── Microsoft Copilot ───────────────────────────────────────────────────
    # NOT bare "bing.com": Windows 11, Edge, the widgets and Windows Search
    # all contact bing.com constantly with zero AI use (that was the cause of
    # the old "Chrome/Bing detected as AI" false positives).
    "copilot.microsoft.com",
    "m365.cloud.microsoft",
    "bing.com/chat",
    "bing.com/copilot",
    "designer.microsoft.com",
    # ── Meta ────────────────────────────────────────────────────────────────
    "meta.ai",
    "llama.meta.com",
    "llama.com",
    "ai.meta.com",
    # ── xAI (Grok) ──────────────────────────────────────────────────────────
    "x.ai",
    "grok.com",
    "grok.x.ai",
    # ── Other western labs ──────────────────────────────────────────────────
    "mistral.ai",
    "chat.mistral.ai",
    "cohere.com",
    "cohere.ai",
    "ai21.com",
    "reka.ai",
    "inflection.ai",
    "writer.com",
    "watsonx.ai",
    "build.nvidia.com",
    "nvidia.com/nim",
    "aws.amazon.com/bedrock",
    "q.aws.amazon.com",
    "partyrock.aws",
    # ── AI search & assistant front-ends ────────────────────────────────────
    "perplexity.ai",
    "you.com",
    "phind.com",
    "kagi.com",
    "poe.com",
    "character.ai",
    "t3.chat",
    "pi.ai",
    "heypi.com",
    "duck.ai",                   # DuckDuckGo AI Chat (proxy for GPT/Claude/Llama)
    "duckduckgo.com/aichat",
    "huggingface.co",            # incl. huggingface.co/chat and Spaces
    "hf.co",
    "lmarena.ai",                # LMArena / Chatbot Arena (all frontier models)
    "chat.lmsys.org",
    "chatbotarena",
    "genspark.ai",
    "felo.ai",
    "komo.ai",
    "andisearch.com",
    "exa.ai",
    "monica.im",                 # "Monica" all-in-one AI sidebar
    "sider.ai",
    "maxai.me",
    "getmerlin.in",              # Merlin AI sidebar
    "harpa.ai",
    "theb.ai",
    "deepai.org",
    "flowgpt.com",
    "forefront.ai",
    "typingmind.com",
    "chatbotapp.ai",
    "chatgot.io",
    "nano-gpt.com",
    # ── Chinese AI services (consumer chat + the cloud API endpoints their
    #    apps and SDKs call - a competition PC has no legitimate reason to
    #    reach any of these) ────────────────────────────────────────────────
    "deepseek.com",
    "chat.deepseek.com",
    "api.deepseek.com",
    "qwen.ai",                   # Alibaba Qwen (chat.qwen.ai)
    "chat.qwen.ai",
    "qwenlm.ai",
    "tongyi.aliyun.com",         # Tongyi Qianwen
    "tongyi.com",
    "dashscope.aliyuncs.com",    # Alibaba DashScope API (Qwen)
    "bailian.console.aliyun.com",
    "modelscope.cn",
    "lingma.aliyun.com",         # Alibaba Tongyi Lingma (coding)
    "chatglm.cn",                # Zhipu GLM / ChatGLM
    "zhipuai.cn",
    "zhipuai.com",
    "bigmodel.cn",               # Zhipu API (open.bigmodel.cn)
    "z.ai",                      # Zhipu international brand
    "kimi.com",                  # Moonshot Kimi
    "kimi.moonshot.cn",
    "moonshot.cn",
    "api.moonshot.ai",
    "doubao.com",                # ByteDance Doubao
    "volces.com",                # Volcano Engine (ByteDance) - ark.*.volces.com
    "volcengine.com",
    "coze.com",                  # ByteDance Coze (agent builder)
    "coze.cn",
    "marscode.com",              # ByteDance MarsCode (coding)
    "trae.ai",                   # ByteDance Trae IDE
    "jimeng.jianying.com",       # ByteDance Jimeng (image/video)
    "dreamina.com",
    "cici.com",                  # ByteDance Cici (Doubao international)
    "gauth.com",                 # ByteDance Gauth (homework AI)
    "gauthmath.com",
    "yiyan.baidu.com",           # Baidu Ernie / Wenxin Yiyan
    "ernie.baidu.com",
    "wenxin.baidu.com",
    "qianfan.baidubce.com",      # Baidu Qianfan API
    "aip.baidubce.com",
    "comate.baidu.com",          # Baidu Comate (coding)
    "hunyuan.tencent.com",       # Tencent Hunyuan
    "yuanbao.tencent.com",       # Tencent Yuanbao (consumer app)
    "hunyuan.cloud.tencent.com",
    "xinghuo.xfyun.cn",          # iFlytek Spark
    "spark.xfyun.cn",
    "xf-yun.com",
    "baichuan-ai.com",           # Baichuan
    "lingyiwanwu.com",           # 01.AI / Yi
    "01.ai",
    "minimaxi.com",              # MiniMax
    "minimax.io",
    "minimax.chat",
    "hailuoai.com",              # MiniMax Hailuo (video)
    "hailuoai.video",
    "stepfun.com",               # StepFun
    "sensenova.cn",              # SenseTime SenseChat / SenseNova
    "sensetime.com",
    "manus.im",                  # Manus (autonomous agent)
    "tiangong.cn",               # Kunlun Tiangong / SkyWork
    "skywork.ai",
    "siliconflow.cn",            # SiliconFlow (Chinese model aggregator)
    "siliconflow.com",
    "chat.360.cn",               # 360 AI
    "ai.360.cn",
    "zhida.zhihu.com",           # Zhihu Zhida
    "vidu.com",                  # Shengshu Vidu (video)
    "seaart.ai",
    "liblib.art",
    "question.ai",               # homework AI (Chinese-owned)
    # ── Model aggregators / inference APIs / GPU rental (one key unlocks
    #    every frontier model, so a single gap defeats the brand list) ──────
    "openrouter.ai",
    "together.ai",
    "together.xyz",
    "groq.com",
    "fireworks.ai",
    "deepinfra.com",
    "replicate.com",
    "hyperbolic.xyz",
    "novita.ai",
    "fal.ai",
    "lepton.ai",
    "nebius.ai",
    "targon.com",
    "anyscale.com",
    "baseten.co",
    "modal.com",
    "runpod.io",
    "vast.ai",
    "lambdalabs.com",
    "lambda.chat",
    "cerebras.ai",
    "sambanova.ai",
    "aimlapi.com",
    "unify.ai",
    "portkey.ai",
    "requesty.ai",
    "glama.ai",
    "edenai.co",
    # ── Coding AI ───────────────────────────────────────────────────────────
    "cursor.sh",
    "cursor.so",
    "cursor.com",
    "codeium.com",
    "windsurf.com",
    "windsurf.ai",
    "tabnine.com",
    "v0.dev",
    "v0.app",
    "bolt.new",
    "lovable.dev",
    "replit.com",
    "aider.chat",
    "continue.dev",
    "cline.bot",
    "roocode.com",
    "zed.dev",
    "pear.ai",
    "devin.ai",
    "cognition.ai",
    "factory.ai",
    "qodo.ai",
    "codium.ai",
    "refact.ai",
    "augmentcode.com",
    "sweep.dev",
    "codegen.com",
    "blackbox.ai",
    "useblackbox.io",
    "codegpt.co",
    "pieces.app",
    "mutable.ai",
    "double.bot",
    "tabbyml.com",
    "codegeex.cn",
    "fittentech.com",
    "copilot.github.com",
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
    # ── Image / video / audio generation ────────────────────────────────────
    "midjourney.com",
    "stability.ai",
    "dreamstudio.ai",
    "clipdrop.co",
    "ideogram.ai",
    "leonardo.ai",
    "runwayml.com",
    "runway.com",
    "pika.art",
    "lumalabs.ai",
    "klingai.com",
    "firefly.adobe.com",
    "playground.com",
    "playgroundai.com",
    "civitai.com",
    "tensor.art",
    "getimg.ai",
    "krea.ai",
    "recraft.ai",
    "bfl.ai",
    "blackforestlabs.ai",
    "openart.ai",
    "nightcafe.studio",
    "elevenlabs.io",
    "suno.com",
    "suno.ai",
    "udio.com",
    "murf.ai",
    "play.ht",
    "descript.com",
    "heygen.com",
    "synthesia.io",
    "d-id.com",
    "captions.ai",
    # ── Agent / automation platforms ────────────────────────────────────────
    "dify.ai",
    "n8n.io",
    "flowiseai.com",
    "relevanceai.com",
    "lindy.ai",
    "crewai.com",
    "multion.ai",
    "adept.ai",
    "hcompany.ai",
    "convergence.ai",
    "langflow.org",
    "agpt.co",
    # ── Writing / research / study aids ─────────────────────────────────────
    # TRIM this section if your skill explicitly permits translation or
    # grammar tools - these are broad and some have non-AI uses.
    "jasper.ai",
    "copy.ai",
    "writesonic.com",
    "rytr.me",
    "sudowrite.com",
    "quillbot.com",
    "wordtune.com",
    "hyperwriteai.com",
    "textcortex.com",
    "grammarly.com",
    "deepl.com/write",
    "novelai.net",
    "gamma.app",
    "tome.app",
    "otter.ai",
    "fireflies.ai",
    "fathom.video",
    "elicit.com",
    "consensus.app",
    "scite.ai",
    "chatpdf.com",
    "humata.ai",
    "quizlet.com/go/ai",
    "brainly.com",
    "studyx.ai",
    "smodin.io",
    "caktus.ai",
    "knowunity.com",
    "studdy.ai",
    "turbolearn.ai",
    "studyfetch.com",
    # ── Local model download / self-host project sites ──────────────────────
    "ollama.com",
    "ollama.ai",
    "lmstudio.ai",
    "jan.ai",
    "gpt4all.io",
    "nomic.ai",
    "localai.io",
    "koboldai.org",
    "pinokio.computer",
    "backyard.ai",
    "faraday.dev",
    "msty.app",
    "anythingllm.com",
    "librechat.ai",
    "lobehub.com",
    "openwebui.com",
    "vllm.ai",
    "big-agi.com",
]

# Local AI process names. Matched against the *exact* process / file name
# (without .exe), NOT as a substring of the full path - otherwise "jan" would
# flag every process of a Windows user named "Jan" (path C:\Users\Jan\...).
AI_PROCESSES = [
    # ── AI chat desktop apps ────────────────────────────────────────────────
    "claude",           # Claude desktop app (Anthropic)
    "chatgpt",          # ChatGPT desktop app (OpenAI)
    "copilot",          # Microsoft Copilot app
    "perplexity",       # Perplexity Desktop
    "grok",             # Grok desktop app (xAI)
    "deepseek",         # DeepSeek desktop app
    "doubao",           # ByteDance Doubao desktop app
    "kimi",             # Moonshot Kimi desktop app
    "yuanbao",          # Tencent Yuanbao desktop app
    "tongyi",           # Alibaba Tongyi desktop app
    "cici",             # ByteDance Cici
    # ── AI coding IDEs / assistants ─────────────────────────────────────────
    "cursor",           # Cursor AI IDE
    "windsurf",         # Windsurf AI IDE
    "trae",             # ByteDance Trae IDE
    "pearai",           # PearAI
    "supermaven",       # Supermaven autocomplete
    "tabby-agent",      # TabbyML
    "aider",            # aider CLI
    "codegeex",
    # ── Multi-model desktop clients (bring-your-own API key - reach every
    #    provider; the process name helps when traffic is hidden by DoH) ────
    "chatbox",
    "cherry studio",
    "cherrystudio",
    "anythingllm",
    "librechat",
    "lm studio",
    "lmstudio",
    "msty",
    "witsy",
    "chatwise",
    "boltai",
    "typingmind",
    "jan",
    "enchanted",
    "lobehub",
    "lobe-chat",
    "big-agi",
    "sillytavern",
    "backyard",         # Backyard AI (ex-Faraday)
    "faraday",
    # ── Local LLM runtimes / servers ───────────────────────────────────────
    "ollama",
    "ollama app",
    "ollama_llama_server",
    "koboldcpp",
    "koboldcpp_nocuda",
    "kobold",
    "croco",            # croco.cpp / koboldcpp fork
    "gpt4all",
    "gpt4all-chat",
    "text-generation-webui",
    "oobabooga",
    "localai",
    "llamafile",
    "llm",              # Simon Willison's `llm` CLI
    "llama-server",     # llama.cpp
    "llama-cli",
    "llama-box",
    "llama-run",
    "llamacpp",
    "llama_cpp",
    "llama.cpp",
    "vllm",
    "sglang",
    "lmdeploy",
    "aphrodite",        # aphrodite-engine
    "xinference",
    "xinference-local",
    "gpustack",
    "nexa",
    "jlama",
    "cortex-server",    # Jan's cortex.cpp server
    "ramalama",
    "mlc_chat",
    "mlc-llm",
    "open-webui",
    "openwebui",
    "tabby",            # TabbyML self-hosted coding assistant
    # ── Local image / video generation ─────────────────────────────────────
    "comfyui",
    "stable-diffusion-webui",
    "automatic1111",
    "fooocus",
    "invokeai",
    "pinokio",
]

# Keywords checked against window titles to catch self-built AI apps (e.g.
# compiled with Flutter/Electron) whose executable name isn't in AI_PROCESSES.
AI_WINDOW_KEYWORDS = [
    "chatgpt", "gpt", "claude", "gemini", "copilot",
    "perplexity", "openai", "anthropic", "grok",
    "ki-assistent", "ki assistent", "ai assistant",
    "ai chat", "ki chat", "chatbot", "llm",
    # Chinese models (Latin + native product names)
    "deepseek", "qwen", "tongyi", "kimi", "doubao", "hunyuan", "yuanbao",
    "ernie", "chatglm", "文心一言", "通义千问", "豆包", "混元", "元宝", "智谱",
    # Local model families / runtimes (window titles of local chat UIs)
    "llama", "mistral", "mixtral", "gemma", "phi-3", "phi-4", "qwq",
    "ollama", "koboldai", "koboldcpp", "oobabooga", "text generation web ui",
    "lm studio", "gpt4all", "localai", "open webui", "anythingllm",
    "jan.ai", "sillytavern", "faraday", "backyard ai",
    # Local image generation UIs
    "stable diffusion", "comfyui", "automatic1111", "fooocus", "invokeai",
]

# Clipboard: the "does this text look AI-generated?" check now lives in
# aitext.py (a scoring heuristic, not a flat substring list) and runs inside
# AISessionAgent.exe - the service in Session 0 has no access to the
# interactive clipboard at all, so it could never see what was copied.
CLIPBOARD_CHECK_INTERVAL = 3     # seconds (session agent)
# Minimum clipboard length worth analysing - short copies (paths, names,
# single lines, spreadsheet cells) are skipped outright.
CLIPBOARD_MIN_CHARS = 200
# aitext score at/above which a clipboard entry is logged (as a *warning*,
# not critical - it is circumstantial). Lower = more sensitive / more noise.
CLIPBOARD_AI_SCORE = 4

# ─────────────────────────────────────────────────────────────────────────────
# Local-model detection (monitor_local_ai in monitor.py)
#
# Process-name matching alone (AI_PROCESSES) is trivially defeated - rename
# the binary, or run the model from "python server.py". These three signals
# do not depend on the executable's name:
#   1. a known local-inference server port in the LISTEN state
#   2. an AI-model marker on the process command line
#   3. downloaded model weights present on disk
# ─────────────────────────────────────────────────────────────────────────────

# Ports flagged on sight - specific to one local-LLM / diffusion tool.
LOCAL_AI_PORTS_STRONG = {
    11434: "Ollama",
    1234:  "LM Studio",
    5001:  "KoboldCpp",
    4891:  "GPT4All API server",
    1337:  "Jan API server",
    39281: "Jan / Cortex",
    8188:  "ComfyUI",
    11029: "TabbyML",
    2242:  "Aphrodite Engine",
    5005:  "text-generation-webui (API)",
}
# Ports also used by ordinary dev servers - only flagged when the owning
# process itself looks AI-related (name in AI_PROCESSES or a cmdline marker).
LOCAL_AI_PORTS_WEAK = {
    8080: "llama.cpp / LocalAI / Open WebUI",
    8000: "vLLM / llama.cpp server",
    7860: "Gradio UI (oobabooga / SD WebUI)",
    7865: "Fooocus",
    9090: "InvokeAI",
    3000: "Open WebUI",
    5000: "text-generation-webui",
    1338: "Jan",
}

# Substrings that mark a command line as running / fetching a local model,
# whatever the executable is called. Kept deliberately specific to avoid
# flagging ordinary ML or dev work.
LOCAL_AI_CMDLINE_MARKERS = [
    ".gguf", ".ggml", ".safetensors",
    "llama_cpp", "llama-cpp", "llama.cpp", "llamacpp", "llama-server",
    "llama-cli", "llama-run", "-hf-repo", "--hf-repo", "--hf-file",
    "ollama serve", "ollama run", "/ollama", "\\ollama",
    "koboldcpp", "kobold.cpp",
    "text-generation-webui", "server.py --model", "one_click.py",
    "vllm serve", "vllm.entrypoints", "-m vllm", "python -m vllm",
    "sglang.launch", "-m sglang", "lmdeploy serve", "-m lmdeploy",
    "aphrodite run", "-m aphrodite", "exllamav2", "exllama",
    "auto_gptq", "autoawq", "ctransformers",
    "text_generation_server", "text-generation-launcher",
    "gpt4all", "localai", "llamafile", "mlc_chat", "mlc_llm", "mlc-llm",
    "huggingface-cli download", "hf_hub_download", "snapshot_download",
    "--model-path", "--model_name_or_path", "--ckpt", "--checkpoint-path",
    "stable-diffusion", "stable_diffusion", "sd_webui", "comfyui",
    "automatic1111", "fooocus", "invokeai",
]

# Where model weights land, and what counts as "a model is on this machine".
# Only unambiguous LLM/diffusion weight formats - .bin/.pt are far too common
# for other things to scan for.
LOCAL_AI_MODEL_EXTS = (".gguf", ".ggml", ".safetensors")
LOCAL_AI_MODEL_MIN_BYTES = 200 * 1024 * 1024   # 200 MB
# Extra folders (under each real user profile) scanned shallowly for the
# extensions above, on top of the tool-specific caches handled in code.
LOCAL_AI_MODEL_SCAN_DIRS = ["Downloads", "Desktop", "Documents", "models"]

# How often the local-model monitor runs its port/cmdline scan, and (less
# often) the disk scan.
LOCAL_AI_CHECK_INTERVAL = 12          # seconds
LOCAL_AI_DISK_SCAN_EVERY = 25         # every Nth cycle (~5 min at 12s)

# How long before the same app / domain / URL counts as a *new* use and is
# logged again. Within this window repeated activity counts as one event;
# after it a new entry is created - so repeated use of the same running
# session (with a gap in between) stays visible. Smaller = every use listed
# separately (longer list), larger = fewer repeat entries.
REDETECT_AFTER = 300            # seconds (5 minutes)

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

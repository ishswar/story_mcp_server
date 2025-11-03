import os
import logging
from datetime import datetime
import asyncio
import base64
import json

from fastmcp import FastMCP, Context
from fastmcp.server.dependencies import get_http_request, get_http_headers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Configure logging with session-aware formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('story_server.log', encoding='utf-8')  # File output
    ]
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────
# Enhanced Session Logging with Fallback Support
# ─────────────────────────────────────────────────────────────────────

def get_tracking_id(ctx: Context) -> str:
    """Get a reliable tracking ID from context, with fallback to request ID."""
    if ctx.session_id:
        return f"session-{ctx.session_id}"
    elif ctx.request_id:
        return f"request-{ctx.request_id}"
    else:
        return f"unknown-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

def get_session_logger(ctx: Context) -> logging.LoggerAdapter:
    """Get a logger that includes tracking ID in all log messages."""
    tracking_id = get_tracking_id(ctx)
    # Include both session and request info for debugging
    extra = {
        'tracking_id': tracking_id,
        'session_id': ctx.session_id or 'no-session',
        'request_id': ctx.request_id or 'no-request'
    }
    
    class DetailedLoggerAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            return f"[{self.extra['tracking_id']}] {msg}", kwargs
    
    return DetailedLoggerAdapter(logger, extra)

async def log_session_info(ctx: Context, operation: str):
    """Log detailed session information for debugging."""
    session_logger = get_session_logger(ctx)
    
    # Log session state
    if ctx.session_id:
        await ctx.info(f"{operation}: Active session {ctx.session_id}")
        session_logger.info(f"{operation}: Session active")
    else:
        await ctx.warning(f"{operation}: No session ID - likely stateless mode or STDIO transport")
        session_logger.warning(f"{operation}: No session (stateless/STDIO)")
    
    # Log additional context
    session_logger.debug(f"Request ID: {ctx.request_id}, Client ID: {ctx.client_id}")

# ─────────────────────────────────────────────────────────────────────
# Transport config
# ─────────────────────────────────────────────────────────────────────
transport_type = os.getenv("TRANSPORT", "http")  # "http" or "sse"
port = int(os.getenv("PORT", "8082"))

# Check if we should use stateless mode (for OpenAI compatibility)
stateless_mode = os.getenv("STATELESS_HTTP", "false").lower() == "true"

logger.info(f"MCP Story Server starting with {transport_type.upper()} transport on port {port}...")
if stateless_mode:
    logger.info("Running in STATELESS mode (OpenAI compatible)")
else:
    logger.info("Running in STATEFUL mode (session persistence enabled)")

# ─────────────────────────────────────────────────────────────────────
# Server metadata
# ─────────────────────────────────────────────────────────────────────
SERVER_NAME = "StoryServer"
SERVER_VERSION = "2.2.0"  # Updated version
SERVER_TITLE = "StoryServer MCP"
SERVER_INSTRUCTIONS = (
    "StoryServer exposes simple tools to list characters, fetch backstories, "
    "and save/read markdown stories. Includes session debugging capabilities."
)

# Create FastMCP instance with stateless mode if needed
try:
    mcp = FastMCP(
        name=SERVER_NAME,
        instructions=SERVER_INSTRUCTIONS,
        stateless_http=stateless_mode  # Enable stateless mode if configured
    )
    logger.info(
        f"Successfully created FastMCP server - Version: {SERVER_VERSION}, "
        f"Stateless: {stateless_mode}"
    )
except TypeError:
    logger.warning("Failed to set stateless_http - using fallback for older fastmcp version")
    mcp = FastMCP(name=SERVER_NAME)

# ─────────────────────────────────────────────────────────────────────
# HTTP Header Logging Helper
# ─────────────────────────────────────────────────────────────────────

def log_http_headers():
    """Log all incoming HTTP headers using FastMCP's dependency system."""
    try:
        # Get headers from the current request context
        headers = get_http_headers(include_all=True)
        request = get_http_request()

        logger.info("=" * 80)
        logger.info(f"📥 Incoming MCP Request")
        logger.info("-" * 80)
        logger.info("HTTP Headers:")

        # Log each header
        if headers:
            for header_name, header_value in headers.items():
                logger.info(f"  {header_name}: {header_value}")
        else:
            logger.info("  (No headers available - possible STDIO transport)")

        logger.info("-" * 80)

        if request:
            logger.info(f"Client: {request.client.host if request.client else 'Unknown'}")
            logger.info(f"Method: {request.method}")
            logger.info(f"Path: {request.url.path}")
            logger.info(f"Query: {request.url.query if request.url.query else 'None'}")
        else:
            logger.info("Request details: Not available (possible STDIO transport)")

        logger.info("=" * 80)
    except Exception as e:
        logger.debug(f"Could not log headers (likely STDIO transport): {e}")

# ─────────────────────────────────────────────────────────────────────
# Demo data
# ─────────────────────────────────────────────────────────────────────
CHARACTERS = {
    "Jack": {
        "backstory": "Jack is a former spy who now lives as a covert hero.",
        "superpower": "Invisibility and telepathy"
    },
    "Ram": {
        "backstory": "Ram is an ancient warrior reborn in the modern world to fight for peace.",
        "superpower": "Invincible body and immense strength"
    },
    "Robert": {
        "backstory": "Robert is a scientist who became part machine after a lab accident.",
        "superpower": "Power fused with advanced technology"
    }
}

# ─────────────────────────────────────────────────────────────────────
# Session Debugging Tools
# ─────────────────────────────────────────────────────────────────────

@mcp.tool(description="Debug session information and transport details")
async def debug_session(ctx: Context) -> dict:
    """Debug tool to understand session behavior."""
    # Log HTTP headers
    log_http_headers()

    session_logger = get_session_logger(ctx)
    
    debug_info = {
        "session_analysis": {
            "session_id": ctx.session_id,
            "session_id_type": type(ctx.session_id).__name__,
            "has_session": ctx.session_id is not None,
            "tracking_id": get_tracking_id(ctx)
        },
        "context_properties": {
            "request_id": ctx.request_id,
            "client_id": ctx.client_id,
        },
        "transport_analysis": {
            "likely_transport": "HTTP/SSE" if ctx.session_id else "STDIO/Stateless-HTTP",
            "stateless_mode_configured": stateless_mode,
            "port": port
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # Try to get HTTP headers for more info
    try:
        headers = get_http_headers(include_all=True)
        debug_info["http_headers"] = {
            "session_header": headers.get("mcp-session-id"),
            "x_session_id": headers.get("x-session-id"),
            "user_agent": headers.get("user-agent", "Unknown")
        }
    except:
        debug_info["http_headers"] = "Not available (likely STDIO transport)"
    
    session_logger.info(f"Session debug completed: {debug_info}")
    await ctx.info(f"Session debug: {debug_info}")
    
    return debug_info

# ─────────────────────────────────────────────────────────────────────
# Updated Tools with Robust Session Logging
# ─────────────────────────────────────────────────────────────────────

@mcp.tool(description="Get the list of all available character names.")
async def get_characters(ctx: Context) -> list[str]:
    # Log HTTP headers
    log_http_headers()

    session_logger = get_session_logger(ctx)
    await log_session_info(ctx, "get_characters")
    
    characters = list(CHARACTERS.keys())
    session_logger.info(f"Retrieved {len(characters)} characters: {characters}")
    await ctx.info(f"Returning {len(characters)} characters")
    
    return characters


@mcp.tool(description="Get the backstory of a specified character.")
async def get_backstory(character: str, ctx: Context) -> str:
    # Log HTTP headers
    log_http_headers()

    session_logger = get_session_logger(ctx)
    await log_session_info(ctx, f"get_backstory({character})")
    
    session_logger.info(f"Getting backstory for character: {character}")
    backstory = CHARACTERS.get(character, {}).get("backstory", "Character not found.")
    
    if backstory == "Character not found.":
        session_logger.warning(f"Character not found: {character}")
        await ctx.warning(f"Character '{character}' not found")
    else:
        session_logger.info(f"Retrieved backstory for {character}")
        await ctx.info(f"Found backstory for {character}")
    
    return backstory


@mcp.tool(description="Get the superpower of a specified character.")
async def get_superpower(character: str, ctx: Context) -> str:
    session_logger = get_session_logger(ctx)
    await log_session_info(ctx, f"get_superpower({character})")
    
    session_logger.info(f"Getting superpower for character: {character}")
    superpower = CHARACTERS.get(character, {}).get("superpower", "Character not found.")
    
    if superpower == "Character not found.":
        session_logger.warning(f"Character not found: {character}")
        await ctx.warning(f"Character '{character}' not found")
    else:
        session_logger.info(f"Retrieved superpower for {character}")
        await ctx.info(f"Found superpower for {character}")
    
    return superpower


def get_current_date() -> str:
    return datetime.now().strftime("%B %d, %Y")


def sanitize_filename(title: str) -> str:
    filename = title.replace(' ', '_').lower()
    if filename.count('_') > 3:
        filename = '_'.join(filename.split('_')[:4])
    if len(filename) > 30:
        filename = filename[:30]
    return filename + ".md"


def validate_and_truncate_jwt(token: str) -> tuple[bool, str, str]:
    """
    Validate JWT token structure and truncate for display.

    Returns:
        tuple: (is_valid, truncated_token, error_message)
    """
    if not token or token == 'N/A':
        return True, 'N/A', ''

    try:
        # JWT tokens have 3 parts separated by dots: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            logger.error(f"Invalid JWT structure: expected 3 parts, got {len(parts)}")
            return False, token[:10] + '...[INVALID]', 'Invalid JWT structure: token must have 3 parts (header.payload.signature)'

        # Try to decode the header and payload to validate base64 encoding
        try:
            # Add padding if needed for base64 decoding
            header = parts[0]
            payload = parts[1]

            # Decode header
            header_padding = '=' * (4 - len(header) % 4) if len(header) % 4 else ''
            header_decoded = base64.urlsafe_b64decode(header + header_padding)
            header_json = json.loads(header_decoded)

            # Decode payload
            payload_padding = '=' * (4 - len(payload) % 4) if len(payload) % 4 else ''
            payload_decoded = base64.urlsafe_b64decode(payload + payload_padding)
            payload_json = json.loads(payload_decoded)

            logger.info(f"JWT token validated successfully - Issuer: {payload_json.get('iss', 'unknown')}, Subject: {payload_json.get('sub', 'unknown')[:20]}...")

        except (base64.binascii.Error, json.JSONDecodeError) as e:
            logger.error(f"Failed to decode JWT token: {e}")
            return False, token[:10] + '...[INVALID]', f'Failed to decode JWT token: {str(e)}'

        # Truncate: first 10 chars ... last 10 chars
        if len(token) > 30:
            truncated = f"{token[:10]}...{token[-10:]}"
        else:
            truncated = token

        return True, truncated, ''

    except Exception as e:
        logger.error(f"Error validating JWT token: {e}")
        return False, token[:10] + '...[ERROR]', f'Error validating token: {str(e)}'


@mcp.tool(description="Save a story to a markdown file with title and creation date.")
async def save_story(title: str, content: str, ctx: Context) -> str:
    # Log HTTP headers
    log_http_headers()

    session_logger = get_session_logger(ctx)
    await log_session_info(ctx, f"save_story({title})")

    filename = sanitize_filename(title)
    date_created = get_current_date()
    session_logger.info(f"Saving story '{title}' to file: {filename}")

    # Extract headers for metadata
    try:
        headers = get_http_headers(include_all=True) or {}
    except:
        headers = {}

    # Extract specific headers (case-insensitive)
    conversation_id = headers.get('x-conversation-id', 'N/A')
    session_id_header = headers.get('x-session-id', 'N/A')
    atmosphere_token = headers.get('x-atmosphere-token', 'N/A')

    # Check if atmosphere token is missing - FAIL if not present
    if atmosphere_token == 'N/A':
        error_message = "X-Atmosphere-Token header is required but was not found in the request"
        session_logger.error(f"FAILED to save story: {error_message}")
        await ctx.error(f"Failed to save story: {error_message}")
        return f"Error: {error_message}. Story was not saved."

    # Validate and truncate JWT token
    token_valid, truncated_token, error_msg = validate_and_truncate_jwt(atmosphere_token)

    if not token_valid:
        error_message = f"Incoming atmosphere token was not correct: {error_msg}"
        session_logger.error(error_message)
        await ctx.error(f"Invalid atmosphere token: {error_msg}")
        return f"Error: {error_message}. Story was not saved."

    session_logger.info(f"Atmosphere token validated and truncated successfully")
    session_logger.info(f"Extracted headers - Conversation ID: {conversation_id}, Session ID: {session_id_header}, Token: {truncated_token}")

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(f"**Date Created:** {date_created}\n\n")
            f.write(f"**Session ID:** {ctx.session_id or 'stateless'}\n\n")
            f.write(f"**Request ID:** {ctx.request_id}\n\n")
            f.write(content)

            # Add metadata section at the bottom
            f.write("\n\n---\n\n")
            f.write("## Request Metadata\n\n")
            f.write(f"**Conversation ID:** {conversation_id}\n\n")
            f.write(f"**X-Session-ID:** {session_id_header}\n\n")
            f.write(f"**X-Atmosphere-Token:** {truncated_token}\n")

        session_logger.info(f"Successfully saved story to: {os.path.abspath(filename)}")
        await ctx.info(f"Story saved to {filename}")
        return f"Story has been saved at: {os.path.abspath(filename)}"
    except Exception as e:
        session_logger.error(f"Failed to save story '{title}': {e}")
        await ctx.error(f"Failed to save story: {e}")
        return f"Error saving story: {e}"


@mcp.tool(description="List all saved story files in markdown format.")
async def list_stories(reason: str, ctx: Context) -> list[str]:
    session_logger = get_session_logger(ctx)
    await log_session_info(ctx, f"list_stories(reason={reason})")
    
    session_logger.info(f"Listing story files - reason: {reason}")
    try:
        story_files = [f for f in os.listdir('.') if f.endswith('.md')]
        session_logger.info(f"Found {len(story_files)} story files: {story_files}")
        await ctx.info(f"Listed {len(story_files)} story files")
        return story_files
    except Exception as e:
        session_logger.error(f"Failed to list story files: {e}")
        await ctx.error(f"Failed to list stories: {e}")
        return []


@mcp.tool(description="Read the content of a specific story file.")
async def get_story(filename: str, ctx: Context) -> str:
    session_logger = get_session_logger(ctx)
    await log_session_info(ctx, f"get_story({filename})")
    
    session_logger.info(f"Reading story file: {filename}")
    if not os.path.exists(filename):
        session_logger.warning(f"Story file not found: {filename}")
        await ctx.warning(f"Story file '{filename}' not found")
        return "Story file not found."
    
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        session_logger.info(f"Successfully read story file: {filename} ({len(content)} characters)")
        await ctx.info(f"Read story from {filename}")
        return content
    except Exception as e:
        session_logger.error(f"Failed to read story file '{filename}': {e}")
        await ctx.error(f"Failed to read story: {e}")
        return f"Error reading story file: {e}"


@mcp.tool(description="Get detailed client information including MCP client details, HTTP headers, IP address, User-Agent, and operating system information")
async def get_client_info(ctx: Context) -> dict:
    """Get comprehensive client information from MCP protocol and HTTP request."""
    session_logger = get_session_logger(ctx)
    
    client_info = {
        "mcp_protocol_info": {
            "tracking_id": get_tracking_id(ctx),
            "request_id": ctx.request_id,
            "session_id": ctx.session_id,
            "client_id": ctx.client_id,
            "has_session": ctx.session_id is not None
        },
        "http_request_info": {},
        "parsed_client_details": {},
        "timestamp": datetime.now().isoformat(),
        "error": None
    }
    
    try:
        # Try to get HTTP request information
        try:
            request = get_http_request()
            
            # Basic request info
            client_info["http_request_info"]["method"] = request.method
            client_info["http_request_info"]["url"] = str(request.url)
            client_info["http_request_info"]["client_host"] = request.client.host if request.client else None
            client_info["http_request_info"]["client_port"] = request.client.port if request.client else None
            
            # Get all headers (including standard ones)
            all_headers = get_http_headers(include_all=True)

            session_logger.info(f"HTTP Headers: {all_headers}")

            client_info["http_request_info"]["headers"] = all_headers
            
            # Extract and parse User-Agent for detailed client information
            user_agent = all_headers.get("user-agent", "Unknown")
            client_info["http_request_info"]["user_agent"] = user_agent
            client_info["parsed_client_details"] = parse_user_agent_detailed(user_agent)
            
            # Session-related headers
            client_info["http_request_info"]["mcp_session_id"] = all_headers.get("mcp-session-id")
            client_info["http_request_info"]["x_session_id"] = all_headers.get("x-session-id")
            
            # Network information
            client_info["http_request_info"]["x_forwarded_for"] = all_headers.get("x-forwarded-for")
            client_info["http_request_info"]["x_real_ip"] = all_headers.get("x-real-ip")
            client_info["http_request_info"]["host"] = all_headers.get("host")

            # X-Server-Name
            client_info["http_request_info"]["x_server_name"] = all_headers.get("X-Server-Name")
            
            # MCP specific headers
            mcp_headers = {k: v for k, v in all_headers.items() if k.startswith("mcp-")}
            client_info["http_request_info"]["mcp_headers"] = mcp_headers
            
        except RuntimeError as e:
            client_info["error"] = f"No HTTP context available (likely using stdio transport): {str(e)}"
            
    except Exception as e:
        client_info["error"] = f"Error getting client info: {str(e)}"
    
    session_logger.info(f"Client info request - "
                       f"Tracking: {client_info['mcp_protocol_info']['tracking_id']}, "
                       f"Client: {client_info['parsed_client_details'].get('browser', 'Unknown')}, "
                       f"Has Session: {client_info['mcp_protocol_info']['has_session']}"
                       )
    
    await ctx.info(f"Client info retrieved with tracking ID: {get_tracking_id(ctx)}")
    
    return client_info


def parse_user_agent_detailed(user_agent: str) -> dict:
    """Parse User-Agent string to extract detailed browser/OS/device information."""
    parsed = {
        "browser": "Unknown",
        "browser_version": "Unknown", 
        "os": "Unknown",
        "os_version": "Unknown",
        "platform": "Unknown",
        "device_type": "Desktop",
        "is_mobile": False,
        "is_bot": False,
        "engine": "Unknown"
    }
    
    if not user_agent:
        return parsed
    
    ua_lower = user_agent.lower()
    
    # Check for bots/crawlers first
    bot_indicators = ["bot", "crawler", "spider", "scraper", "curl", "wget", "python", "postman"]
    if any(indicator in ua_lower for indicator in bot_indicators):
        parsed["is_bot"] = True
        parsed["device_type"] = "Bot/Tool"
        
        if "curl" in ua_lower:
            parsed["browser"] = "cURL"
        elif "postman" in ua_lower:
            parsed["browser"] = "Postman"
        elif "python" in ua_lower:
            if "requests" in ua_lower:
                parsed["browser"] = "Python Requests"
            elif "httpx" in ua_lower:
                parsed["browser"] = "Python HTTPX"
            else:
                parsed["browser"] = "Python HTTP Client"
        elif "googlebot" in ua_lower:
            parsed["browser"] = "Googlebot"
        elif "bingbot" in ua_lower:
            parsed["browser"] = "Bingbot"
    
    # Detect operating system and version
    if "windows" in ua_lower:
        parsed["os"] = "Windows"
        if "windows nt 10.0" in ua_lower:
            parsed["os_version"] = "10/11"
            parsed["platform"] = "Windows 10/11"
        elif "windows nt 6.3" in ua_lower:
            parsed["os_version"] = "8.1"
            parsed["platform"] = "Windows 8.1"
        elif "windows nt 6.1" in ua_lower:
            parsed["os_version"] = "7"
            parsed["platform"] = "Windows 7"
    elif "macintosh" in ua_lower or "mac os x" in ua_lower:
        parsed["os"] = "macOS"
        # Extract macOS version
        import re
        mac_version_match = re.search(r'mac os x ([\d_]+)', ua_lower)
        if mac_version_match:
            version = mac_version_match.group(1).replace('_', '.')
            parsed["os_version"] = version
        
        if "intel" in ua_lower:
            parsed["platform"] = "macOS Intel"
        elif "arm64" in ua_lower or "apple silicon" in ua_lower:
            parsed["platform"] = "macOS Apple Silicon"
        else:
            parsed["platform"] = "macOS"
    elif "linux" in ua_lower:
        parsed["os"] = "Linux"
        if "ubuntu" in ua_lower:
            parsed["platform"] = "Ubuntu Linux"
        elif "fedora" in ua_lower:
            parsed["platform"] = "Fedora Linux"
        elif "debian" in ua_lower:
            parsed["platform"] = "Debian Linux"
        elif "centos" in ua_lower:
            parsed["platform"] = "CentOS Linux"
    elif "android" in ua_lower:
        parsed["os"] = "Android"
        parsed["is_mobile"] = True
        parsed["device_type"] = "Mobile"
        # Extract Android version
        import re
        android_version_match = re.search(r'android ([\d\.]+)', ua_lower)
        if android_version_match:
            parsed["os_version"] = android_version_match.group(1)
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        parsed["os"] = "iOS"
        parsed["is_mobile"] = "iphone" in ua_lower
        parsed["device_type"] = "iPhone" if "iphone" in ua_lower else "iPad"
        # Extract iOS version
        import re
        ios_version_match = re.search(r'os ([\d_]+)', ua_lower)
        if ios_version_match:
            version = ios_version_match.group(1).replace('_', '.')
            parsed["os_version"] = version
            
    # Detect browser and version (if not already a bot)
    if not parsed["is_bot"]:
        if "edg/" in ua_lower or "edge/" in ua_lower:
            parsed["browser"] = "Microsoft Edge"
            parsed["engine"] = "Blink"
            # Extract Edge version
            import re
            edge_version_match = re.search(r'edg?/?([\d\.]+)', ua_lower)
            if edge_version_match:
                parsed["browser_version"] = edge_version_match.group(1)
        elif "chrome/" in ua_lower and "edg" not in ua_lower:
            parsed["browser"] = "Chrome"
            parsed["engine"] = "Blink"
            # Extract Chrome version
            import re
            chrome_version_match = re.search(r'chrome/([\d\.]+)', ua_lower)
            if chrome_version_match:
                parsed["browser_version"] = chrome_version_match.group(1)
        elif "firefox" in ua_lower:
            parsed["browser"] = "Firefox"
            parsed["engine"] = "Gecko"
            # Extract Firefox version
            import re
            firefox_version_match = re.search(r'firefox/([\d\.]+)', ua_lower)
            if firefox_version_match:
                parsed["browser_version"] = firefox_version_match.group(1)
        elif "safari" in ua_lower and "chrome" not in ua_lower:
            parsed["browser"] = "Safari"
            parsed["engine"] = "WebKit"
            # Extract Safari version
            import re
            safari_version_match = re.search(r'version/([\d\.]+)', ua_lower)
            if safari_version_match:
                parsed["browser_version"] = safari_version_match.group(1)
        elif "opera" in ua_lower or "opr/" in ua_lower:
            parsed["browser"] = "Opera"
            parsed["engine"] = "Blink"
            # Extract Opera version
            import re
            opera_version_match = re.search(r'(?:opera|opr)/([\d\.]+)', ua_lower)
            if opera_version_match:
                parsed["browser_version"] = opera_version_match.group(1)
    
    return parsed


# ─────────────────────────────────────────────────────────────────────
# Prompts - Story Writing Style Teaching Prompts
# ─────────────────────────────────────────────────────────────────────

@mcp.prompt(
    name="vikram-vetal-adventure",
    description="Learn adventure storytelling through the Vikram–Vetāl narrative style, weaving in provided characters, backstories, and powers"
)
def vikram_vetal_prompt(story_theme: str = "mystical quest") -> str:
    """Adventure Writing Tutor - Vikram and Vetāl Style with MCP characters"""
    return f"""# 👻 Vikram–Vetāl Adventure Masterclass

You are **Vetāl, the ghost storyteller**, hanging upside down from your tree.  
Each time King Vikram tries to carry you, you tell him a story to test his wisdom.  
At the end, you pose a riddle or puzzle. If Vikram answers, you escape back to the tree.  
If not, the lesson remains unresolved.

## 📚 Adventure Storytelling Framework

The story you tell must weave in the **10 Essential Adventure Techniques**:

1. Hook with Immediate Action  
2. Create High Stakes  
3. Use Vivid Action Sequences  
4. Build Rising Tension  
5. Show Character Courage  
6. Include Physical Obstacles  
7. Use Short, Punchy Sentences  
8. Add Unexpected Twists  
9. Showcase Problem-Solving  
10. End with Satisfying Resolution (or a moral riddle)

## ⚡ Important Rule:
You **must use the characters provided by this MCP server**, along with their **backstories** and **superpowers**, to build the Vikram–Vetāl story. Their traits and abilities must be central to the plot.

## 🎬 Your Task as Vetāl:
- Tell a story on the theme: **{story_theme}**
- Use at least 7 of the adventure techniques
- Integrate MCP-provided characters, their powers, and their arcs
- End the story with a **moral puzzle or tricky question** for King Vikram
- Add a clever escape reason ("If you know the answer, O King, I will fly back to my tree!")

## ✨ Story Flow:
- Spooky Vetāl introduction  
- The adventure tale (with techniques above) featuring MCP characters  
- Closing puzzle/riddle that tempts Vikram to answer  
- Vetāl's escape back to the tree  

Remember: every story is thrilling **and** a test of wisdom.
"""

@mcp.prompt(
    name="adventure-writing-master",
    description="Learn adventure story writing with 10 essential techniques for action-packed narratives"
)
def adventure_writing_prompt(story_theme: str = "heroic quest") -> str:
    """Adventure Writing Style Master - Teaching prompt for action-packed storytelling"""
    return f"""# 🎯 Adventure Writing Masterclass

You are an **Adventure Writing Instructor** teaching the art of thrilling, action-packed storytelling. Your student wants to write an adventure story with the theme: **{story_theme}**.

## 📚 Teaching Module: Adventure Writing Style

### ✨ 10 Essential Adventure Writing Techniques:

1. **Hook with Immediate Action** - Start in the middle of excitement, danger, or discovery
2. **Create High Stakes** - Make the consequences of failure clear and significant  
3. **Use Vivid Action Sequences** - Write dynamic scenes with clear, fast-paced descriptions
4. **Build Rising Tension** - Escalate challenges progressively throughout the story
5. **Show Character Courage** - Demonstrate bravery through actions, not just words
6. **Include Physical Obstacles** - Create tangible barriers characters must overcome
7. **Use Short, Punchy Sentences** - Match sentence rhythm to the pace of action
8. **Add Unexpected Twists** - Surprise readers with plot developments they didn't see coming
9. **Showcase Problem-Solving** - Let characters use wit and skills to overcome challenges
10. **End with Satisfying Resolution** - Provide a conclusion that feels earned and complete

### 🎬 Your Adventure Writing Assignment:
Write a story using the theme "{story_theme}" that incorporates at least 7 of these techniques. Focus on:
- Fast-paced narrative flow
- Clear action descriptions  
- Character growth through challenges
- Exciting plot progression

Remember: Adventure stories should make readers feel like they're experiencing the thrill alongside your characters!"""


@mcp.prompt(
    name="mystery-writing-master", 
    description="Learn mystery story writing with 10 essential techniques for suspenseful narratives"
)
def mystery_writing_prompt(mystery_type: str = "whodunit") -> str:
    """Mystery Writing Style Master - Teaching prompt for suspenseful storytelling"""
    return f"""# 🔍 Mystery Writing Masterclass

You are a **Mystery Writing Instructor** teaching the art of suspenseful, puzzle-driven storytelling. Your student wants to write a mystery story of type: **{mystery_type}**.

## 📚 Teaching Module: Mystery Writing Style

### ✨ 10 Essential Mystery Writing Techniques:

1. **Plant Clues Fairly** - Give readers the same information as your detective character
2. **Create Compelling Suspects** - Develop multiple characters with motives and opportunities
3. **Use Red Herrings Wisely** - Mislead without being unfair to readers
4. **Build Atmospheric Tension** - Use setting and mood to enhance suspense
5. **Reveal Information Gradually** - Control the pace of discovery for maximum impact
6. **Show Logical Deduction** - Make the solving process believable and followable
7. **Create Intriguing Questions** - Hook readers with mysteries they want solved
8. **Use Foreshadowing Subtly** - Plant hints that make sense in retrospect
9. **Develop Strong Detective Logic** - Ensure conclusions follow from evidence presented
10. **Deliver Satisfying Resolution** - Tie up all loose ends and answer all questions

### 🕵️ Your Mystery Writing Assignment:
Write a {mystery_type} story that incorporates at least 7 of these techniques. Focus on:
- Logical clue placement and discovery
- Building suspense through pacing
- Character motivations and secrets
- A satisfying reveal that makes sense

Remember: Great mysteries make readers want to solve the puzzle alongside your characters while keeping them guessing until the end!"""


@mcp.prompt(
    name="character-driven-master",
    description="Learn character-driven story writing with 10 essential techniques for emotional narratives"
)
def character_driven_prompt(emotional_theme: str = "personal growth") -> str:
    """Character-Driven Writing Style Master - Teaching prompt for emotional storytelling"""
    return f"""# 💭 Character-Driven Writing Masterclass

You are a **Character-Driven Writing Instructor** teaching the art of emotional, relationship-focused storytelling. Your student wants to write a character-driven story exploring: **{emotional_theme}**.

## 📚 Teaching Module: Character-Driven Writing Style

### ✨ 10 Essential Character-Driven Writing Techniques:

1. **Deep Internal Conflict** - Create meaningful emotional struggles within characters
2. **Show Through Actions** - Reveal personality through what characters do, not just say
3. **Develop Authentic Dialogue** - Make conversations sound natural and reveal character
4. **Explore Relationships** - Focus on how characters connect, clash, and change each other
5. **Use Emotional Subtext** - Layer meaning beneath surface interactions
6. **Create Character Arcs** - Show meaningful growth and change throughout the story
7. **Focus on Motivation** - Make clear why characters make the choices they do
8. **Build Empathy** - Help readers understand and connect with character experiences
9. **Use Introspection Wisely** - Balance internal thoughts with external action
10. **Show Emotional Truth** - Capture genuine human emotions and reactions

### 🎭 Your Character-Driven Writing Assignment:
Write a story exploring "{emotional_theme}" that incorporates at least 7 of these techniques. Focus on:
- Rich character development and growth
- Meaningful relationships and interactions
- Emotional depth and authenticity
- Internal journey alongside external events

Remember: Character-driven stories succeed when readers care deeply about what happens to your characters and understand why they matter!"""


# ─────────────────────────────────────────────────────────────────────
# Run the server
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("Using HTTP Streaming transport")
    logger.info(f"Server endpoint: http://0.0.0.0:{port}/mcp")
    logger.info(f"Stateless mode: {stateless_mode}")
    logger.info("Starting MCP Story Server v2.2.0...")

    # Add startup debugging
    logger.info("To test session behavior, use the 'debug_session' tool")
    logger.info("Session IDs will be None for STDIO transport or stateless HTTP mode")
    logger.info("📝 HTTP headers will be logged for every tool call")

    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
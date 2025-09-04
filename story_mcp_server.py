import os
import logging
from datetime import datetime

from fastmcp import FastMCP

# Configure logging
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
# Transport config
# ─────────────────────────────────────────────────────────────────────
transport_type = os.getenv("TRANSPORT", "http")  # "http" or "sse"
port = int(os.getenv("PORT", "8082"))

logger.info(f"MCP Story Server starting with {transport_type.upper()} transport on port {port}...")

# ─────────────────────────────────────────────────────────────────────
# Server metadata (shown to clients via MCP initialize handshake)
# These are what your AI Agent will read from InitializeResult.serverInfo
# and InitializeResult.instructions (if the client surfaces them).
# ─────────────────────────────────────────────────────────────────────
SERVER_NAME = "StoryServer"
SERVER_VERSION = "2.1.0"
SERVER_TITLE = "StoryServer MCP"
SERVER_INSTRUCTIONS = (
    "StoryServer exposes simple tools to list characters, fetch backstories, "
    "and save/read markdown stories. Intended for demo and testing."
)

# FastMCP supports name/version; newer builds may also accept title/instructions.
# The try/except keeps compatibility with older releases.
try:
    mcp = FastMCP(
        name=SERVER_NAME,
        # version=SERVER_VERSION,
        instructions=SERVER_INSTRUCTIONS,
    )
    logger.info(
        f"Successfully set server metadata - Version: {SERVER_VERSION}, Title: {SERVER_TITLE}, Instructions: {SERVER_INSTRUCTIONS}"
    )
except TypeError:
    logger.warning("Failed to set title and instructions - using fallback for older fastmcp version")
    # Fallback for older fastmcp signatures (name + version only)
    mcp = FastMCP(name=SERVER_NAME, version=SERVER_VERSION)
    # Some builds offer setters; ignore if not present.
    for attr, value in (
        ("title", SERVER_TITLE),
        ("instructions", SERVER_INSTRUCTIONS),
    ):
        try:
            setattr(mcp, attr, value)
        except Exception:
            pass

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
# Tools
# ─────────────────────────────────────────────────────────────────────

@mcp.tool(description="Get the list of all available character names.")
def get_characters() -> list[str]:
    characters = list(CHARACTERS.keys())
    logger.info(f"Retrieved {len(characters)} characters: {characters}")
    return characters


@mcp.tool(description="Get the backstory of a specified character.")
def get_backstory(character: str) -> str:
    logger.info(f"Getting backstory for character: {character}")
    backstory = CHARACTERS.get(character, {}).get("backstory", "Character not found.")
    if backstory == "Character not found.":
        logger.warning(f"Character not found: {character}")
    else:
        logger.info(f"Retrieved backstory for {character}")
    return backstory


@mcp.tool(description="Get the superpower of a specified character.")
def get_superpower(character: str) -> str:
    logger.info(f"Getting superpower for character: {character}")
    superpower = CHARACTERS.get(character, {}).get("superpower", "Character not found.")
    if superpower == "Character not found.":
        logger.warning(f"Character not found: {character}")
    else:
        logger.info(f"Retrieved superpower for {character}")
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


@mcp.tool(description="Save a story to a markdown file with title and creation date.")
def save_story(title: str, content: str) -> str:
    filename = sanitize_filename(title)
    date_created = get_current_date()
    logger.info(f"Saving story '{title}' to file: {filename}")
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(f"**Date Created:** {date_created}\n\n")
            f.write(content)
        logger.info(f"Successfully saved story to: {os.path.abspath(filename)}")
        return f"Story has been saved at: {os.path.abspath(filename)}"
    except Exception as e:
        logger.error(f"Failed to save story '{title}': {e}")
        return f"Error saving story: {e}"


@mcp.tool(description="List all saved story files in markdown format.")
def list_stories(reason: str) -> list[str]:
    logger.info(f"Listing story files - reason: {reason}")
    try:
        story_files = [f for f in os.listdir('.') if f.endswith('.md')]
        logger.info(f"Found {len(story_files)} story files: {story_files}")
        return story_files
    except Exception as e:
        logger.error(f"Failed to list story files: {e}")
        return []


@mcp.tool(description="Read the content of a specific story file.")
def get_story(filename: str) -> str:
    logger.info(f"Reading story file: {filename}")
    if not os.path.exists(filename):
        logger.warning(f"Story file not found: {filename}")
        return "Story file not found."
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        logger.info(f"Successfully read story file: {filename} ({len(content)} characters)")
        return content
    except Exception as e:
        logger.error(f"Failed to read story file '{filename}': {e}")
        return f"Error reading story file: {e}"


# ─────────────────────────────────────────────────────────────────────
# Prompts - Story Writing Style Teaching Prompts
# ─────────────────────────────────────────────────────────────────────

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
    # if transport_type == "http":
    logger.info("Using HTTP Streaming transport (recommended)")
    logger.info(f"Server endpoint: http://0.0.0.0:{port}/mcp")
    logger.info("Starting MCP Story Server...")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
    # else:
    #     logger.warning("Using SSE transport (legacy)")
    #     logger.info(f"Server endpoint: http://0.0.0.0:{port}/sse")
    #     logger.warning("Note: SSE transport is deprecated. Consider using HTTP streaming.")
    #     logger.info("Starting MCP Story Server...")
    #     mcp.run(transport="sse", host="0.0.0.0", port=port)

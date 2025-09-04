# 📚 Story MCP Server

This is a lightweight **MCP (Multi-Channel Processor)** server powered by the `fastmcp` module. It provides a creative storytelling platform with character management and story storage capabilities using HTTP Streaming transport.

---

## 📦 Features

- FastAPI-based HTTP Streaming server using `fastmcp`
- Character management with backstories and superpowers
- Story creation and storage in markdown format
- Comprehensive logging system
- Dockerized for portability and ease of use

---

## 🚀 Getting Started

### 🔧 Prerequisites

- Docker & Docker Compose installed
- Python 3.x (for local runs)
- `fastmcp` Python package

---

### 🐳 Run via Docker

#### 1. Clone the repository

```bash
git clone <your-repo-url>
cd story_mcp_server
```

#### 2. Build and run

```bash
docker compose up --build
```

> 🟢 MCP server will be available at `http://localhost:8082/mcp`

---

### 🛠 Local Run (for development)

```bash
pip install fastmcp
python story_mcp_server.py
```

---

## ⚙️ Project Structure

```txt
.
├── Dockerfile                # Container setup
├── docker-compose.yml        # Compose file for container orchestration
├── story_mcp_server.py      # Main MCP server implementation
├── requirements.txt         # Python dependencies
├── story_server.log        # Server logs
└── README.md
```

---

## 🌐 Networking (Docker Compose)

The server is configured to run on port 8082 by default and uses HTTP Streaming transport:

```yaml
networks:
  app_network_pyd:
    driver: bridge
```

---

## 🧰 Exposed MCP Tools

This MCP server registers **six tools**, each providing specific storytelling and character management functionality:

### 1. `get_characters()`

🔍 **Description**:  
Returns a list of all available character names.

📤 **Output**:
- List of character names (e.g., ["Jack", "Ram", "Robert"])

---

### 2. `get_backstory(character: str)`

📄 **Description**:  
Retrieves the backstory for a specified character.

📥 **Input**:
- `character` *(str)*: Name of the character

📤 **Output**:
- Character's backstory as a string

---

### 3. `get_superpower(character: str)`

💪 **Description**:  
Gets the superpower of a specified character.

📥 **Input**:
- `character` *(str)*: Name of the character

📤 **Output**:
- Character's superpower as a string

---

### 4. `save_story(title: str, content: str)`

💾 **Description**:  
Saves a story to a markdown file with title and creation date.

📥 **Inputs**:
- `title` *(str)*: Story title
- `content` *(str)*: Story content

📤 **Output**:
- Confirmation message with file path

---

### 5. `list_stories(reason: str)`

📚 **Description**:  
Lists all saved story files in markdown format.

📥 **Input**:
- `reason` *(str)*: Reason for listing stories (for logging)

📤 **Output**:
- List of story filenames

---

### 6. `get_story(filename: str)`

📖 **Description**:  
Reads and returns the content of a specific story file.

📥 **Input**:
- `filename` *(str)*: Name of the story file to read

📤 **Output**:
- Story content in markdown format

---

### ✅ Example Flow

1. Get available characters: `get_characters()`
2. Get character details: `get_backstory("Jack")` and `get_superpower("Jack")`
3. Create and save a story: `save_story("Jack's Adventure", "...")`
4. List available stories: `list_stories("checking available stories")`
5. Read a story: `get_story("jacks_adventure.md")`

---

## 🎨 Writing Style Prompts

This MCP server also exposes **three educational prompts** that act as writing instructors, teaching different storytelling styles with specific techniques and assignments.

### 1. `adventure-writing-master`

🎯 **Description**:  
An Adventure Writing Instructor that teaches action-packed storytelling techniques.

📥 **Input**:
- `story_theme` *(str, optional)*: Theme for the adventure story (default: "heroic quest")

📤 **Output**:
- Complete masterclass content with 10 essential adventure writing techniques
- Specific writing assignment based on the provided theme
- Teaching guidance for creating thrilling, fast-paced narratives

---

### 2. `mystery-writing-master`

🔍 **Description**:  
A Mystery Writing Instructor that teaches suspenseful, puzzle-driven storytelling.

📥 **Input**:
- `mystery_type` *(str, optional)*: Type of mystery story (default: "whodunit")

📤 **Output**:
- Complete masterclass content with 10 essential mystery writing techniques
- Specific writing assignment based on the mystery type
- Teaching guidance for creating engaging, suspenseful narratives

---

### 3. `character-driven-master`

💭 **Description**:  
A Character-Driven Writing Instructor that teaches emotional, relationship-focused storytelling.

📥 **Input**:
- `emotional_theme` *(str, optional)*: Emotional theme to explore (default: "personal growth")

📤 **Output**:
- Complete masterclass content with 10 essential character-driven writing techniques
- Specific writing assignment based on the emotional theme
- Teaching guidance for creating deep, emotionally resonant narratives

---

### 🎓 How to Use Writing Prompts

These prompts are designed to be used with AI language models to get structured writing guidance:

1. **Choose a writing style** that matches your story goals
2. **Specify parameters** (theme, mystery type, or emotional focus)
3. **Receive comprehensive teaching content** with techniques and assignments
4. **Apply the techniques** to create stories using the character tools

**Example Usage:**
- Request `adventure-writing-master` with theme "space exploration"
- Use the teaching content to write an adventure story featuring Jack's invisibility powers
- Save the completed story using `save_story()`

---

## 📝 Demo Characters

The server comes with three pre-configured characters:

1. **Jack**: A former spy with invisibility and telepathy powers
2. **Ram**: An ancient warrior with invincible body and immense strength
3. **Robert**: A scientist-turned-cyborg with advanced technological powers

These characters can be used to create engaging stories using their unique backstories and abilities.

---
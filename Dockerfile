# Use an official Python image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for Playwright browsers)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Install Playwright browsers (this installs Chromium)
# RUN playwright install chromium --with-deps

# Copy the app code
COPY . .

# Expose the port used by the MCP server
EXPOSE 8082

# Run the MCP server
# CMD ["mcp", "run", "-t", "sse", "kb_support_mcp.py"]
# python story_mcp_server.py     
CMD ["python", "story_mcp_server.py"]
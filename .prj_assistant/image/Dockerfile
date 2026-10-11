FROM ghcr.io/pandazxx/codex-slack-agent-minimal:v4.20-rc17

USER root
# Build toolchain + native libs needed by raylib (pyray) and headless testing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    libgl1 \
    libglu1-mesa \
    libx11-6 \
    libxrandr2 \
    libxi6 \
    libxcursor1 \
    libxinerama1 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Shared libraries for Playwright's headless Chromium (scripts/agent_web_test.py), so agents
# can drive web builds in the browser. The browser itself comes from `just agent-setup`.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libgbm1 libpango-1.0-0 \
    libcairo2 libexpat1 \
    && (apt-get install -y --no-install-recommends libasound2 \
        || apt-get install -y --no-install-recommends libasound2t64) \
    && rm -rf /var/lib/apt/lists/*

# uv (Python/dependency manager) and just (task runner), installed system-wide.
# uv downloads the Python version pinned in .python-version on demand.
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin INSTALLER_NO_MODIFY_PATH=1 sh \
    && UV_TOOL_DIR=/opt/uv-tools UV_TOOL_BIN_DIR=/usr/local/bin uv tool install rust-just

USER appuser

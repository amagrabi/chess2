FROM python:3.10-slim

# Install pygame dependencies and X virtual framebuffer
RUN apt-get update && apt-get install -y \
    python3-dev \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install -e .

# Use xvfb-run to handle headless environment
ENTRYPOINT ["xvfb-run", "-s", "-screen 0 800x800x24", "python", "-m", "gui.app"]
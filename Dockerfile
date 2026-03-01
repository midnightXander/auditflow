FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CHROME_PATH=/usr/bin/chromium

# Install OS deps, Chromium and Node.js (Node from NodeSource)
RUN apt-get update && \
    apt-get install -y curl gnupg ca-certificates build-essential \
      libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libx11-6 \
      libxcomposite1 libxdamage1 libxrandr2 libxss1 libasound2 \
      fonts-liberation xdg-utils chromium && \
    # install Node 18.x (adjust version if needed)
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python requirements & install
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

# Install Node deps for the lighthouse runner
COPY package.json package-lock.json /app/
WORKDIR /app/
RUN npm ci --no-audit --no-fund

# Copy project sources
WORKDIR /app
COPY . /app

EXPOSE $PORT

ENV PATH="/usr/local/bin:${PATH}"

# Adjust the command to how you run your app in production (uvicorn/gunicorn)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "$PORT", "--workers", "1"]
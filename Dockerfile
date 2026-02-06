FROM node:20-bookworm

# System packages (ffmpeg etc.)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# App folder
WORKDIR /app

# Sirf package.json copy karo
COPY package.json ./

# NPM install
RUN npm install

# Baaki project files copy
COPY . .

# App start command
CMD ["node", "index.js"]


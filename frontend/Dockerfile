# -----------------------------
#  Development Dockerfile
#  Uses Vite dev server (auto-refresh + browser open)
# -----------------------------
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Expose Vite default port
EXPOSE 5173

# Run Vite dev server, open browser automatically
CMD ["npm", "run", "dev", "--", "--host", "--open"]

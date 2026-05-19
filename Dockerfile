FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json* ./

RUN npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && (npm ci --maxsockets=1 || npm ci --maxsockets=1 || npm ci --maxsockets=1)

COPY . .

USER node

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

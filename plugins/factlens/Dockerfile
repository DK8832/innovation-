FROM node:22-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

ENV NODE_ENV=production \
    FACTLENS_TRANSPORT=http \
    FACTLENS_PYTHON=python3 \
    HOST=0.0.0.0 \
    PORT=3000

EXPOSE 3000
CMD ["node", "dist/server.mjs"]

# Frontend image (spec 017, T024).
#
# Build context is the REPO ROOT (set RAILWAY_DOCKERFILE_PATH=frontend/Dockerfile
# on the Railway frontend service), kept uniform with the backend. Only frontend/
# is copied in, so the image stays small.
#
# NEXT_PUBLIC_API_URL is inlined into the client bundle at BUILD time, so it must
# be present as a build ARG (Railway passes service variables as Docker build args).
# Set it to the backend's public domain BEFORE building; a later change needs a rebuild.

FROM node:22-slim

# NOTE: do NOT set NODE_ENV=production before `npm ci` — that omits
# devDependencies (openapi-typescript, typescript, tailwindcss), which the build
# step needs. `next start` runs in production mode regardless of this var.
WORKDIR /app

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

# Install deps first (cache layer). package-lock.json is committed.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# App source + typed-client generation + production build.
COPY frontend ./
RUN npm run gen:api && npm run build

EXPOSE 3000
# Railway injects $PORT; default to 3000 for local `docker run`.
CMD ["sh", "-c", "npm run start -- -p ${PORT:-3000}"]

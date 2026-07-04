# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    AI_NOVEL_DATABASE_URL=sqlite:////data/app.db \
    AI_NOVEL_PROJECTS_DIR=/data/projects \
    AI_NOVEL_MODEL_TIMEOUT_SECONDS=120 \
    AI_NOVEL_GENERATION_TIMEOUT_SECONDS=900

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

RUN mkdir -p /data/projects
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app.interfaces.main:app", "--host", "0.0.0.0", "--port", "8000"]

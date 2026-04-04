FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Copy dependency configuration first
COPY pyproject.toml uv.lock ./

# Install directly into the container's system Python.
# This cleanly avoids virtually environment clashes between Windows host and Linux container!
RUN uv pip install --system --no-cache-dir -r pyproject.toml

# We don't copy the source code here in dev mode because docker-compose will volume map it.
# EXPOSE the port
EXPOSE 8000

# Default command
CMD ["bash", "-c", "cd core && python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]

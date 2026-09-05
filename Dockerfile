# ------------------------------------------------------------------------------
# App-layer image (FastAPI). Multi-stage build: a builder stage installs deps,
# the final stage copies only what's needed -> smaller, cleaner image.
# Runs the app on the mock backend by default; guardrails default to passthrough
# inside the container (no local gateway path), and the app runs fine that way.
# ------------------------------------------------------------------------------

# ---- Stage 1: builder ----
FROM python:3.11-slim AS builder

# Install deps into a virtualenv we can copy wholesale into the final stage.
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /build
# Copy only requirements first so this layer is cached unless deps change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Stage 2: final runtime ----
FROM python:3.11-slim

# Copy the ready-made virtualenv from the builder (no build tools carried over).
ENV VIRTUAL_ENV=/opt/venv
COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Run as a non-root user -- a basic container security best practice.
RUN useradd --create-home appuser
WORKDIR /home/appuser/app
COPY --chown=appuser:appuser app ./app
USER appuser

# The app listens on 8080.
EXPOSE 8080

# Default config: mock backend, guardrails passthrough (no gateway path set).
ENV BACKEND=mock

# Start the server. 0.0.0.0 so it's reachable from outside the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

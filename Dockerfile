FROM python:3.11-slim

# Create non-root user and group
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid 1000 --create-home appuser



ENV ANSIBLE_HOST_KEY_CHECKING=False

# Install Ansible and FastAPI deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    git openssh-client && \
    pip install --no-cache-dir ansible fastapi uvicorn python-multipart && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /mnt/ansible_logs

# Set working directory
WORKDIR /app

# Copy code
COPY --chown=1000:1000 app /app/app
COPY --chown=1000:1000 ansible /app/ansible
COPY --chown=1000:1000 static /app/static

# Create logs dir and give permissions
RUN mkdir -p /app/logs && chown -R 1000:1000 /app

USER 1000:1000

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
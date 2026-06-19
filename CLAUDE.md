# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Run

```bash
# Build the Docker image
docker build -t ansible-runner .

# Run the container
docker run -p 8080:8080 ansible-runner

# Access the web UI
open http://localhost:8080
```

There is no local dev server or test suite — all development is Docker-based. The app runs as non-root user `appuser` (UID 1000) inside the container.

## Architecture

This is a minimal **FastAPI + Ansible** app containerized in a single Docker image.

**Request flow:**
1. User submits the HTML form (`static/index.html`) to `POST /run-stream`
2. `app/main.py` receives form data, decrypts the SSH private key via `ssh-keygen`, writes a dynamic `ansible/inventory.ini`, then streams `ansible-playbook` stdout back to the browser via `StreamingResponse`
3. After the playbook finishes, logs are zipped and a `::DOWNLOAD:: <job_id>` sentinel line is sent — the frontend intercepts this to render a download link
4. The ZIP is served from `GET /download/<job_id>`

**Key design constraint:** Frontend form fields, backend `Form(...)` parameters, and Ansible `--extra-vars` must stay aligned. When adding a new playbook workflow, all three need updating together.

**Runtime paths (inside container):**
- SSH keys: `/home/appuser/.ssh/`
- Inventory: `/app/ansible/inventory.ini` (overwritten per run)
- Logs/results: `/app/logs/<job_id>/`
- ZIP archives: `/app/logs/<job_id>.zip`

**Ansible configuration** (`ansible/ansible.cfg`) sets `host_key_checking = False` and points to the decrypted key at `/home/appuser/.ssh/id_ansible_runner`. The env var `ANSIBLE_HOST_KEY_CHECKING=False` is also set in the Dockerfile as a belt-and-suspenders measure.

## Adding a New Playbook

1. Add the playbook to `ansible/`
2. Add new `Form(...)` parameters to the `/run-stream` handler in `app/main.py`
3. Map those parameters into the `extra_vars` dict passed via `--extra-vars`
4. Add matching `<input>` / `<textarea>` fields to `static/index.html`

The playbook in `ansible/reserved_instance.yml` (user creation, SSH key install, hostname set, hardware validation, result fetch) serves as the reference example.
# Ansible Runner (Example: Reserved Instance Validator)

A lightweight **FastAPI + Ansible** application that provides a web interface for running Ansible playbooks over SSH — no AWX, no Tower, no agent installation on target hosts.

You submit a form, the backend decrypts your SSH key, generates an inventory, and streams `ansible-playbook` output back to your browser in real time. When the run finishes, logs are zipped and a download link appears automatically.

This repository ships a **Reserved Instance validation and setup workflow** as the built-in example, but the runner is intentionally generic. Any playbook can be wired in by aligning three things: the HTML form fields, the FastAPI parameters, and the Ansible `extra_vars`.


## How It Works

When you submit the form, the backend runs through this sequence:

1. **Key decryption** — The encrypted private key is written to disk and decrypted in-place with `ssh-keygen -p`. A wrong passphrase stops the run immediately with an error. The encrypted copy is deleted after the run completes.

2. **Inventory generation** — A fresh `ansible/inventory.ini` is written for this run, one line per target IP, embedding the SSH username and key path.

3. **Streaming execution** — `ansible-playbook` runs as a subprocess. Its stdout is piped line-by-line into a `StreamingResponse`, so you see Ansible task output in real time rather than waiting for a single response at the end.

4. **Result packaging** — After the playbook exits, the per-run log directory is zipped. The backend emits a `::DOWNLOAD:: <job_id>` sentinel line into the stream. The frontend detects this, parses the job ID, and renders a download link — no polling required.

5. **Download** — `GET /download/<job_id>` serves the ZIP directly from the container filesystem.


## Current Implementation: Reserved Instance Validator

The included playbook (`ansible/reserved_instance.yml`) does the following on each target host in order:

1. Creates the new user, adds them to `sudo`, grants passwordless sudo
2. Writes `authorized_keys` with the public keys you provided
3. Sets the system hostname and updates `/etc/hosts`
4. Writes a DNS fallback (`1.1.1.1` / `8.8.8.8`) to `/etc/resolv.conf`
5. Captures hardware info: `lsb_release`, `lscpu`, `free`, `df`, `lsblk`, `nvidia-smi`, `ibstat` (GPU and Infiniband use `ignore_errors: true`)
6. Writes a per-host summary to the remote, then `fetch`es it back to `/app/logs/<job_id>/` — named by IP so multiple targets don't overwrite each other

This workflow is the **reference example**, not a limitation of the runner.


## Directory Structure

```
ansible-runner/
├── Dockerfile                     # Docker build for app
├── app/
│   └── main.py                    # FastAPI backend
├── static/
│   └── index.html                 # HTML form UI
├── ansible/
│   ├── reserved_instance.yml      # Example Ansible playbook
│   └── inventory.ini              # Dynamically generated inventory
├── logs/                          # Populated at runtime
│   └── validation_results/
│       ├── validation_summary.txt
│       └── ...
│   └── validation_results.zip
```


## Usage

### Build and run with Docker

```bash
docker build -t ansible-runner .
docker run -p 8080:8080 ansible-runner
```

Open in your browser:

```
http://localhost:8080
```


## Form Fields (Current Workflow)

| Field           | Description                                                   |
|-----------------|---------------------------------------------------------------|
| Target IPs      | One IP per line (e.g. `66.172.11.4`)                          |
| Ansible User    | SSH user to connect as (e.g. `root`)                          |
| SSH Public Keys | One or more public keys to install on the new user            |
| Private Key     | Encrypted SSH private key (textarea)                          |
| Passphrase      | Passphrase for the encrypted private key                      |
| New Hostname    | Hostname to assign on each target                             |
| New User        | User account to create on each target                         |
| Client Name     | Optional identifier used for log and ZIP naming               |


## Output

Logs are written inside the container to:

```
/app/logs/<client>_validation_results_<timestamp>/
```

Once zipped, the archive is available at:

```
GET /download/<client>_validation_results_<timestamp>
```

The `::DOWNLOAD::` line that triggers the frontend link is a sentinel written by the backend after archiving — it's not part of Ansible's output.


## Extending the Runner with New Playbooks

The runner has a three-layer contract that must stay aligned:

```
HTML form fields  →  FastAPI Form() params  →  Ansible extra_vars
```

If you add a field to the form but not the backend, it gets silently dropped. If you add a backend param but not the Ansible variable, the playbook uses its declared default. When all three are aligned, the runner infrastructure (streaming, key handling, inventory, ZIP packaging) doesn't change — only the playbook does.

### Walkthrough

**Step 1: Add the playbook** under `ansible/`, with `vars:` defaults for anything the backend will pass:

```yaml
- hosts: all
  gather_facts: false
  vars:
    app_name: ""
    app_version: ""
    environment: ""
  tasks:
    - debug:
        msg: "Deploying {{ app_name }} version {{ app_version }} to {{ environment }}"
```

**Step 2: Update `app/main.py`** — add `Form(...)` parameters to `run_stream()`, populate `extra_vars`, and point the command at the new playbook:

```python
extra_vars = {
    "app_name": app_name,
    "app_version": app_version,
    "environment": environment,
}
cmd = ["ansible-playbook", "/app/ansible/deploy_app.yml", "-i", inventory_path,
       "--extra-vars", json.dumps(extra_vars)]
```

**Step 3: Update `static/index.html`** — add matching fields with the same `name` attributes:

```html
<label>App Name</label>
<input name="app_name" />

<label>App Version</label>
<input name="app_version" />

<label>Environment</label>
<select name="environment">
  <option value="dev">dev</option>
  <option value="prod">prod</option>
</select>
```


## Kubernetes Support

This application can be deployed into a Kubernetes cluster for **internal tooling**.

Ensure that:

- The pod has outbound SSH access to target hosts
- You use `ClusterIP` or internal routing
- The service is not exposed publicly
- SSH keys and sensitive inputs are handled carefully


## Notes

- No authentication layer — treat this as an internal tool only
- `inventory.ini` is a shared file; concurrent form submissions would overwrite each other
- SSH keys are written to disk during the run and deleted after, but not zero-wiped
- Not intended to replace AWX/Tower

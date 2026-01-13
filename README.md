# Ansible Runner (Example: Reserved Instance Validator)

A lightweight **FastAPI + Ansible** application that provides a simple web interface for running Ansible automation over SSH.

This repository currently implements a **Reserved Instance validation and setup workflow**, but the overall structure is intentionally generic. The same backend and frontend pattern can be adapted to run **any Ansible playbook** as long as the required variables are surfaced in the UI and handled by the API.

---

## Features

- Web-based form to trigger Ansible runs
- Supports:
  - Multiple target IPs (line-delimited)
  - SSH authentication using an encrypted private key + passphrase
  - Installation of one or more SSH public keys
  - Hostname and user creation on remote systems
- Executes Ansible inside the container
- Collects per-run logs and summaries
- Packages results into a downloadable ZIP
- Fully functional in:
  - Docker (single container, no external mounts)
  - Kubernetes (for internal usage only; not safe for public exposure)

---

## Current Implementation: Reserved Instance Validator

The included Ansible playbook performs validation and preparation of reserved instances over SSH, including:

- Connecting to each target host
- Creating a new user
- Installing provided SSH public keys
- Setting the hostname
- Running validation checks
- Capturing logs per host
- Generating a ZIP archive of results per session

This workflow serves as a **reference example**, not a limitation of the runner itself.

---

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

---

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

---

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

---

## Output

After submitting the form:

- Logs and summaries are written to:

```
/app/logs/<client>_validation_results_<timestamp>/
```

- A ZIP archive containing all results is generated and made available at:

```
/download/<client>_validation_results_<timestamp>
```

A download link also appears in the web UI once execution completes, displayed as:

```
::DOWNLOAD:: <client>_validation_results_<timestamp>
```

---

## Extending the Runner with New Playbooks

This application is designed so that new Ansible workflows can be added with minimal changes.

At a high level:

1. Add or replace a playbook under `ansible/`
2. Update the backend to:
   - accept the required inputs
   - validate them
   - pass them as Ansible variables (e.g. `--extra-vars`)
3. Update the frontend form to collect those inputs

As long as the **frontend fields, backend handling, and Ansible variables remain aligned**, the runner can execute different automation workflows without changing its overall structure.

---

## Walkthrough: Adding a New Playbook

### Step 1: Add the playbook

```
ansible/
└── deploy_app.yml
```

Example playbook:

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

---

### Step 2: Update the backend

Extend the API to accept the required inputs and map them to Ansible variables.

Conceptual example:

```python
extra_vars = {
  "app_name": request.app_name,
  "app_version": request.app_version,
  "environment": request.environment,
}
```

Execute:

```
ansible-playbook ansible/deploy_app.yml --extra-vars "<serialized vars>"
```

---

### Step 3: Update the frontend

Add corresponding fields to the HTML form:

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

---

### Step 4: Keep the contract aligned

> Frontend inputs → backend validation → Ansible variables must remain aligned.

If they are aligned, the underlying automation can change freely.

---

## Kubernetes Support

This application can be deployed into a Kubernetes cluster for **internal tooling**.

Ensure that:

- The pod has outbound SSH access to target hosts
- You use `ClusterIP` or internal routing
- The service is not exposed publicly
- SSH keys and sensitive inputs are handled carefully

---

## Notes

- This is not intended to replace AWX/Tower
- There is no authentication layer by default
- Treat this as an internal automation tool

---

## Future Improvements (Optional)

- Multiple selectable playbooks/actions
- Per-playbook input schemas
- Live log streaming
- Authentication and access controls
- Run history and auditing

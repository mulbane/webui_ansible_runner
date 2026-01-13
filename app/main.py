# /app/main.py
import subprocess
import os
import shutil
import json
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime

app = FastAPI()
app.mount("/static", StaticFiles(directory="/app/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("/app/static/index.html") as f:
        return HTMLResponse(f.read())

@app.post("/run-stream")
async def run_stream(
    target_ips: str = Form(...),
    ansible_user: str = Form(...),
    ssh_keys: str = Form(...),
    private_key: str = Form(...),
    passphrase: str = Form(...),
    new_hostname: str = Form(...),
    new_user: str = Form(...),
    client: str = Form(None),
):
    def generate():
        ssh_dir = "/home/appuser/.ssh"
        os.makedirs(ssh_dir, exist_ok=True)

        # Save raw SSH public keys (for debug/logs)
        with open(f"{ssh_dir}/authorized_keys", "w") as f:
            f.write(ssh_keys)
        os.chmod(f"{ssh_dir}/authorized_keys", 0o600)

        # Save encrypted private key
        encrypted_key_path = f"{ssh_dir}/id_ansible_runner_encrypted"
        decrypted_key_path = f"{ssh_dir}/id_ansible_runner"
        with open(encrypted_key_path, "w") as f:
            f.write(private_key)
        os.chmod(encrypted_key_path, 0o600)

        # Decrypt the SSH key with passphrase
        try:
            subprocess.run([
                "ssh-keygen", "-p",
                "-P", passphrase,
                "-N", "",
                "-f", encrypted_key_path,
                "-m", "PEM"
            ], check=True)
            shutil.copyfile(encrypted_key_path, decrypted_key_path)
            os.chmod(decrypted_key_path, 0o600)
        except subprocess.CalledProcessError:
            yield "ERROR: Failed to decrypt SSH key. Is the passphrase correct?\n"
            return

        # Write inventory based on IPs and provided ansible_user
        inventory_path = "/app/ansible/inventory.ini"
        with open(inventory_path, "w") as f:
            for ip in target_ips.strip().splitlines():
                f.write(f"{ip.strip()} ansible_user={ansible_user} ansible_ssh_private_key_file=/home/appuser/.ssh/id_ansible_runner\n")

        # Generate job ID and output path
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_client = client or "client"
        job_id = f"{safe_client}_validation_results_{now}"
        validation_output_dir = f"/app/logs/{job_id}"
        os.makedirs(validation_output_dir, exist_ok=True)

        # Prepare newline-separated pubkeys string
        pubkey_string = "\n".join(ssh_keys.strip().splitlines()) + "\n"

        remote_tmp_dir = "/tmp/validation_results"

        extra_vars = {
            "new_hostname": new_hostname,
            "new_user": new_user,
            "client": safe_client,
            "ssh_pubkeys": pubkey_string,
            "validation_output_dir": remote_tmp_dir,
            "job_id": job_id
        }

        # Run the Ansible playbook
        cmd = [
            "ansible-playbook",
            "/app/ansible/reserved_instance.yml",
            "-i", inventory_path,
            "--extra-vars", json.dumps(extra_vars)
        ]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            yield line

        # Zip the job folder
        shutil.make_archive(validation_output_dir, 'zip', validation_output_dir)
        os.remove(encrypted_key_path)

        yield f"::DOWNLOAD:: {job_id}\n"

    return StreamingResponse(generate(), media_type="text/plain")

@app.get("/download/{job_id}")
async def download_zip(job_id: str):
    zip_path = f"/app/logs/{job_id}.zip"
    if os.path.exists(zip_path):
        return FileResponse(zip_path, media_type="application/zip", filename=f"{job_id}.zip")
    return HTMLResponse("ZIP archive not found.", status_code=404)
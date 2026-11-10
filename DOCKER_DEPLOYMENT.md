# Ubuntu 26.04 Docker deployment

The container is built from the **official \`ubuntu:26.04\` image**. It runs the current FastAPI + CSV-audit application as a non-root user, includes no third-party frontend assets, and does not embed API keys.

## Local deployment on WSL2

Prerequisites: WSL2 Ubuntu 26.04 LTS, Docker Engine and the Docker Compose plugin.

**On Windows, the simplest launcher is `start-docker-wsl.bat`.** It starts Docker Compose in the foreground so the WSL distribution remains running. Keep its terminal open while using ValuePilot, and press Ctrl+C to stop. When no WSL process remains, Windows may automatically shut down the WSL virtual machine and stop its containers. The launcher avoids relying on background services surviving an idle WSL shutdown.

Alternatively, start from the project directory in Ubuntu:

\`\`\`bash
cd /mnt/c/Users/kiran/ValuePilot
sudo docker compose build --pull
sudo docker compose up
sudo docker compose ps
\`\`\`

Open [http://127.0.0.1:8765](http://127.0.0.1:8765). The default **CSV opportunity audit works without Ollama, Redis, or Groq**, and CSV files never leave the browser.

\`\`\`bash
curl -fsS http://127.0.0.1:8765/health
sudo docker image inspect valuepilot:ubuntu-26.04 --format '{{.Config.User}}'
sudo docker compose logs --tail=50
sudo docker compose down
\`\`\`

The Compose file binds the host port to **127.0.0.1 only**, not to the local network. The container runs as **UID 10001**, with read-only filesystem, dropped Linux capabilities, limited memory and processes, and no-new-privileges.

### Optional Ollama integration

For the other (non-CSV) agent tools, the local model server must be reachable by the container at \`OLLAMA_BASE_URL\`. The example Compose file uses \`http://host.docker.internal:11434/v1\`.

Ollama on Windows may listen only on its own loopback address and may therefore **not** be reachable from a Linux Docker container through the bridge gateway. Do **not** expose the Ollama port to the public internet. If connectivity fails, keep the free offline CSV audit working and configure a private local-only model endpoint for the optional tools. The model is **not** required for the default CSV feature or container health checks.

### Docker Engine setup on Ubuntu

Use Docker's official Ubuntu repository and verify your WSL distro is Ubuntu 26.04 first:
https://docs.docker.com/engine/install/ubuntu/

If you decide to add your user to the \`docker\` group, be aware that Docker documents it as granting root-level privileges. This project instead uses \`sudo docker\` to avoid automatically widening that privilege.

## CI and deployment

GitHub Actions builds the same Dockerfile on an Ubuntu 26.04 runner, verifies the non-root user and boots the container to check the API and static assets.

For **Render**, changing the existing native Python service to the **Docker** runtime is a separate action. Committing the Dockerfile alone does not change the hosting service's runtime. In Render: Web service → Settings → Build → Source → Edit → Runtime Docker (build from repository Dockerfile) → Deploy. Preserve the existing \`GROQ_API_KEY\` and \`REDIS_URL\` secrets. Do not set \`VALUEPILOT_LOCAL_MODE=1\` or \`VALUEPILOT_CONTAINER_LOCAL=1\` on the public service.

### Limitations

- Container image tag \`ubuntu:26.04\` identifies the LTS release but is not pinned to an immutable digest; use a digest and timely automated dependency updates if strict reproducibility/supply-chain controls are required.
- Docker and Ubuntu consume local disk space, RAM and electricity. The CSV algorithm invokes no model, but the container is not literally zero-cost.
- No claim of full GDPR, SOC 2, ISO 27001, or SDG compliance is made.
- All business recommendations require human review, and the pipeline metrics do not establish causal revenue recovery.

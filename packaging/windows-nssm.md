# Windows service using NSSM

1. Download NSSM and install.
2. Create service:
   - Application: path to `ey-cs-monitor.exe` (or your venv `Scripts\ey-cs-monitor.exe`).
   - Arguments: `--config C:\path\to\config.yaml`
   - Startup directory: folder containing `config.yaml`.
3. In the Environment tab, add required variables (e.g., `CS_CLIENT_ID=...;CS_CLIENT_SECRET=...`).
4. Set service recovery to restart on failure.
5. Start service.

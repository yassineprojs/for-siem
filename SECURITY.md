# Security design

- Secrets are provided via environment variables; no secrets in config or code.
- All HTTP calls use HTTPS endpoints.
- Local JSONL audit log records each notification event and no sensitive fields from detections are transmitted, only counts and a static link.
- Minimal dependencies, pinned at install via lock from CI.
- No telemetry, no data egress beyond selected notification channels.
- Consider placing the tool behind a proxy that enforces egress allow-listing.

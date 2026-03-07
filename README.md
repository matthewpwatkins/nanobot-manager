# nanobot-manager

A CLI tool that installs [Nanobot](https://github.com/HKUDS/nanobot) into a hardened Linux sandbox: dedicated system user, filesystem ACL whitelisting, network domain allowlisting via Squid proxy, iptables containment, and systemd service management.

**Linux only.** No AppArmor/SELinux required — uses standard Unix primitives.

## Security layers

| Layer | Mechanism |
|-------|-----------|
| Dedicated user | `nanobot` system user, no login, no sudo |
| Filesystem | POSIX ACLs (`setfacl`) — explicit per-path grants only |
| Network | Squid proxy domain allowlist + iptables UID rules to prevent bypass |
| systemd | `NoNewPrivileges`, `ProtectSystem=strict`, `PrivateTmp`, etc. |
| Config | `config.json` owned by managing user, group-readable by nanobot — nanobot can't modify its own config or API keys |

## Requirements

- Linux (systemd-based distro)
- Python 3.11+
- `curl` (for auto-installing uv if missing)
- `iptables`

The following are auto-installed by `nanomanager install` if missing:

- [`uv`](https://docs.astral.sh/uv/) — Python package/tool manager
- `acl` package (`setfacl`/`getfacl`) — POSIX ACL utilities
- `squid` — HTTP proxy (skipped with `--skip-proxy`)

## Install

```bash
git clone https://github.com/matthewpwatkins/nanobot-manager.git
cd nanobot-manager
sudo ./bootstrap.sh    # installs uv (if missing) + nanomanager
```

Or if you already have `uv`:

```bash
uv tool install --from . nanobot-manager
```

## Usage

### Full setup

```bash
sudo nanomanager install
sudo nanomanager onboard       # configure API key, model, chat channel
sudo nanomanager start
sudo nanomanager status
```

### Skip optional layers

```bash
sudo nanomanager install --skip-proxy --skip-firewall
```

### Service management

```bash
sudo nanomanager start
sudo nanomanager stop
sudo nanomanager restart
sudo nanomanager status [--json]
sudo nanomanager logs [-f] [-n 100]
```

### Filesystem access

```bash
sudo nanomanager access grant /data/reports          # read-only
sudo nanomanager access grant /data/output --write   # read-write
sudo nanomanager access revoke /data/reports
sudo nanomanager access list
```

### Network allowlist

```bash
sudo nanomanager network allow api.example.com
sudo nanomanager network block api.example.com
sudo nanomanager network list
```

### Config

```bash
sudo nanomanager config show
sudo nanomanager config show --reveal-secrets
sudo nanomanager config edit
```

### MCP servers

```bash
sudo nanomanager mcp add my-tool --type stdio --command "/usr/local/bin/my-mcp-server"
sudo nanomanager mcp add remote --type sse --url "http://localhost:8080/sse"
sudo nanomanager mcp remove my-tool
sudo nanomanager mcp list
```

### Update nanobot

```bash
sudo nanomanager update
sudo nanomanager update --version 1.2.3
```

### Uninstall

```bash
sudo nanomanager uninstall
sudo nanomanager uninstall --keep-data   # preserve /home/nanobot
```

## How it works

### Network containment

Nanobot runs with `HTTP_PROXY`/`HTTPS_PROXY` pointing at a local Squid instance (`127.0.0.1:3128`). Squid enforces a domain allowlist. iptables rules (matched by UID) block all outbound traffic from the `nanobot` user except to loopback — so there's no way to bypass the proxy with raw sockets or direct HTTP calls.

DNS resolution happens inside Squid (a different UID), not inside the nanobot process.

### Filesystem isolation

External paths are not accessible by default. Use `nanomanager access grant` to whitelist specific paths via `setfacl`. Default ACLs are set so new files created under granted directories inherit the same permissions.

Nanobot's own install directory (`~/.local`) is owned `root:nanobot` with mode `750` — nanobot can read and execute its own binaries but cannot modify them.

### Config protection

`config.json` is owned by the managing user with group `nanobot` and mode `640`. Nanobot can read its config (including API keys) but cannot write to it. The manager controls all config changes and MCP server definitions.

## State

Manager state is stored at `/etc/nanomanager/state.yaml` (root-owned, mode `600`). It tracks ACL grants, the network domain allowlist, install options, and metadata.

## Default network allowlist

During `onboard`, domains are added based on your chosen LLM provider and chat channel:

| Provider | Domains |
|----------|---------|
| Anthropic | `api.anthropic.com` |
| OpenAI | `api.openai.com` |
| OpenRouter | `openrouter.ai` |
| DeepSeek | `api.deepseek.com` |
| Groq | `api.groq.com` |
| Gemini | `generativelanguage.googleapis.com` |

| Channel | Domains |
|---------|---------|
| Slack | `slack.com` |
| Discord | `discord.com`, `gateway.discord.gg` |
| Telegram | `api.telegram.org` |

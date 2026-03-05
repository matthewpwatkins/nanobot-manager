from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from nanomanager.core.nanobot_config import (
    CHANNEL_DOMAINS,
    CONFIG_PATH,
    DEFAULT_CONFIG,
    PROVIDER_DOMAINS,
    set_proxy_in_config,
    write_config,
)
from nanomanager.core.proxy import add_domain
from nanomanager.state import NetworkDomain, load_state, save_state
from nanomanager.sudo import require_root

console = Console()

PROVIDERS = list(PROVIDER_DOMAINS.keys())
CHANNELS = list(CHANNEL_DOMAINS.keys()) + ["none"]

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5",
    "openai": "gpt-4o",
    "openrouter": "anthropic/claude-sonnet-4-5",
    "deepseek": "deepseek-chat",
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.0-flash",
}


def onboard() -> None:
    """Interactive setup wizard for API keys and channel configuration."""
    require_root()

    state = load_state()
    if state is None:
        console.print("[red]Error:[/red] nanomanager is not installed. Run 'sudo nanomanager install' first.")
        raise typer.Exit(1)

    console.print(Panel.fit("[bold cyan]Nanobot Manager - Onboard[/bold cyan]"))
    console.print("This wizard configures your API keys and chat channel.\n")

    # LLM Provider
    console.print("[bold]Available LLM providers:[/bold]")
    for i, p in enumerate(PROVIDERS, 1):
        console.print(f"  {i}. {p}")
    provider_idx = Prompt.ask(
        "Select provider",
        choices=[str(i) for i in range(1, len(PROVIDERS) + 1)],
    )
    provider = PROVIDERS[int(provider_idx) - 1]

    api_key = Prompt.ask(f"Enter {provider} API key", password=True)
    default_model = DEFAULT_MODELS.get(provider, "")
    model = Prompt.ask("Model name", default=default_model)

    # Chat channel
    console.print("\n[bold]Available chat channels:[/bold]")
    for i, ch in enumerate(CHANNELS, 1):
        console.print(f"  {i}. {ch}")
    channel_idx = Prompt.ask(
        "Select channel",
        choices=[str(i) for i in range(1, len(CHANNELS) + 1)],
    )
    channel = CHANNELS[int(channel_idx) - 1]

    channel_config: dict = {}
    if channel == "slack":
        channel_config["slackBotToken"] = Prompt.ask("Slack bot token", password=True)
        channel_config["slackAppToken"] = Prompt.ask("Slack app token", password=True)
    elif channel == "discord":
        channel_config["discordToken"] = Prompt.ask("Discord bot token", password=True)
    elif channel == "telegram":
        channel_config["telegramToken"] = Prompt.ask("Telegram bot token", password=True)

    # Build config
    config = dict(DEFAULT_CONFIG)
    config["llmProvider"] = provider
    config["apiKey"] = api_key
    config["model"] = model
    if channel != "none":
        config["channel"] = channel
        config.update(channel_config)

    if state.install_options.proxy_enabled:
        config = set_proxy_in_config(config, state.install_options.proxy_port)

    write_config(config, owner_user=state.managing_user)

    # Add required domains to squid allowlist
    if state.install_options.proxy_enabled:
        console.print("\n[bold]Configuring network allowlist...[/bold]")
        domains_to_add = list(PROVIDER_DOMAINS.get(provider, []))
        if channel != "none":
            domains_to_add += CHANNEL_DOMAINS.get(channel, [])

        existing_domains = {d.domain for d in state.network_domains}
        for domain in domains_to_add:
            if domain not in existing_domains:
                state.network_domains.append(NetworkDomain(domain=domain, builtin=True))
                console.print(f"  + {domain}")

        from nanomanager.core.proxy import write_domain_allowlist, restart_squid
        write_domain_allowlist([d.domain for d in state.network_domains])
        save_state(state)
        try:
            restart_squid()
        except Exception:
            pass

    console.print("\n[bold green]Onboarding complete![/bold green]")
    console.print("Run [cyan]sudo nanomanager start[/cyan] to launch nanobot.")

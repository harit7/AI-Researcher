# llm_runtimes integration notes

Additive support for routing model names prefixed `claudecli-` or `local-`
through the vendored `llm_runtimes/` package (an embedded OpenAI-compatible
server started lazily in-process, default `http://127.0.0.1:8399/v1`).
All other model names behave exactly as before.

## Files changed

- `research_agent/inno/llm_runtimes_compat.py` (new): `apply_llm_runtimes(create_params)`
  rewrites litellm kwargs when the model name starts with `claudecli-` or
  `local-`: `model -> "openai/<name>"`, `base_url -> ensure_server()`,
  `api_key -> "llm-runtimes"`. No-op otherwise.
- `research_agent/inno/core.py`: translation applied in `get_chat_completion`
  (sync) and in the function-calling branch of `get_chat_completion_async`,
  just before the litellm `completion`/`acompletion` calls.
- `research_agent/inno/tools/file_surfer_tool.py`: translation applied to the
  two direct `completion(model=COMPLETION_MODEL, ...)` calls.

`llm_runtimes/` itself is unmodified.

## Usage

Model names are configured the usual way (`.env` / environment; see
`.env.template`). Only the value changes per backend.

### 1. Usual provider API (unchanged)

```bash
export COMPLETION_MODEL=claude-3-5-sonnet-20241022   # or gpt-4o-2024-08-06, openrouter/..., etc.
export CHEEP_MODEL=gpt-4o-mini-2024-07-18
# plus the provider API key(s), e.g. OPENAI_API_KEY / ANTHROPIC_API_KEY
```

### 2. Claude via local `claude` CLI (subscription auth, no API key)

```bash
export COMPLETION_MODEL=claudecli-sonnet    # also: claudecli-opus, claudecli-haiku
export CHEEP_MODEL=claudecli-haiku
```

Equivalents to the README examples: where the README says
`COMPLETION_MODEL=claude-3-5-sonnet-20241022`, use
`COMPLETION_MODEL=claudecli-sonnet`.

### 3. Local model via in-process vLLM

```bash
export COMPLETION_MODEL=local-qwen          # default HF model: Qwen/Qwen3-8B-AWQ
# optional overrides:
export LLM_RUNTIMES_LOCAL_HF_ID=Qwen/Qwen3-8B-AWQ
export LLM_RUNTIMES_LOCAL_GPU=0
export LLM_RUNTIMES_PORT=8399
```

No other env vars are needed for the runtime backends; the dummy
`api_key="llm-runtimes"` is injected automatically and the server starts on
first use.

## Limitations

- `claudecli-*` ignores `temperature`; sampling is controlled by the CLI.
- `claudecli-*` reports zeroed token-usage fields (the CLI does not expose
  comparable counts), so any cost/usage accounting reads 0.
- Tool/function calling on the runtime server is emulated: only the first
  tool's schema is forwarded and the reply is wrapped as a single
  `tool_calls` entry (single-tool, forced-call style). The agent loop in
  `research_agent/inno/core.py` passes the full multi-tool list per agent, so
  agents with many tools will effectively only be offered the first tool when
  running on `claudecli-*` / `local-*`. Fine for single-tool or
  `tool_choice="required"` single-function calls; multi-tool agent turns are
  degraded.
- `local-*` defaults to `Qwen/Qwen3-8B-AWQ` and needs a local GPU.
- Docker-based execution flows (`run_infer_plan.py` / `run_infer_idea.py`
  execute code inside a container): LLM calls are made from the host process,
  but if anything inside the container needs to reach the runtime server,
  `LLM_RUNTIMES_PORT` (default 8399) must be reachable from the container
  (e.g. host networking). Not addressed here; noted for later.

## Overnight run attempt (2026-08-12)

The LLM plumbing works end to end on this host (smoke test passed via
claudecli-haiku). A full pipeline run is NOT possible on this machine tonight:
container execution is required, and rootless podman fails to unpack images
("potentially insufficient UIDs or GIDs available in user namespace" - the host
has no /etc/subuid,/etc/subgid mappings for this user; needs a sysadmin, e.g.
`usermod --add-subuids 100000-165535 --add-subgids 100000-165535 <user>` then
`podman system migrate`). On a machine with working docker, the documented
recipes above should run as-is.

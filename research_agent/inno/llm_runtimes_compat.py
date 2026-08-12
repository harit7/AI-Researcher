"""Optional routing of llm_runtimes-backed models through litellm.

If the configured model name starts with "claudecli-" (Claude via the local
`claude` CLI) or "local-" (in-process vLLM model), rewrite the litellm call to
target the embedded OpenAI-compatible server provided by the vendored
`llm_runtimes` package at the repo root:

    model    -> "openai/<name>"   (litellm's generic OpenAI-compatible route)
    base_url -> ensure_server()   (e.g. http://127.0.0.1:8399/v1)
    api_key  -> "llm-runtimes"    (dummy; the local server ignores it)

For every other model name this is a no-op, so existing API-based
configurations are unaffected.
"""


def is_llm_runtimes_model(model) -> bool:
    return isinstance(model, str) and (
        model.startswith("claudecli-") or model.startswith("local-")
    )


def apply_llm_runtimes(create_params: dict) -> dict:
    """Rewrite litellm kwargs in place when the model targets llm_runtimes.

    Returns the same dict for call-site convenience.
    """
    model = create_params.get("model")
    if is_llm_runtimes_model(model):
        from llm_runtimes import ensure_server  # lazy: only needed for these models

        create_params["model"] = "openai/" + model
        create_params["base_url"] = ensure_server()
        create_params["api_key"] = "llm-runtimes"
    return create_params

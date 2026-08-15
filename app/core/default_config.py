DEFAULT_CONFIG = {
    "active_provider": "openai",
    "active_model": "gpt-4.1-mini",
    "fallback_provider": "gigachat",
    "fallback_model": "GigaChat",
    "openai_model": "gpt-4.1-mini",
    "gigachat_model": "GigaChat",
    "temperature": 0.1,
    "max_tokens": 2048,
    "prompt_id": "onboarding",
    "providers": {
        "openai": {
            "api_key_env": "OPENAI_API_KEY",
            "base_url": None,
        },
        "gigachat": {
            "auth_key_env": "GIGACHAT_AUTH_KEY",
            "base_url_env": "GIGACHAT_BASE_URL",
            "token_url_env": "GIGACHAT_TOKEN_URL",
            "scope_env": "GIGACHAT_SCOPE",
            "ca_bundle_env": "GIGACHAT_CA_BUNDLE",
        },
    },
}

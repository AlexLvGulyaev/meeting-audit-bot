DEFAULT_CONFIG = {
    "active_provider": "openai",
    "fallback_provider": "gigachat",
    "openai_model": "gpt-4.1-mini",
    "gigachat_model": "GigaChat",
    "prompt_id": "onboarding",
    "providers": {
        "openai": {
            "api_key_env": "OPENAI_API_KEY",
            "base_url": None,
            "temperature": 0.1,
            "max_tokens": 2048,
        },
        "gigachat": {
            "auth_key_env": "GIGACHAT_AUTH_KEY",
            "base_url_env": "GIGACHAT_BASE_URL",
            "token_url_env": "GIGACHAT_TOKEN_URL",
            "scope_env": "GIGACHAT_SCOPE",
            "ca_bundle_env": "GIGACHAT_CA_BUNDLE",
            "temperature": 0.1,
            "max_tokens": 2048,
        },
    },
}

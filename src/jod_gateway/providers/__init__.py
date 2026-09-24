def load_builtin_adapters() -> None:
    from jod_gateway.core.router import register
    from jod_gateway.providers.echo.adapter import EchoAdapter

    register(EchoAdapter())
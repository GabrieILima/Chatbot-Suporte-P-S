import asyncio

from src.api.main import health


def test_health_endpoint():
    body = asyncio.run(health())
    assert body["status"] == "healthy"
    assert body["service"] == "Chatbot Suporte P&S"

"""Robinhood Agentic has NO official paper sandbox in its Trading MCP.

Never implement an unofficial Robinhood login/API or direct live order route.
This adapter is explicitly simulation-only.
"""
from .models import LimitOrder, OrderRejected

MCP_URL = "https://agent.robinhood.com/mcp/trading"

def check() -> dict:
    return {
        "broker":"robinhood",
        "paper_trading_available":False,
        "live_agentic_supported_by_provider":True,
        "live_trading_enabled_here":False,
        "connection":"NOT_CONNECTED",
        "note":"Official Robinhood Agentic MCP trades in a dedicated real-money account; no PAPER sandbox"
    }

def submit(req: LimitOrder):
    raise OrderRejected("Robinhood Agentic offers no verified PAPER endpoint; LIVE submissions are disabled")

def shadow_preview(req: LimitOrder) -> dict:
    return {
        **req.public(),
        "broker":"robinhood",
        "environment":"SIMULATION_ONLY",
        "status":"SIMULATED_ONLY",
        "broker_order_id":None,
        "submitted_to_robinhood":False,
        "note":"No account or live broker contacted"
    }

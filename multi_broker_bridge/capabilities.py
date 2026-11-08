"""Machine-readable capability declaration for the five-minute monitor.

Provider support is not the same as a commissioned bridge capability.
These are deliberately the capabilities of THIS implementation, not every
order type offered by the underlying brokerage.
"""
CAPABILITIES = {
    "alpaca": {
        "paper_environment": True, "live_enabled": False,
        "order_types": ["limit"], "time_in_force": ["day"],
        "extended_hours": False, "bracket": False, "fractional": False,
        "max_order_notional_usd": "2000.00",
        "sell_requires_long_position": True, "broker_readback": True,
        "operationally_verified": False
    },
    "ibkr": {
        "paper_environment": True, "live_enabled": False,
        "order_types": ["limit"], "time_in_force": ["day"],
        "extended_hours": False, "bracket": False, "fractional": False,
        "max_order_notional_usd": "2000.00",
        "sell_requires_long_position": True, "broker_readback": "callbacks",
        "operationally_verified": False
    },
    "robinhood": {
        "paper_environment": False, "live_enabled": False,
        "order_types": [], "time_in_force": [],
        "extended_hours": False, "bracket": False, "fractional": False,
        "max_order_notional_usd": "0",
        "shadow_preview_only": True, "broker_readback": False,
        "operationally_verified": False
    }
}

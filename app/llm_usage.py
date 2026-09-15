"""What each Claude call consumed, and what it cost.

Anthropic is by far the larger bill here - a single long script can produce
twenty thousand output tokens at ten dollars a million, where an AI image costs
four cents - and until now nothing recorded it. Every call logs through here so
the cost of a video is measured rather than estimated, the same way image
generation reports its own tokens.

Prices are the published Claude API rates and, like the image rate, are
overridable by environment variable rather than being buried in code.
"""

import logging
import os

logger = logging.getLogger(__name__)

# Dollars per million tokens, per model. Input, output, and the two cache
# rates: writing a cache entry costs 1.25x input, reading one costs 0.1x.
_PRICES = {
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-opus-5": (5.0, 25.0),
}
_PRICE_OVERRIDE = os.environ.get("CLAUDE_PRICE_PER_MILLION", "").strip()

_totals: dict[str, float] = {}


def _rates(model: str) -> tuple[float, float] | None:
    if _PRICE_OVERRIDE:
        try:
            entrada, salida = (float(x) for x in _PRICE_OVERRIDE.split(","))
            return entrada, salida
        except ValueError:
            logger.warning("CLAUDE_PRICE_PER_MILLION mal escrito (%r); se ignora.", _PRICE_OVERRIDE)
    for name, rates in _PRICES.items():
        if model.startswith(name):
            return rates
    return None


def record(step: str, model: str, message) -> float:
    """Logs one call's tokens and cost, and returns the cost in dollars.

    Returns 0.0 and logs what it can when the usage block is missing or the
    model's price is unknown - accounting must never be able to break a video.
    """
    usage = getattr(message, "usage", None)
    if usage is None:
        return 0.0
    entrada = getattr(usage, "input_tokens", 0) or 0
    salida = getattr(usage, "output_tokens", 0) or 0
    cache_write = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0

    rates = _rates(model)
    if rates is None:
        logger.info(
            "[coste] %s: %s entrada, %s salida, %s cache leida (precio de %s desconocido)",
            step, entrada, salida, cache_read, model,
        )
        return 0.0

    precio_entrada, precio_salida = rates
    coste = (
        entrada * precio_entrada
        + cache_write * precio_entrada * 1.25
        + cache_read * precio_entrada * 0.10
        + salida * precio_salida
    ) / 1_000_000
    _totals[step] = _totals.get(step, 0.0) + coste
    logger.info(
        "[coste] %s: %s entrada + %s salida (%s cache escrita, %s leida) = %.4f $",
        step, entrada, salida, cache_write, cache_read, coste,
    )
    return coste


def report_and_reset() -> str:
    """One line summing what a whole video cost, then starts the next count."""
    if not _totals:
        return ""
    total = sum(_totals.values())
    desglose = ", ".join(f"{k} {v:.4f}$" for k, v in sorted(_totals.items(), key=lambda kv: -kv[1]))
    _totals.clear()
    return f"Coste en Claude de este video: {total:.4f} $ ({desglose})"

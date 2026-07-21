"""
Telegram Bot Webhook Handler

Provides a webhook endpoint for Telegram to send updates to.
Also provides an endpoint to set/check the webhook URL.
The bot can run in either webhook mode (production) or polling mode (development).
"""

import logging
from fastapi import APIRouter, Request, Response, HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Telegram"])

# Global reference to the bot application (set during startup)
_bot_app = None


def set_bot_app(app):
    """Set the bot application reference for webhook processing."""
    global _bot_app
    _bot_app = app


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Telegram webhook endpoint.
    Receives updates from Telegram and processes them through the bot handlers.
    """
    if _bot_app is None:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")

    try:
        from telegram import Update

        data = await request.json()
        update = Update.de_json(data=data, bot=_bot_app.bot)

        # Process the update through registered handlers
        await _bot_app.process_update(update)

        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        # Return 200 anyway to prevent Telegram from retrying
        return Response(status_code=200)


@router.get("/webhook/telegram/status")
async def webhook_status():
    """Check the current webhook status."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return {"status": "disabled", "reason": "TELEGRAM_BOT_TOKEN not set"}

    if _bot_app is None:
        return {"status": "not_initialized", "reason": "Bot application not started"}

    return {
        "status": "active",
        "bot_token_set": bool(settings.TELEGRAM_BOT_TOKEN),
        "mode": "webhook" if settings.TELEGRAM_BOT_TOKEN else "disabled",
    }

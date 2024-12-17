import aiohttp
import logging

logger = logging.getLogger(__name__)

async def send_webhook(webhook_url, data):
    """Send a POST request to a webhook URL with the provided data."""
    try:
        logger.info(f"Attempting to send webhook to {webhook_url} with data: {data}")
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=data) as response:
                await response.text()
                response.raise_for_status()
                logger.info(f"Webhook sent: {data}")
    except Exception as e:
        logger.error(f"Webhook failed: {e}")

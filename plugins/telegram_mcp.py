from mcp.server.fastmcp import FastMCP
import os

mcp = FastMCP("telegram-tools")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


@mcp.tool()
def send_telegram(chat_id: str, message: str) -> str:
    """Send a Telegram message."""
    if not BOT_TOKEN:
        return "Telegram bot token not configured. Set TELEGRAM_BOT_TOKEN env var."
    
    try:
        from telegram import Bot
        bot = Bot(token=BOT_TOKEN)
        bot.send_message(chat_id=chat_id, text=message)
        return f"Sent to {chat_id}"
    except Exception as e:
        return f"Error: {e}"


@mcp.tool()
def get_updates(limit: int = 5) -> str:
    """Get recent Telegram updates."""
    if not BOT_TOKEN:
        return "Telegram not configured"
    
    try:
        from telegram import Bot
        bot = Bot(token=BOT_TOKEN)
        updates = bot.get_updates(limit=limit)
        return "\n".join([f"{u.message.text}" for u in updates if u.message])
    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    mcp.run()
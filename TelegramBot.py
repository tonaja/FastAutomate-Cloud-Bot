# telegram.py
import os
import re
import sys
import asyncio
from urllib.parse import urlparse

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

from query_data import query_rag

sys.path.append(os.path.abspath("C:\\Users\\FaceGraph\\Downloads\\FastAutomate_PrimeLeads\\new-folder\\Prime_Leads"))
from main_graph import main_PrimeLeads

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Simple in-memory state
user_state = {}  # { user_id: "WAITING_PRIMELEADS_URL" }

ASK_TOKEN = "[[ASK:PRIMELEADS_URL]]"

def extract_url(text: str) -> str | None:
    """Grab the first http(s) URL and validate it."""
    m = re.search(r"(data/sample_website_url[^\s]+)", text, flags=re.IGNORECASE)
    if not m:
        return None
    url = m.group(1)
    parsed = urlparse(url)
    if parsed.scheme in ("data") and parsed.netloc:
        return url
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! I’m your chatbot. Send me a message.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()

    # 1) If we're waiting for a PrimeLeads URL, try to extract it and run the tool
    if user_state.get(user_id) == "WAITING_PRIMELEADS_URL":
        url = extract_url(text)
        if not url:
            await update.message.reply_text("Please send a valid URL")
            return

        await update.message.reply_text("⏳ Running PrimeLeads…")
        try:
            # Run blocking function in a thread so we don't block the bot
            result = await asyncio.get_running_loop().run_in_executor(None, main_PrimeLeads, url)
            await update.message.reply_text(str(result))
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error running PrimeLeads: {e}")
        finally:
            user_state.pop(user_id, None)
        return

    # 2) Normal flow: ask the LLM
    response = query_rag(text)

    # If the LLM asked for a PrimeLeads URL, set state and send a cleaned message
    if ASK_TOKEN in response:
        clean = response.replace(ASK_TOKEN, "").strip()
        if not clean:
            clean = "🔗 Please send the URL you want PrimeLeads to process."
        user_state[user_id] = "WAITING_PRIMELEADS_URL"
        await update.message.reply_text(clean)
        return

    # Otherwise just reply with the LLM answer
    await update.message.reply_text(response)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

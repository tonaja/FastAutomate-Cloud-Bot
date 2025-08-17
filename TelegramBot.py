import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from query_data import query_rag
from primeleads_runner import main_primeleads   # ✅ import your PrimeLeads function

load_dotenv()  # Load local .env
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# simple dictionary to track user states
user_state = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! I’m your chatbot. Send me a message.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text.strip()

    # ✅ Step 1: If we are waiting for a URL for PrimeLeads
    if user_state.get(user_id) == "waiting_for_url":
        url = user_message
        await update.message.reply_text("⏳ Running PrimeLeads, please wait...")
        try:
            result = main_primeleads(url)
            await update.message.reply_text(result)
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error running PrimeLeads: {e}")
        user_state[user_id] = None
        return

    # ✅ Step 2: Normal flow - use query_rag
    response = query_rag(user_message)

    # If query_rag asked for URL, set state
    if "🔗 Please provide the URL" in response:
        user_state[user_id] = "waiting_for_url"

    await update.message.reply_text(response)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

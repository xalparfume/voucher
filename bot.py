import os
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)

# === LOAD ENV ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
REPL_ID = os.getenv("REPL_ID")
WEBHOOK_URL = f"https://{REPL_ID}.replit.app/webhook"

# === FILE CONFIG ===
VOUCHER_FILES = {
    "2000": "2000.txt",
    "10000": "10000.txt",
    "30000": "30000.txt"
}
LOG_FILE = "log_voucher.txt"

# === STATE ===
pending_upload = {}
lapor_pending = {}
user_messages = {}
user_last_voucher_message = {}
restock_state = {}

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === LOGIKA UTAMA ===
bot = Bot(token=BOT_TOKEN)
application = Application.builder().token(BOT_TOKEN).build()
flask_app = Flask(__name__)

async def kirim_tombol_awal(chat_id, context):
    messages = user_messages.get(chat_id, [])
    for mid in messages:
        if user_last_voucher_message.get(chat_id) != mid:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=mid)
            except:
                pass
    keyboard = [
        [InlineKeyboardButton("💳 Rp 2.000 (24 JAM)", callback_data="2000")],
        [InlineKeyboardButton("💰 Rp 10.000 (7 HARI)", callback_data="10000")],
        [InlineKeyboardButton("🛒 Rp 30.000 (30 HARI)", callback_data="30000")]
    ]
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text="📦 *Silakan pilih paket voucher:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    user_messages[chat_id] = [msg.message_id]

def ambil_voucher(file_path):
    if not os.path.exists(file_path): return None
    with open(file_path, "r") as f:
        lines = f.readlines()
    if not lines: return None
    voucher = lines[0].strip()
    with open(file_path, "w") as f:
        f.writelines(lines[1:])
    return voucher

def log_transaksi(user, harga, voucher):
    waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nama = f"{user.first_name} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "(no username)"
    with open(LOG_FILE, "a") as f:
        f.write(f"[{waktu}] - {nama} ({username}, ID: {user.id}) beli Rp{harga}: {voucher}\n")

# === HANDLERS (same as tes.py) ===
# (gunakan handler yang sama dari file aslimu — bisa di-copy-paste langsung)

# Contoh 1:
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await kirim_tombol_awal(update.effective_chat.id, context)

# === Tambahkan semua handler lainnya di sini ===
# Copy semua: handle_harga, handle_foto, handle_konfirmasi, handle_lapor_habis, restock, dsb.

# === FLASK WEBHOOK ===
@flask_app.route("/")
def index():
    return "🤖 Bot Telegram voucher aktif (webhook)."

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put(update)
    return "OK"

@flask_app.before_first_request
def setup():
    bot.delete_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

# === DAFTARKAN HANDLER DAN JALANKAN APP ===
def main():
    application.add_handler(CommandHandler("start", start))
    # tambahkan handler lainnya sama seperti di `tes.py`

    application.run_task()
    flask_app.run(host="0.0.0.0", port=3000)

if __name__ == "__main__":
    main()

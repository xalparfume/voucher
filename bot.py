import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# === LOAD ENVIRONMENT VARIABLES ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# === KONFIGURASI FILE ===
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

# === KIRIM TOMBOL VOUCHER ===
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
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r") as f:
        lines = f.readlines()
    if not lines:
        return None
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

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await kirim_tombol_awal(update.effective_chat.id, context)

async def handle_harga(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    harga = query.data
    user = query.from_user
    user_id = user.id
    file_path = VOUCHER_FILES.get(harga)

    if not file_path:
        await context.bot.send_message(chat_id=user_id, text="⚠️ Terjadi kesalahan.")
        return

    loading_msg = await context.bot.send_message(
        chat_id=user_id,
        text="⏳ *The voucher code is being created, please wait...!*",
        parse_mode="Markdown"
    )
    user_messages.setdefault(user_id, []).append(loading_msg.message_id)

    await asyncio.sleep(5)

    voucher = ambil_voucher(file_path)
    if not voucher:
        lapor_pending[user_id] = harga
        tombol_lapor = [[InlineKeyboardButton("📢 Laporkan ke Admin", callback_data="lapor_habis")]]
        habis_msg = await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ Stok voucher Rp{harga} habis.",
            reply_markup=InlineKeyboardMarkup(tombol_lapor)
        )
        user_messages[user_id].append(habis_msg.message_id)
        return

    voucher_msg = await context.bot.send_message(
        chat_id=user_id,
        text=f"✅ Voucher Rp{harga} berhasil!\n🔐 Kode Anda:\n`{voucher}`\n\n🙏 Terima kasih telah melakukan pembelian!",
        parse_mode="Markdown"
    )
    user_last_voucher_message[user_id] = voucher_msg.message_id

    nama = f"{user.first_name} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "(no username)"
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📥 Voucher Rp{harga} telah dikirim ke:\n👤 *{nama}* ({username})\n🆔 ID: `{user.id}`\n🔐 Kode: `{voucher}`",
        parse_mode="Markdown"
    )

    log_transaksi(user, harga, voucher)

    keyboard = [[InlineKeyboardButton("✅ Konfirmasi Pembayaran", callback_data="konfirmasi")]]
    konfirmasi_msg = await context.bot.send_message(
        chat_id=user_id,
        text="Jika sudah transfer, klik tombol di bawah untuk kirim bukti.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    user_messages[user_id].append(konfirmasi_msg.message_id)

async def handle_lapor_habis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id
    harga = lapor_pending.get(user_id)
    if not harga:
        await context.bot.send_message(chat_id=user_id, text="⚠️ Tidak ada laporan yang bisa dikirim.")
        return

    nama = f"{user.first_name} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "(no username)"
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🚨 LAPORAN: Stok voucher Rp{harga} habis!\n👤 {nama} ({username})\n🆔 ID: {user_id}"
    )
    konfirmasi = await context.bot.send_message(
        chat_id=user_id,
        text="📩 Laporan telah dikirim ke admin. Terima kasih telah memberi tahu!"
    )
    msg_id_konfirmasi = konfirmasi.message_id
    del lapor_pending[user_id]
    await kirim_tombol_awal(user_id, context)
    await asyncio.sleep(30)
    try:
        await context.bot.delete_message(chat_id=user_id, message_id=msg_id_konfirmasi)
    except:
        pass

async def handle_konfirmasi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    pending_upload[user_id] = True
    msg = await context.bot.send_message(chat_id=user_id, text="📸 Silakan kirim screenshot bukti pembayaran.")
    user_messages[user_id].append(msg.message_id)

async def handle_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg_id = update.message.message_id
    if pending_upload.get(user_id):
        await context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=update.effective_chat.id,
            message_id=msg_id
        )
        try:
            await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
        except:
            pass
        msg = await context.bot.send_message(
            chat_id=user_id,
            text="✅ Bukti pembayaran berhasil dikirim ke admin.\n🙏 Terima kasih atas kepercayaannya!"
        )
        user_messages.setdefault(user_id, []).append(msg.message_id)
        pending_upload[user_id] = False
        await kirim_tombol_awal(user_id, context)

async def restock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("✅ Perintah /restock diterima oleh admin.")
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Akses ditolak.")
        return
    keyboard = [
        [InlineKeyboardButton("➕ Add Voucher 24JAM", callback_data="restock_2000")],
        [InlineKeyboardButton("➕ Add Voucher 7DAY", callback_data="restock_10000")],
        [InlineKeyboardButton("➕ Add Voucher 30DAY", callback_data="restock_30000")]
    ]
    await update.message.reply_text(
        "🛠 Silakan pilih jenis voucher yang ingin ditambahkan:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_restock_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        return
    pilihan = query.data
    if pilihan == "restock_2000":
        restock_state[user_id] = "2000"
    elif pilihan == "restock_10000":
        restock_state[user_id] = "10000"
    elif pilihan == "restock_30000":
        restock_state[user_id] = "30000"
    await context.bot.send_message(chat_id=user_id, text="📥 Silakan kirim daftar voucher (satu per baris).")

async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID and user_id in restock_state:
        harga = restock_state[user_id]
        file_path = VOUCHER_FILES.get(harga)
        if file_path:
            vouchers = update.message.text.strip().splitlines()
            with open(file_path, "a") as f:
                for v in vouchers:
                    if v.strip():
                        f.write(v.strip() + "\n")
            await context.bot.send_message(chat_id=user_id, text=f"✅ {len(vouchers)} voucher berhasil ditambahkan ke Rp{harga}.")
        del restock_state[user_id]
    else:
        await update.message.reply_text("🤖 Maaf, saya tidak mengerti perintah ini. Silakan gunakan tombol yang tersedia.")

# === MAIN ===
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("restock", restock))
    application.add_handler(CallbackQueryHandler(handle_harga, pattern="^(2000|10000|30000)$"))
    application.add_handler(CallbackQueryHandler(handle_konfirmasi, pattern="^konfirmasi$"))
    application.add_handler(CallbackQueryHandler(handle_lapor_habis, pattern="^lapor_habis$"))
    application.add_handler(CallbackQueryHandler(handle_restock_choice, pattern="^restock_"))
    application.add_handler(MessageHandler(filters.PHOTO, handle_foto))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_admin_text))
    logger.info("Bot berjalan...")
    application.run_polling()

if __name__ == '__main__':
    main()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime
import os

# Mapping harga ke file
VOUCHER_FILES = {
    "2000": "2000.txt",
    "10000": "10000.txt",
    "30000": "30000.txt"
}

# Ganti dengan ID Anda
ADMIN_ID = 8185056425
LOG_FILE = "log_voucher.txt"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("Rp2.000 24JAM", callback_data='2000'),
            InlineKeyboardButton("Rp10.000 7DAY", callback_data='10000'),
            InlineKeyboardButton("Rp30.000 30DAY", callback_data='30000')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Silakan pilih paket voucher:", reply_markup=reply_markup)

def ambil_voucher(file_path):
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as file:
        lines = file.readlines()

    if not lines:
        return None

    voucher = lines[0].strip()
    with open(file_path, "w") as file:
        file.writelines(lines[1:])

    return voucher

def log_transaksi(user, harga, voucher):
    waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nama = f"{user.first_name} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "(no username)"
    user_id = user.id

    log_entry = (
        f"[{waktu}] - {nama} ({username}, ID: {user_id}) membeli Rp{harga} "
        f"dengan voucher: {voucher}\n"
    )

    with open(LOG_FILE, "a") as log:
        log.write(log_entry)

async def kirim_notif_admin(context: ContextTypes.DEFAULT_TYPE, user, harga):
    waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nama = f"{user.first_name} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else "(no username)"
    user_id = user.id

    pesan = (
        f"❗ STOK HABIS\n"
        f"Waktu: {waktu}\n"
        f"Paket: Rp{harga}\n"
        f"User: {nama} ({username}, ID: {user_id}) mencoba membeli."
    )

    await context.bot.send_message(chat_id=ADMIN_ID, text=pesan)

async def tombol_diklik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    harga = query.data
    file_voucher = VOUCHER_FILES.get(harga)

    if not file_voucher:
        await query.edit_message_text("❌ Terjadi kesalahan sistem.")
        return

    voucher = ambil_voucher(file_voucher)

    if voucher:
        log_transaksi(query.from_user, harga, voucher)
        pesan = (
            f"✅ Pembayaran Rp{harga} berhasil!\n"
            f"Berikut adalah kode voucher Anda:\n\n🔐 `{voucher}`"
        )
    else:
        await kirim_notif_admin(context, query.from_user, harga)
        pesan = (
            f"❌ Stok voucher Rp{harga} saat ini habis.\n"
            "Silakan hubungi admin untuk restock."
        )

    await query.edit_message_text(pesan, parse_mode="Markdown")

if __name__ == '__main__':
    import asyncio

    async def main():
        app = ApplicationBuilder().token("7691640004:AAEJREqhdDuPVBeFatkVq7Ztj0GKbC4-Swk").build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(tombol_diklik))

        print("Bot sedang berjalan...")
        await app.run_polling()

    asyncio.run(main())
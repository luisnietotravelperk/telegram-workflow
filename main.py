import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith(".pdf"):
        return

    file = await document.get_file()
    file_path = os.path.join(DOWNLOAD_DIR, document.file_name)
    await file.download_to_drive(file_path)

    await update.message.reply_text(f"✅ Archivo recibido y guardado: {document.file_name}")

    # Aquí podrías agregar: conversión y envío por correo

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    print("Bot iniciado...")
    app.run_polling()
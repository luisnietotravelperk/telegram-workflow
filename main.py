import os
import re
import base64
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from email.message import EmailMessage

# 🔐 Variables de entorno (añádelas en Railway)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_TO = os.environ.get("EMAIL_TO")  # ej: tunombre@kindle.com
EMAIL_FROM = os.environ.get("RESEND_SMTP_FROM_ADDRESS")  # ej: noreply@resend.dev

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 🔠 Sanitiza el nombre del archivo (sin espacios raros)
def sanitizar_nombre(nombre_original):
    base = os.path.splitext(nombre_original)[0]
    limpio = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', base)
    return limpio

# 📤 Envía el PDF a Kindle usando Resend API
def enviar_pdf_via_sendgrid(file_path):
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    data = {
        "personalizations": [{
            "to": [{"email": os.environ["EMAIL_TO"]}],
            "subject": " "
        }],
        "from": {"email": os.environ["EMAIL_FROM"]},
        "content": [{
            "type": "text/plain",
            "value": "Envío automático desde bot de Telegram"
        }],
        "attachments": [{
            "content": encoded,
            "type": "application/pdf",
            "filename": os.path.basename(file_path),
            "disposition": "attachment"
        }]
    }

    headers = {
        "Authorization": f"Bearer {os.environ['SENDGRID_API_KEY']}",
        "Content-Type": "application/json"
    }

    response = requests.post("https://api.sendgrid.com/v3/mail/send", json=data, headers=headers)
    print(f"SendGrid status: {response.status_code}, body: {response.text}")
    return response.status_code == 202

# 🤖 Manejador de archivos PDF
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith(".pdf"):
        return

    await update.message.reply_text("📥 Recibiendo PDF...")

    # Ruta de archivo segura
    original_name = document.file_name
    safe_name = f"{sanitizar_nombre(original_name)}.pdf"
    file_path = os.path.join(DOWNLOAD_DIR, safe_name)

    # Descarga
    file = await document.get_file()
    await file.download_to_drive(file_path)
    await update.message.reply_text(f"✅ PDF guardado como: {safe_name}")

    # Envío por Resend
    success = enviar_pdf_via_sendgrid(file_path)
    if success:
        await update.message.reply_text("📤 PDF enviado a Kindle (convertible).")
    else:
        await update.message.reply_text("❌ Error al enviar PDF. Revisa los logs.")

    # Limpieza
    try:
        os.remove(file_path)
        print(f"🧹 Archivo eliminado: {file_path}")
    except Exception as e:
        print(f"❌ Error al eliminar archivo: {e}")

# 🚀 Inicio del bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    print("🤖 Bot activo. Esperando archivos PDF...")
    app.run_polling()
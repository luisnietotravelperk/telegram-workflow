import os
import requests
import base64
import re
import smtplib
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from email.message import EmailMessage

# Configuración desde Railway (Variables de entorno)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
EMAIL_FROM = os.environ.get("EMAIL_FROM")         # Correo emisor autorizado
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") # Contraseña de aplicación
EMAIL_TO = os.environ.get("EMAIL_TO")             # Dirección de destino (ej: tu@kindle.com)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ✅ Función para sanitizar nombre de archivo (conserva formato legible)
def sanitizar_nombre(nombre_original):
    base = os.path.splitext(nombre_original)[0]  # "Op-Cap. 1131"
    limpio = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', base)  # Reemplaza caracteres no seguros
    return limpio

# ✅ Envío por correo
def enviar_pdf_para_convertir(file_path):
    msg = EmailMessage()
    msg["Subject"] = "Convert"  # Este asunto activa la conversión en Amazon
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.set_content("Archivo PDF enviado automáticamente desde tu bot de Telegram.")

    with open(file_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=os.path.basename(file_path)
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.send_message(msg)

def enviar_pdf_via_resend_api(file_path):
    with open(file_path, "rb") as f:
        contenido = base64.b64encode(f.read()).decode()

    data = {
        "from": f"Tu Bot <{os.environ['EMAIL_FROM']}>",
        "to": [os.environ["EMAIL_TO"]],
        "subject": "Convert",
        "attachments": [
            {
                "filename": os.path.basename(file_path),
                "content": contenido,
                "type": "application/pdf"
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {os.environ['RESEND_API_KEY']}",
        "Content-Type": "application/json"
    }

    response = requests.post("https://api.resend.com/emails", json=data, headers=headers)
    print(f"Resend API status: {response.status_code}, body: {response.text}")

# ✅ Manejador del bot cuando recibe un PDF
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith(".pdf"):
        return

    await update.message.reply_text("📥 Recibiendo PDF...")

    # Sanitiza nombre y genera rutas
    original_name = document.file_name
    base_name = sanitizar_nombre(original_name)
    safe_pdf_name = f"{base_name}.pdf"

    file_path = os.path.join(DOWNLOAD_DIR, safe_pdf_name)

    # Descarga el archivo
    file = await document.get_file()
    await file.download_to_drive(file_path)
    await update.message.reply_text(f"✅ PDF guardado como: {safe_pdf_name}")

    # Envía por correo
    try:
        enviar_pdf_via_resend_api(file_path)
        await update.message.reply_text("📤 EPUB enviado por correo electrónico.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error al enviar por email: {str(e)}")

    # Limpieza
    try:
        os.remove(file_path)
        print(f"🧹 Archivos eliminados: {file_path}")
    except Exception as e:
        print(f"❌ Error al eliminar archivos: {e}")

# ✅ Inicio del bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    print("🤖 Bot activo. Esperando archivos PDF...")
    app.run_polling()
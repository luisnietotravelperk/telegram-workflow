import os
import locale
import re
import smtplib
import pypandoc
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

# ✅ Conversión PDF → EPUB
def convertir_pdf_a_epub(input_path, output_path):
    try:
        # Fijar locale para evitar errores de entorno
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        
        # Descargar pandoc si hace falta
        pypandoc.download_pandoc()  # Asegura que pandoc esté disponible
        pypandoc.convert_file(input_path, 'epub', outputfile=output_path)
        return True
    except Exception as e:
        print(f"❌ Error en conversión: {e}")
        return False

# ✅ Envío por correo
def enviar_email_epub(archivo_epub):
    msg = EmailMessage()
    msg["Subject"] = " "  # Vacío para Kindle
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.set_content("Envío automático a Kindle desde tu bot de Telegram.")

    with open(archivo_epub, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="epub+zip",
            filename=os.path.basename(archivo_epub)
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.send_message(msg)

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
    safe_epub_name = f"{base_name}.epub"

    file_path = os.path.join(DOWNLOAD_DIR, safe_pdf_name)
    epub_path = os.path.join(DOWNLOAD_DIR, safe_epub_name)

    # Descarga el archivo
    file = await document.get_file()
    await file.download_to_drive(file_path)
    await update.message.reply_text(f"✅ PDF guardado como: {safe_pdf_name}")

    # Convierte a EPUB
    success = convertir_pdf_a_epub(file_path, epub_path)
    if not success:
        await update.message.reply_text("❌ Error al convertir a EPUB.")
        return
    await update.message.reply_text("📚 EPUB creado con éxito.")

    # Envía por correo
    try:
        enviar_email_epub(epub_path)
        await update.message.reply_text("📤 EPUB enviado por correo electrónico.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error al enviar por email: {str(e)}")

    # Limpieza
    try:
        os.remove(file_path)
        os.remove(epub_path)
        print(f"🧹 Archivos eliminados: {file_path}, {epub_path}")
    except Exception as e:
        print(f"❌ Error al eliminar archivos: {e}")

# ✅ Inicio del bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    print("🤖 Bot activo. Esperando archivos PDF...")
    app.run_polling()
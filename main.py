import os
import smtplib
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from email.message import EmailMessage
import pypandoc

# Configuración desde variables de entorno
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
EMAIL_FROM = os.environ.get("EMAIL_FROM")         # Correo emisor (autorizado en Amazon si usas Kindle)
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD") # Contraseña de aplicación
EMAIL_TO = os.environ.get("EMAIL_TO")             # Tu dirección @kindle.com o correo destino

# Carpeta de archivos temporales
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Conversión PDF → EPUB
def convertir_pdf_a_epub(input_path, output_path):
    try:
        # Descarga pandoc si es necesario
        pypandoc.download_pandoc()
        pypandoc.convert_file(input_path, 'epub', outputfile=output_path)
        return True
    except Exception as e:
        print(f"❌ Error en conversión: {e}")
        return False

# Envío del EPUB por correo
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

# Manejador de archivos PDF
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith(".pdf"):
        return

    await update.message.reply_text("📥 Recibiendo PDF...")
    file = await document.get_file()
    file_path = os.path.join(DOWNLOAD_DIR, document.file_name)
    await file.download_to_drive(file_path)
    await update.message.reply_text(f"✅ PDF guardado como: {document.file_name}")

    # Conversión
    epub_path = file_path.replace(".pdf", ".epub")
    success = convertir_pdf_a_epub(file_path, epub_path)

    if not success:
        await update.message.reply_text("❌ Error al convertir a EPUB.")
        return

    await update.message.reply_text("📚 EPUB creado con éxito.")

    # Envío por correo
    try:
        enviar_email_epub(epub_path)
        await update.message.reply_text("📤 EPUB enviado por correo electrónico.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error al enviar por email: {str(e)}")

    # Limpieza de archivos
    try:
        os.remove(file_path)
        os.remove(epub_path)
        print(f"🧹 Archivos eliminados: {file_path}, {epub_path}")
    except Exception as e:
        print(f"❌ Error al eliminar archivos: {e}")

# Inicialización del bot
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    print("🤖 Bot activo. Esperando archivos PDF...")
    app.run_polling()
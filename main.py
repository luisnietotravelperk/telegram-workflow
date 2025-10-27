import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from pdf2epub import convert
import smtplib
from email.message import EmailMessage

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
DOWNLOAD_DIR = "downloads"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith(".pdf"):
        return

    # Descarga del PDF
    file = await document.get_file()
    file_path = os.path.join(DOWNLOAD_DIR, document.file_name)
    await file.download_to_drive(file_path)
    await update.message.reply_text(f"✅ PDF recibido: {document.file_name}")

    # Conversión a EPUB
    epub_path = file_path.replace(".pdf", ".epub")
    success = convertir_pdf_a_epub(file_path, epub_path)

    if success:
        await update.message.reply_text(f"📚 Archivo convertido a EPUB: {os.path.basename(epub_path)}")
        enviar_email_epub(epub_path)
        await update.message.reply_text("📤 EPUB enviado por correo electrónico.")
    else:
        await update.message.reply_text("❌ No se pudo convertir el archivo a EPUB.")

def convertir_pdf_a_epub(input_path, output_path):
    try:
        output = pypandoc.convert_file(input_path, 'epub', outputfile=output_path)
        return True
    except Exception as e:
        print(f"Error al convertir: {e}")
        return False

def enviar_email_epub(archivo_epub):
    msg = EmailMessage()
    msg["Subject"] = ""
    msg["From"] = os.environ.get("EMAIL_FROM")
    msg["To"] = os.environ.get("EMAIL_TO")

    with open(archivo_epub, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="epub+zip",
            filename=os.path.basename(archivo_epub)
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.environ.get("EMAIL_FROM"), os.environ.get("EMAIL_PASSWORD"))
        smtp.send_message(msg)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    print("Bot iniciado...")
    app.run_polling()
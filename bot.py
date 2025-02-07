import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
    CallbackQueryHandler,
)

# Configuración de logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = os.getenv("TOKEN")
LOGIN_URL = os.getenv("LOGIN_URL")
REPORT_URL = os.getenv("REPORT_URL")

# Estados de la conversación
CATEGORIA, REPORT_TYPE, USER_EMAIL, USER_PASSWORD, COORD_X, COORD_Y, DESCRIPCION, CALLE, COLONIA, IMAGEN = range(10)

# Variables globales
reporte_data = {}
user_token = None
user_id = None
default_token = None
default_user_id = None

# Obtener token del usuario anónimo
def obtener_token_por_defecto():
    global default_token, default_user_id
    try:
        login_data = {"correo": "christiantronix@gmail.com", "contrasena": "123456789"}
        response = requests.post(LOGIN_URL, json=login_data)
        if response.status_code == 200:
            data = response.json()
            default_token = data.get("token")
            default_user_id = data.get("id")
            logging.info("✅ Token anónimo obtenido correctamente.")
        else:
            logging.error(f"❌ Error en autenticación anónima: {response.json()}")
    except Exception as e:
        logging.error(f"❌ Excepción en autenticación anónima: {e}")

# Iniciar el bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Mostrar botones de categorías
    keyboard = [
        [InlineKeyboardButton("Bacheo", callback_data="16")],
        [InlineKeyboardButton("Recolección de basura", callback_data="23")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecciona la categoría del reporte:", reply_markup=reply_markup)
    return CATEGORIA

# Manejo de la selección de categoría
async def categoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Guardar la categoría seleccionada
    reporte_data["id_cat_reportes"] = query.data

    # Mostrar botones de tipo de reporte (Anónimo o Con Usuario)
    keyboard = [
        [InlineKeyboardButton("Anónimo", callback_data="anonimo")],
        [InlineKeyboardButton("Con Usuario", callback_data="con_usuario")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("¿Quieres reportar como Anónimo o Con Usuario?", reply_markup=reply_markup)
    return REPORT_TYPE

# Manejo del tipo de reporte
async def report_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data
    global user_token, user_id

    if choice == "anonimo":
        user_token = default_token
        user_id = default_user_id
        reporte_data["idUsuariosReporte"] = user_id
        reporte_data["ciudadano"] = ""
        reporte_data["telefono"] = ""
        await query.edit_message_text("Ingresa la coordenada X:")
        return COORD_X
    elif choice == "con_usuario":
        await query.edit_message_text("Proporciona tu correo electrónico:")
        return USER_EMAIL
    else:
        await query.edit_message_text("Opción inválida. Selecciona una opción válida.")
        return REPORT_TYPE

# Autenticación con correo y contraseña
async def user_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["correo"] = update.message.text
    await update.message.reply_text("Proporciona tu contraseña:")
    return USER_PASSWORD

async def user_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contrasena"] = update.message.text
    await update.message.reply_text("Autenticando...")

    try:
        login_data = {"correo": context.user_data["correo"], "contrasena": context.user_data["contrasena"]}
        response = requests.post(LOGIN_URL, json=login_data)
        if response.status_code == 200:
            global user_token, user_id
            data = response.json()
            user_token = data.get("token")
            user_id = data.get("id")
            reporte_data["idUsuariosReporte"] = user_id
            await update.message.reply_text("✅ Autenticación exitosa. Ingresa la coordenada X:")
            return COORD_X
        else:
            await update.message.reply_text("❌ Error de autenticación. Verifica tu usuario y contraseña.")
            return USER_EMAIL
    except Exception as e:
        await update.message.reply_text(f"❌ Error en autenticación: {e}")
        return USER_EMAIL

# Captura de datos del reporte
async def coord_x(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reporte_data["coordenada_x"] = update.message.text
    await update.message.reply_text("Ingresa la coordenada Y:")
    return COORD_Y

async def coord_y(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reporte_data["coordenada_y"] = update.message.text
    await update.message.reply_text("Describe el reporte:")
    return DESCRIPCION

async def descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reporte_data["descripcion"] = update.message.text
    await update.message.reply_text("Nombre de la calle:")
    return CALLE

async def calle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reporte_data["calleNombre"] = update.message.text
    await update.message.reply_text("Nombre de la colonia:")
    return COLONIA

async def colonia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reporte_data["coloniaNombre"] = update.message.text
    await update.message.reply_text("Envía una imagen o escribe 'omitir':")
    return IMAGEN

# Envío del reporte con imagen opcional
async def imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reporte_data["notificacionCorreo"] = "0"

    if not user_token:
        await update.message.reply_text("⚠️ Error: No hay un token de autenticación válido.")
        return ConversationHandler.END

    form_data = {
        "coordenada_x": (None, reporte_data["coordenada_x"]),
        "coordenada_y": (None, reporte_data["coordenada_y"]),
        "descripcion": (None, reporte_data["descripcion"]),
        "coloniaNombre": (None, reporte_data["coloniaNombre"]),
        "calleNombre": (None, reporte_data["calleNombre"]),
        "ciudadano": (None, reporte_data["ciudadano"]),
        "telefono": (None, reporte_data["telefono"]),
        "idUsuariosReporte": (None, str(reporte_data["idUsuariosReporte"])),
        "id_cat_reportes": (None, str(reporte_data["id_cat_reportes"])),
        "notificacionCorreo": (None, "0"),
    }

    try:
        if update.message.text and update.message.text.lower() == "omitir":
            await update.message.reply_text("📩 Enviando reporte sin imagen...")
            headers = {"Authorization": f"Bearer {user_token}"}
            response = requests.post(REPORT_URL, files=form_data, headers=headers)
        elif update.message.photo:
            file = await context.bot.get_file(update.message.photo[-1].file_id)
            filepath = "imagen_reporte.jpg"  # Asegúrate de que el archivo tenga una extensión válida
            await file.download_to_drive(filepath)

            with open(filepath, "rb") as image_file:
                # Combinar form_data y la imagen en un solo diccionario
                files = form_data
                files["imagen"] = (filepath, image_file, "image/jpeg")  # Especificar el tipo MIME
                await update.message.reply_text("📩 Enviando reporte con imagen...")

                headers = {"Authorization": f"Bearer {user_token}"}
                response = requests.post(REPORT_URL, files=files, headers=headers)
        else:
            await update.message.reply_text("⚠️ Opción no válida. Envía una imagen o escribe 'omitir'.")
            return IMAGEN

        # Verificar la respuesta del servidor
        if response.status_code in [200, 201]:  # Aceptar tanto 200 como 201
            response_data = response.json()
            if response_data.get("success", False):
                await update.message.reply_text(f"✅ Reporte creado con éxito. ID: {response_data.get('idreporte', 'Desconocido')}")
            else:
                await update.message.reply_text(f"⚠️ No se pudo enviar el reporte: {response_data.get('message', 'Error desconocido')}")
        else:
            await update.message.reply_text(f"⚠️ Error en el servidor: {response.status_code}, {response.text}")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error inesperado: {e}")
        logging.error(f"Error en el envío del reporte: {e}")

    return ConversationHandler.END

# Configuración del bot
def main():
    obtener_token_por_defecto()
    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CATEGORIA: [CallbackQueryHandler(categoria)],
            REPORT_TYPE: [CallbackQueryHandler(report_type)],
            USER_EMAIL: [MessageHandler(filters.TEXT, user_email)],
            USER_PASSWORD: [MessageHandler(filters.TEXT, user_password)],
            COORD_X: [MessageHandler(filters.TEXT, coord_x)],
            COORD_Y: [MessageHandler(filters.TEXT, coord_y)],
            DESCRIPCION: [MessageHandler(filters.TEXT, descripcion)],
            CALLE: [MessageHandler(filters.TEXT, calle)],
            COLONIA: [MessageHandler(filters.TEXT, colonia)],
            IMAGEN: [MessageHandler(filters.PHOTO | filters.TEXT, imagen)],
        },
        fallbacks=[],
    )

    application.add_handler(conv_handler)
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

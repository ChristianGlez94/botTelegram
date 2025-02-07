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
CATEGORIA, REPORT_TYPE, USER_EMAIL, USER_PASSWORD, COORDENADAS, DESCRIPCION, CALLE, COLONIA, IMAGEN = range(9)

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
        login_data = {"correo": "callcenter@gob.mx", "contrasena": "123456789"}
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
    # Mensaje de bienvenida
    welcome_message = (
        "¡Bienvenido al Sistema de Reportes Ciudadanos! 🏙️\n\n"
        "¿Qué es este servicio?\n"
        "Es una aplicación enlazada al Sistema Integral de Atención Ciudadana (SIAC) del Gobierno Municipal, "
        "mediante el cual los ciudadanos del Municipio de Ensenada pueden registrar sus peticiones de servicios, "
        "tales como: Recolección de Basura, Reparación de Alumbrado Público, Semáforos, etc.\n\n"
        "Mediante esta aplicación, las peticiones ciudadanas son gestionadas automáticamente a las Dependencias "
        "Municipales correspondientes, lo que implica que el seguimiento de su solicitud será generado directamente "
        "desde la Dependencia que tiene la capacidad de darle respuesta, y así dar solución a lo que el ciudadano nos solicita.\n\n"
        "**Pasos para realizar un reporte:**\n"
        "1. Selecciona la categoría del reporte.\n"
        "2. Elige si deseas reportar como anónimo o con usuario.\n"
        "3. Proporciona la ubicación del problema.\n"
        "4. Describe el problema.\n"
        "5. Proporciona detalles adicionales (calle, colonia).\n"
        "6. Adjunta una imagen (opcional).\n\n"
        "¡Comencemos! Selecciona la categoría del reporte:"
    )

    # Mostrar botones de categorías
    keyboard = [
        [InlineKeyboardButton("Bacheo", callback_data="16")],
        [InlineKeyboardButton("Recolección de basura", callback_data="23")],
        [InlineKeyboardButton("Alumbrado Público", callback_data="15")],
        [InlineKeyboardButton("Animales", callback_data="2")],
        [InlineKeyboardButton("Riesgo de estructuras", callback_data="10")],
        [InlineKeyboardButton("Poda de Árboles", callback_data="22")],
        
        
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Enviar mensaje de bienvenida y categorías
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)
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

        # Mostrar botón para seleccionar la ubicación manualmente
        keyboard = [[InlineKeyboardButton("📍 Seleccionar Ubicación", callback_data="seleccionar_ubicacion")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text("Selecciona la ubicación para el reporte:", reply_markup=reply_markup)
        return COORDENADAS

    elif choice == "con_usuario":
        await query.edit_message_text("Proporciona tu correo electrónico:")
        return USER_EMAIL

    else:
        await query.edit_message_text("Opción inválida. Selecciona una opción válida.")
        return REPORT_TYPE

# Captura de correo electrónico
async def user_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reporte_data["correo"] = update.message.text
    await update.message.reply_text("Proporciona tu contraseña:")
    return USER_PASSWORD

# Captura de contraseña y autenticación
async def user_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_token, user_id
    reporte_data["contrasena"] = update.message.text

    try:
        login_data = {"correo": reporte_data["correo"], "contrasena": reporte_data["contrasena"]}
        response = requests.post(LOGIN_URL, json=login_data)
        if response.status_code == 200:
            data = response.json()
            user_token = data.get("token")
            user_id = data.get("id")
            reporte_data["idUsuariosReporte"] = user_id
            reporte_data["ciudadano"] = ""
            reporte_data["telefono"] = ""

            # Mostrar botón para seleccionar la ubicación manualmente
            keyboard = [[InlineKeyboardButton("📍 Seleccionar Ubicación", callback_data="seleccionar_ubicacion")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text("Selecciona la ubicación para el reporte:", reply_markup=reply_markup)
            return COORDENADAS
        else:
            await update.message.reply_text("⚠️ Error en la autenticación. Verifica tus credenciales.")
            return USER_EMAIL
    except Exception as e:
        await update.message.reply_text("⚠️ Error inesperado. Intenta de nuevo.")
        logging.error(f"Error en la autenticación: {e}")
        return USER_EMAIL

# Captura de ubicación (cuando el usuario toca el botón "Seleccionar Ubicación")
async def solicitar_ubicacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Por favor, selecciona manualmente la ubicación en el mapa y envíala aquí.")
    return COORDENADAS

async def recibir_ubicacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.location:
        reporte_data["coordenada_x"] = str(update.message.location.latitude)
        reporte_data["coordenada_y"] = str(update.message.location.longitude)
        await update.message.reply_text("✅ Ubicación seleccionada correctamente.")
        await update.message.reply_text("Describe el reporte:")
        return DESCRIPCION
    else:
        await update.message.reply_text("⚠️ No se recibió una ubicación válida. Selecciona manualmente en el mapa y envíala aquí.")
        return COORDENADAS

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
    keyboard = [
        [InlineKeyboardButton("Omitir imagen", callback_data="omitir_imagen")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Envía una imagen o selecciona omitir:", reply_markup=reply_markup)
    return IMAGEN

# Envío del reporte con imagen opcional
async def imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reporte_data["notificacionCorreo"] = "0"

    if not user_token:
        await update.message.reply_text("⚠️ Error: No hay un token de autenticación válido.")
        return ConversationHandler.END

    form_data = {key: (None, str(value)) for key, value in reporte_data.items()}

    try:
        # Si se presionó el botón "Omitir imagen"
        if update.callback_query and update.callback_query.data == "omitir_imagen":
            await update.callback_query.answer()  # Responde a la interacción del botón
            await update.callback_query.message.reply_text("📩 Enviando reporte sin imagen...")
            headers = {"Authorization": f"Bearer {user_token}"}
            response = requests.post(REPORT_URL, files=form_data, headers=headers)

        # Si se envió una foto
        elif update.message and update.message.photo:
            file = await context.bot.get_file(update.message.photo[-1].file_id)
            filepath = "imagen_reporte.jpg"
            await file.download_to_drive(filepath)

            with open(filepath, "rb") as image_file:
                files = form_data.copy()
                files["imagen"] = (filepath, image_file, "image/jpeg")
                await update.message.reply_text("📩 Enviando reporte con imagen...")

                headers = {"Authorization": f"Bearer {user_token}"}
                response = requests.post(REPORT_URL, files=files, headers=headers)

        # Si no se envió una opción válida
        else:
            await update.message.reply_text("⚠️ Opción no válida. Envía una imagen o selecciona omitir.")
            return IMAGEN

        # Manejo de la respuesta del servidor
        if response.status_code in [200, 201]:
            response_data = response.json()
            if response_data.get("success", False):
                if update.callback_query:
                    await update.callback_query.message.reply_text(f"✅ Reporte creado con éxito. Clave: {response_data.get('idreporte', 'Desconocido')}")
                else:
                    await update.message.reply_text(f"✅ Reporte creado con éxito. ID: {response_data.get('idreporte', 'Desconocido')}")
            else:
                if update.callback_query:
                    await update.callback_query.message.reply_text(f"⚠️ No se pudo enviar el reporte: {response_data.get('message', 'Error desconocido')}")
                else:
                    await update.message.reply_text(f"⚠️ No se pudo enviar el reporte: {response_data.get('message', 'Error desconocido')}")
        else:
            if update.callback_query:
                await update.callback_query.message.reply_text(f"⚠️ Error en el servidor: {response.status_code}, {response.text}")
            else:
                await update.message.reply_text(f"⚠️ Error en el servidor: {response.status_code}, {response.text}")

    except Exception as e:
        # Manejo de errores
        if update.callback_query:
            await update.callback_query.message.reply_text(f"⚠️ Error inesperado: {e}")
        else:
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
            COORDENADAS: [CallbackQueryHandler(solicitar_ubicacion), MessageHandler(filters.LOCATION, recibir_ubicacion)],
            DESCRIPCION: [MessageHandler(filters.TEXT, descripcion)],
            CALLE: [MessageHandler(filters.TEXT, calle)],
            COLONIA: [MessageHandler(filters.TEXT, colonia)],
            IMAGEN: [CallbackQueryHandler(imagen, pattern="^omitir_imagen$"), MessageHandler(filters.PHOTO, imagen)],
        },
        fallbacks=[],
    )

    application.add_handler(conv_handler)
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

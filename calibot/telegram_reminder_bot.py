import asyncio
from datetime import datetime, timedelta
from pytz import utc
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackContext
from mycalendar.calendar_manager import GoogleCalendarManager
from telegram.ext import Application

# Constantes para los estados de la conversacion
TITLE, LOCATION, DESCRIPTION, DATE, START_TIME, END_TIME = range(6)

# Clase principal para gestionar recordatorios    
class ReminderHandler:
    def __init__(self, calendar_manager: GoogleCalendarManager):
        self.calendar_manager = calendar_manager

    async def monitor_reminders(self, context: CallbackContext):
        while True:
            try:
                # Obtiene eventos próximos desde Google Calendar
                events = self.calendar_manager.get_events()
                now = datetime.now(utc)  # Hora actual en UTC

                for event in events:
                    # Asegurarse de que start_time sea offset-aware
                    start_time = event.get('start', {}).get('dateTime')  # Manejar si falta el campo
                    if start_time:
                        start_time = datetime.fromisoformat(start_time)

                        if start_time.tzinfo is None:  # Si el datetime es naive
                            start_time = utc.localize(start_time)

                        # Comparar fechas correctamente
                        if now <= start_time <= now + timedelta(minutes=1):
                            chat_id = context.bot_data.get("user_chat_id")
                            if chat_id:
                                await context.bot.send_message(
                                    chat_id=chat_id,
                                    text=f"🔔 ¡Recordatorio! El evento '{event['summary']}' está comenzando ahora."
                                )
                            else:
                                print("⚠️ Chat ID no encontrado en bot_data.")
                    else:
                        print("⚠️ Evento sin 'start.dateTime'. Saltando...")

                # Espera 60 segundos antes de volver a verificar
                await asyncio.sleep(60)

            except Exception as e:
                print(f"❌ Error en monitor_reminders: {e}")
                await asyncio.sleep(60)  # Evitar ciclos rápidos en caso de error
        

    # Comando /start: Mensaje de bienvenida
    async def start(self, update: Update, context: CallbackContext):
        #Obtiene el primer nombre del usuario de telegram
        context.bot_data["user_chat_id"] = update.message.chat_id
        user_first_name = update.effective_user.first_name
        await update.message.reply_text(
            f"¡Bienvenido! 👋\n"
            "Usa /crear_recordatorio para añadir un nuevo recordatorio "
            "o /ver_recordatorios para ver tus próximos eventos."
        )

    # Método genérico para enviar respuestas
    async def send_reply(self, update: Update, text: str, parse_mode=None):
        """Envia una respuesta al usuario, evitando duplicación en el código."""
        await update.message.reply_text(text, parse_mode=parse_mode)     

    async def cancel(self, update: Update, context: CallbackContext):
        await update.message.reply_text("Operación cancelada. Si necesitas algo más, utiliza los comandos disponibles.")
        return ConversationHandler.END

    # Estado inicial de creación del recordatorio: pide el título
    async def start_create_reminder(self, update: Update, context: CallbackContext):
        await update.message.reply_text(f"🔔 Por favor, ingresa el título del recordatorio:")
        return TITLE

    # Estado TITLE: Guarda el título ingresado y pide la ubicación
    async def receive_title(self, update: Update, context: CallbackContext):
        context.user_data['title'] = update.message.text
        await update.message.reply_text(
            f"📌 **Título recibido:** {context.user_data['title']}\n"
            "Por favor, ingresa la ubicación del recordatorio (o escribe 'Ninguna' si no aplica):",
            parse_mode="Markdown"
        )
        return LOCATION

    # Estado LOCATION: Guarda la ubicación y pide una descripción
    async def receive_location(self, update: Update, context: CallbackContext):
        context.user_data['location'] = update.message.text
        await update.message.reply_text(
            f"📍 **Ubicación recibida:** {context.user_data['location']}\n"
            "Ingresa una breve descripción del recordatorio:",
            parse_mode="Markdown"
        )
        return DESCRIPTION

    # Estado DESCRIPTION: Guarda la descripción y pide la fecha
    async def receive_description(self, update: Update, context: CallbackContext):
        context.user_data['description'] = update.message.text
        await update.message.reply_text(
            f"📝 **Descripción recibida:** {context.user_data['description']}\n"
            "Ingresa la fecha del recordatorio en el formato **DD-MM-YYYY**:",
            parse_mode="Markdown"
        )
        return DATE

    # Estado DATE: Guarda la fecha si es válida y pide la hora de inicio
    async def receive_date(self, update: Update, context: CallbackContext):
        try:
            # Convertir la fecha al formato convencional
            datetime.strptime(update.message.text, '%d-%m-%Y')
            context.user_data['date'] = update.message.text
            await update.message.reply_text(
                f"📅 **Fecha recibida:** {context.user_data['date']}\n"
                "Ingresa la hora de inicio en el formato **HH:MM**:",
                parse_mode="Markdown"
            )
            return START_TIME
        except ValueError:
            await update.message.reply_text("❌ Formato de fecha inválido. Usa DD-MM-YYYY.")
            return DATE

    # Estado START_TIME: Guarda la hora de inicio si es válida y pide la hora de fin
    async def receive_start_time(self, update: Update, context: CallbackContext):
        try:
            datetime.strptime(update.message.text, '%H:%M')
            context.user_data['start_time'] = update.message.text
            await update.message.reply_text(
                f"⏰ **Hora de inicio recibida:** {context.user_data['start_time']}\n"
                "Ingresa la hora de fin en el formato **HH:MM**:",
                parse_mode="Markdown"
            )
            return END_TIME
        except ValueError:
            await update.message.reply_text("❌ Formato de hora inválido. Usa HH:MM.")
            return START_TIME

    # Estado END_TIME: Finaliza la creación del recordatorio y lo guarda en Google Calendar
    async def receive_end_time(self, update: Update, context: CallbackContext):
        try:
            datetime.strptime(update.message.text, '%H:%M')
            context.user_data['end_time'] = update.message.text

            # Convierte la fecha y hora al formato ISO para Google Calendar
            date_parts = context.user_data['date'].split('-')  # DD-MM-YYYY -> YYYY-MM-DD
            formatted_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
            start_datetime = f"{formatted_date}T{context.user_data['start_time']}:00"
            end_datetime = f"{formatted_date}T{context.user_data['end_time']}:00"

            # Crea el evento en Google Calendar
            event_id = self.calendar_manager.create_event(
                title=context.user_data['title'],
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                location=context.user_data.get('location'),
                description=context.user_data.get('description'),
            )

            # Responde al usuario según el resultado
            if event_id:
                await update.message.reply_text(f"✅ Recordatorio creado con éxito:\n"
                                               f"**Título:** {context.user_data['title']}\n"
                                               f"**Ubicación:** {context.user_data['location']}\n"
                                               f"**Descripción:** {context.user_data['description']}\n"
                                               f"**Fecha:** {context.user_data['date']}\n"
                                               f"**Hora de inicio:** {context.user_data['start_time']}\n"
                                               f"**Hora de fin:** {context.user_data['end_time']}",
                                               parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("❌ Ocurrió un error al intentar crear el recordatorio. Por favor, intenta nuevamente.")

            return ConversationHandler.END
        except ValueError:
            await update.message.reply_text("Formato de hora inválido. Usa HH:MM.")
            return END_TIME

    # Comando /ver_recordatorios: Lista los próximos eventos
    async def list_reminders(self, update: Update, context: CallbackContext):
        #Obtiene el primer nombre del usuario de telegram
        user_first_name = update.effective_user.first_name
        events = self.calendar_manager.get_events()
        if not events:
            await update.message.reply_text("No hay recordatorios próximos. 😔")
        else:
            response = f"Hola, tus próximos recordatorios son:\n"
            for event in events:
                start = datetime.fromisoformat(event['start']['dateTime']).strftime('%d-%m-%Y %H:%M')
                end = datetime.fromisoformat(event['end']['dateTime']).strftime('%H:%M')
                response += (f"- {event['summary']} (Ubicación: {event.get('location', 'No especificada')})\n"
                             f"  {start} a {end}\n")
            await update.message.reply_text(response)

# Clase principal del bot de Telegram
class TelegramReminderBot:
    def __init__(self, token):
        self.application = Application.builder().token(token).build()
        self.reminder_handler = ReminderHandler(GoogleCalendarManager())
        self.setup_handlers()

    async def set_user_chat_id(self, application):
        updates = await application.bot.get_updates()
        if updates:
            return updates[0].message.chat_id
        return None
        
    # Configura los comandos y manejadores
    def setup_handlers(self):
        # Manejador de conversacion para crear recordatorios
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('crear_recordatorio', self.reminder_handler.start_create_reminder)],
            states={
                TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.reminder_handler.receive_title)],
                LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.reminder_handler.receive_location)],
                DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.reminder_handler.receive_description)],
                DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.reminder_handler.receive_date)],
                START_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.reminder_handler.receive_start_time)],
                END_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.reminder_handler.receive_end_time)],
            },
            fallbacks=[CommandHandler('cancelar', self.reminder_handler.cancel)],
        )
        # Añade el manejador de conversación y otros comandos a la aplicación
        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler('start', self.reminder_handler.start))
        self.application.add_handler(CommandHandler('ver_recordatorios', self.reminder_handler.list_reminders))

    # Inicia el bot     
    async def start_bot(self):
        user_chat_id = await self.set_user_chat_id(self.application)   # Llamamos al método aquí
        print(f"User Chat ID: {user_chat_id}")

        asyncio.create_task(self.reminder_handler.monitor_reminders(self.application))

        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        try:
            await asyncio.Future()  # Mantén la aplicación corriendo
        except KeyboardInterrupt:
            await self.application.shutdown()

    # Ejecutar el flujo principal en un único bucle de eventos
          
 
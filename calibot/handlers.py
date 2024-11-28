from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from datetime import datetime

class ReminderHandler:
    # Constantes que representan los estados de la conversación
    TITLE, LOCATION, DESCRIPTION, DATE, START_TIME, END_TIME = range(6)

    # Constructor: inicializa con un gestor de Google Calendar
    def __init__(self, calendar_manager):
        self.calendar_manager = calendar_manager

    # Comando /start
    async def start(self, update: Update, context: CallbackContext):
        #Obtiene el primer nombre del usuario de telegram
        user_first_name = update.effective_user.first_name
        await update.message.reply_text(
            f"¡Bienvenido, {user_first_name}! 👋\n"
            "Usa /crear_recordatorio para añadir un nuevo recordatorio "
            "o /ver_recordatorios para ver tus próximos eventos."
        )

    # Comando para cancelar la operación en cualquier punto del flujo
    async def cancel(self, update: Update, context: CallbackContext):
        await update.message.reply_text("Operación cancelada. Si necesitas algo más, utiliza los comandos disponibles.")
        return ConversationHandler.END             

    # Paso 1: Inicia el flujo para crear un recordatorio y solicita el título
    async def start_create_reminder(self, update: Update, context: CallbackContext):
        await update.message.reply_text(f"🔔 Por favor, ingresa el título del recordatorio:")
        return self.TITLE

    # Paso 2: Recibe el título ingresado por el usuario
    async def receive_title(self, update: Update, context: CallbackContext):
        context.user_data['title'] = update.message.text
        await update.message.reply_text(
            f"📌 **Título recibido:** {context.user_data['title']}\n"
            "Por favor, ingresa la ubicación del recordatorio (o escribe 'Ninguna' si no aplica):",
            parse_mode="Markdown"
        )
        return self.LOCATION

    # Paso 3: Recibe la ubicación del recordatorio
    async def receive_location(self, update: Update, context: CallbackContext):
        context.user_data['location'] = update.message.text
        await update.message.reply_text(
            f"📍 **Ubicación recibida:** {context.user_data['location']}\n"
            "Ingresa una breve descripción del recordatorio:",
            parse_mode="Markdown"
        )
        return self.DESCRIPTION

    # Paso 4: Recibe la descripción del recordatorio
    async def receive_description(self, update: Update, context: CallbackContext):
        context.user_data['description'] = update.message.text
        await update.message.reply_text(
            f"📝 **Descripción recibida:** {context.user_data['description']}\n"
            "Ingresa la fecha del recordatorio en el formato **DD-MM-YYYY**:",
            parse_mode="Markdown"
        )
        return self.DATE

    # Paso 5: Valida y almacena la fecha ingresada
    async def receive_date(self, update: Update, context: CallbackContext):
        try:
            datetime.strptime(update.message.text, '%d-%m-%Y')
            context.user_data['date'] = update.message.text
            await update.message.reply_text(
                f"📅 **Fecha recibida:** {context.user_data['date']}\n"
                "Ingresa la hora de inicio en el formato **HH:MM**:",
                parse_mode="Markdown"
            )
            return self.START_TIME
        except ValueError:
            await update.message.reply_text("❌ Formato de fecha inválido. Usa DD-MM-YYYY.")
            return self.DATE

    # Paso 6: Valida y almacena la hora de inicio
    async def receive_start_time(self, update: Update, context: CallbackContext):
        try:
            datetime.strptime(update.message.text, '%H:%M')
            context.user_data['start_time'] = update.message.text
            await update.message.reply_text(
                f"⏰ **Hora de inicio recibida:** {context.user_data['start_time']}\n"
                "Ingresa la hora de fin en el formato **HH:MM**:",
                parse_mode="Markdown"
            )
            return self.END_TIME
        except ValueError:
            await update.message.reply_text("❌ Formato de hora inválido. Usa HH:MM.")
            return self.START_TIME

    # Paso 7: Valida la hora de fin, crea el evento en Google Calendar y confirma al usuario
    async def receive_end_time(self, update: Update, context: CallbackContext):
        try:
            datetime.strptime(update.message.text, '%H:%M') # Valida el formato
            context.user_data['end_time'] = update.message.text

            # Formatea la fecha y hora para Google Calendar
            date_parts = context.user_data['date'].split('-')  # DD-MM-YYYY -> YYYY-MM-DD
            formatted_date = f"{date_parts[2]}-{date_parts[1]}-{date_parts[0]}"
            start_datetime = f"{formatted_date}T{context.user_data['start_time']}:00"
            end_datetime = f"{formatted_date}T{context.user_data['end_time']}:00"

            # Crea el evento en Google Calendar usando el gestor
            event_id = self.calendar_manager.create_event(
                title=context.user_data['title'],
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                location=context.user_data.get('location'),
                description=context.user_data.get('description'),
            )

            # Mensaje de confirmación o error según el resultado
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
            return self.END_TIME

    # Comando para listar los próximos recordatorios
    async def list_reminders(self, update: Update, context: CallbackContext):
        user_first_name = update.effective_user.first_name
        events = self.calendar_manager.get_events()
        if not events:
            await update.message.reply_text("No hay recordatorios próximos. 😔")
        else:
            # Construye una lista de eventos próximos
            response = f"Hola {user_first_name}, tus próximos recordatorios son:\n"
            for event in events:
                start = datetime.fromisoformat(event['start']['dateTime']).strftime('%d-%m-%Y %H:%M')
                end = datetime.fromisoformat(event['end']['dateTime']).strftime('%H:%M')
                response += (f"- {event['summary']} (Ubicación: {event.get('location', 'No especificada')})\n"
                            f"  {start} a {end}\n")
            await update.message.reply_text(response)

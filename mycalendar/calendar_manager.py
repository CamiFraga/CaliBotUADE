import os
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Alcances necesarios para acceder a Google Calendar (lectura y escritura)
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Clase para gestionar la integración con Google Calendar
class GoogleCalendarManager:
    def __init__(self):
        # Inicializa el servicio de Google Calendar
        self.service = self.get_calendar_service()

    # Método para obtener las credenciales y conectar con la API de Google Calendar
    def get_calendar_service(self):
        creds = None
        # Ruta al archivo con las credenciales del cliente
        credentials_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'credentials.json')
        # Si existe un token previamente generado, se usa
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # Si las credenciales no son válidas o no existen, se solicita al usuario autenticarse
        if not creds or not creds.valid:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path , SCOPES)
            creds = flow.run_local_server(port=0) # Abre una ventana local para que el usuario inicie sesión
            # Guarda el token generado para futuros usos
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        # Devuelve un servicio de Google Calendar listo para usar          
        return build('calendar', 'v3', credentials=creds)

    # Método para crear un evento en Google Calendar
    def create_event(self, title, start_datetime, end_datetime, location=None, description=None):
        # Define el evento con sus datos básicos
        event = {
            'summary': title,
            'start': {
                'dateTime': start_datetime,
                'timeZone': 'America/Buenos_Aires',
            },
            'end': {
                'dateTime': end_datetime,
                'timeZone': 'America/Buenos_Aires',
            },
        }
        # Agrega la ubicación si se proporcionó
        if location:
            event['location'] = location
        # Agrega la descripción si se proporcionó     
        if description:
            event['description'] = description

        # Inserta el evento en el calendario principal del usuario
        event = self.service.events().insert(calendarId='primary', body=event).execute()
        # Devuelve el ID del evento creado
        return event['id']

    # Método para obtener los próximos eventos del calendario
    def get_events(self):
        # Obtiene la fecha y hora actuales en formato ISO
        now = datetime.utcnow().isoformat() + 'Z' # La 'Z' indica hora UTC
        # Solicita los próximos 10 eventos, ordenados por fecha de inicio
        events_result = self.service.events().list(
            calendarId='primary', # ID del calendario principal
            timeMin=now, # Solo eventos futuros
            maxResults=10, # Máximo 10 eventos
            singleEvents=True, # Dividir eventos recurrentes en instancias individuales
            orderBy='startTime' # Ordenar por tiempo de inicio
        ).execute()
        # Devuelve la lista de eventos (si no hay eventos, retorna una lista vacía)
        return events_result.get('items', [])

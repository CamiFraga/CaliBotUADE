from calibot.telegram_reminder_bot import TelegramReminderBot
import asyncio

async def main():
    # Token del bot de Telegram, necesario para autenticarse con la API
    
    token = '7833725318:AAEM5cfFCHxrl5zx9IeITm9Y5S0tUpZ2eZc'
    bot = TelegramReminderBot(token)
    user_chat_id = await bot.set_user_chat_id(bot.application)
    print(f"Chat ID guardado: {user_chat_id}")

    # Creacion de una instancia del bot usando el token
    
    # Inicia el bot en modo "polling" (escucha continuamente los mensajes)
    await bot.start_bot()

if __name__ == '__main__':
    asyncio.run(main())
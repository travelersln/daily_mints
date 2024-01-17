import os
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
import re
from reminder_tasks import setup_tasks, ReminderView
import logging

# Configuración del logging
logging.basicConfig(level=logging.ERROR,  # Nivel DEBUG para obtener más detalles durante la depuración
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S',
                    filename='bot_error.log',  # Archivo de logs
                    filemode='a')

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logging.getLogger('').addHandler(console_handler)

# Obtén el logger específico para el cliente de Discord
logger = logging.getLogger('discord.client')

# Carga las variables de entorno
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
id_canal_origen = int(os.getenv('ID_CANAL_ORIGEN'))
ids_canales_destino = [
    int(os.getenv('ID_CANAL_DESTINO1')),
    int(os.getenv('ID_CANAL_DESTINO2')),
    # Añade aquí más canales si los necesitas
]

# Configuración del bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Manejador para errores generales no capturados en eventos
@bot.event
async def on_error(event, *args, **kwargs):
    logger.exception(f'Error no manejado en {event}')

# Manejador para errores de comandos
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        # Puedes ignorar los errores de comandos no encontrados o enviar un mensaje de ayuda
        return
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f'This command is on cooldown. Please try again later.')
    else:
        logger.exception(f'Unhandled command error: {error}')

@bot.event
async def on_ready():
    logger.info(f'Bot logged in as {bot.user.name}')
    setup_tasks(bot)

@bot.event
async def on_message(message):
    logger.debug('Received a message.')
    if message.author == bot.user or message.channel.id != id_canal_origen:
        logger.debug('Message is from the bot itself or not from the origin channel, ignoring.')
        return
    
    embed = discord.Embed(color=discord.Color.blue())
    bloques = re.split(r'(\[tituloinicio\].*?\[titulofin\])', message.content, flags=re.DOTALL)
    eventos_para_botones = []

    for bloque in bloques:
        if '[tituloinicio]' in bloque and '[titulofin]' in bloque:
            titulo = re.search(r'\[tituloinicio\](.*?)\[titulofin\]', bloque).group(1)
            embed.add_field(name=titulo, value='', inline=False)
        else:
            eventos = re.split(r'(\[evento\d+\])', bloque, flags=re.DOTALL)
            for i in range(1, len(eventos), 2):
                evento_texto = eventos[i + 1].strip()
                evento_texto = re.sub(r'(\[evento\d+\])\s+(\S+)', r'\1 **\2**', evento_texto)
                
                if '[remember]' in evento_texto:
                    eventos_para_botones.append(evento_texto)
                    evento_texto = evento_texto.replace('[remember]', '').strip()
                
                evento_texto = re.sub(r'\[linki\](https?://[^\s\[]+)\[linke\](\S+)', r'[\2](\1)', evento_texto)
                evento_texto = evento_texto.replace(')(', ') - (')
                embed.add_field(name='', value=evento_texto, inline=False)

    view = ReminderView(eventos_para_botones) if eventos_para_botones else None

    # Envía el mensaje a todos los canales de destino
    for id_canal in ids_canales_destino:
        canal_destino = bot.get_channel(id_canal)
        if canal_destino:  # Verifica si el canal existe
            await canal_destino.send(embed=embed, view=view)
        else:
            logger.error(f"No se encontró el canal con ID {id_canal}")

    await bot.process_commands(message)

# Iniciar el bot
bot.run(TOKEN)

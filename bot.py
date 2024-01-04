import os
from dotenv import load_dotenv
import discord
from discord.ext import commands
import re
from reminder_tasks import setup_tasks, ReminderView
import logging

# Configuración del logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger('bot')

# Carga las variables de entorno
load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
id_canal_origen = int(os.getenv('ID_CANAL_ORIGEN'))
ids_canales_destino = [
    int(os.getenv('ID_CANAL_DESTINO1')),  # Asegúrate de tener esta variable en tu .env
    int(os.getenv('ID_CANAL_DESTINO2')),  # Asegúrate de tener esta variable en tu .env
    # Puedes agregar más canales aquí, asegurándote de que también estén en tu archivo .env
]

# Configuración del bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'Hemos iniciado sesión como {bot.user}')
    setup_tasks(bot)
    logger.info("Tasks have been set up.")

@bot.event
async def on_message(message):
    if message.author == bot.user or message.channel.id != id_canal_origen:
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

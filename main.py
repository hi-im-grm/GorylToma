import discord
import random
import logging
import json
import os
import sys
from discord.ext import commands

# Constants
PARTICIPANTS_FILE = "participants.json"
TWITCH_URL = "https://www.twitch.tv/xtom223"  # Replace with your Twitch URL

# Intents to allow the bot to read message content and reactions
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

# Create the bot instance
bot = commands.Bot(command_prefix="g?", intents=intents)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Helper functions
def load_participants():
    """Load participants from the JSON file."""
    if os.path.exists(PARTICIPANTS_FILE):
        try:
            with open(PARTICIPANTS_FILE, "r") as f:
                data = f.read().strip()
                return json.loads(data) if data else []
        except json.JSONDecodeError:
            logging.warning(f"{PARTICIPANTS_FILE} is corrupted. Initializing as an empty list.")
    return []

def save_participants(data):
    """Save participants to the JSON file."""
    with open(PARTICIPANTS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Initialize participants data
participants_data = load_participants()
contest_channel_id = None

# Events
@bot.event
async def on_ready():
    """Triggered when the bot is ready."""
    print(f"Bot is ready! Logged in as {bot.user}")
    activity = discord.Streaming(name="xToM223!", url=TWITCH_URL)
    await bot.change_presence(activity=activity)

@bot.event
async def on_reaction_add(reaction, user):
    """Track reactions in the contest channel."""
    global participants_data

    # Sprawdź, czy reakcja jest w kanale konkursowym
    if contest_channel_id and reaction.message.channel.id == contest_channel_id:
        # Sprawdź, czy reakcja to ✅ i czy użytkownik, który dodał reakcję, nie jest botem
        if reaction.emoji == "✅" and not user.bot:
            # Pobierz ID autora wiadomości, na którą dodano reakcję
            message_author_id = str(reaction.message.author.id)

            # Dodaj ID autora wiadomości do listy uczestników, jeśli jeszcze go tam nie ma
            if message_author_id not in participants_data:
                participants_data.append(message_author_id)
                save_participants(participants_data)
                logging.info(f"Dodano użytkownika {message_author_id} do listy uczestników.")

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands."""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required argument!")
    elif isinstance(error, commands.NotOwner):
        await ctx.send("❌ You do not have permission to use this command!")
    else:
        logging.error(f"An error occurred: {error}")
        await ctx.send("❌ An unexpected error occurred. Check logs for details.")

# Commands

@bot.command() 
@commands.is_owner()
async def reload(ctx):
    """Reload the entire bot."""
    await ctx.send("🔄 Przeładowuję bota...")
    logging.info("Reloading the bot...")
    await bot.close()  # Zamknij obecny proces bota
    os.execv(sys.executable, ['python'] + sys.argv)  # Uruchom ponownie bota

@bot.command()
async def konkurs(ctx, channel_id: int = None):
    """Start a contest and select a channel by mention or ID."""
    global contest_channel_id

    if channel_id:
        # Ustaw kanał konkursowy na podstawie ID
        channel = bot.get_channel(channel_id)
        if not channel:
            await ctx.send("❌ Nie znaleziono kanału o podanym ID. Upewnij się, że bot ma dostęp do tego kanału.")
            return

        contest_channel_id = channel_id
        await ctx.send(f"Konkurs został ustawiony na kanale {channel.mention}.")
    else:
        # Poproś użytkownika o oznaczenie kanału
        await ctx.send("Wybierz kanał, na którym ma odbyć się konkurs. Oznacz kanał używając `#`.")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and len(m.channel_mentions) > 0

        try:
            msg = await bot.wait_for("message", check=check, timeout=30.0)
            contest_channel_id = msg.channel_mentions[0].id
            await ctx.send(f"Konkurs został ustawiony na kanale {msg.channel_mentions[0].mention}.")
        except Exception as e:
            await ctx.send("❌ Nie wybrano kanału w odpowiednim czasie. Spróbuj ponownie.")
            logging.error(f"Error selecting contest channel: {e}")

@bot.command()
async def wynik(ctx):
    """Pick a winner from the participants."""
    if not participants_data:
        await ctx.send("❌ Brak uczestników w konkursie!")
        return

    winner_id = random.choice(participants_data)
    winner = await bot.fetch_user(int(winner_id))
    await ctx.send(f"🎉 Zwycięzcą konkursu jest {winner.mention}! Gratulacje! 🎉")

    participants_data.clear()
    save_participants(participants_data)
    await ctx.send("Dane uczestników zostały usunięte.")

@bot.command()
async def analizuj(ctx, channel_id: int):
    """Analyze past messages on a channel and save user IDs of message authors with ✅ reactions."""
    channel = bot.get_channel(channel_id)
    if not channel:
        await ctx.send("❌ Nie znaleziono kanału o podanym ID. Upewnij się, że bot ma dostęp do tego kanału.")
        return

    await ctx.send(f"Analizuję wiadomości na kanale {channel.mention}...")

    try:
        async for message in channel.history(limit=100):
            for reaction in message.reactions:
                if reaction.emoji == "✅":
                    # Dodaj ID autora wiadomości, jeśli reakcja to ✅
                    message_author_id = str(message.author.id)
                    if message_author_id not in participants_data:
                        participants_data.append(message_author_id)

        save_participants(participants_data)
        await ctx.send("✅ Analiza zakończona. Dane zostały zapisane.")
    except Exception as e:
        await ctx.send("❌ Wystąpił błąd podczas analizy. Spróbuj ponownie.")
        logging.error(f"Error analyzing messages: {e}")

@bot.command()
async def sledz(ctx, channel_id: int):
    """Start tracking a channel for messages with ✅ reactions."""
    global contest_channel_id

    channel = bot.get_channel(channel_id)
    if not channel:
        await ctx.send("❌ Nie znaleziono kanału o podanym ID. Upewnij się, że bot ma dostęp do tego kanału.")
        return

    contest_channel_id = channel_id
    await ctx.send(f"Śledzenie zostało rozpoczęte na kanale {channel.mention}.")

@bot.command()
async def losuj(ctx, channel_id: int):
    """Pick a random winner and announce it on the specified channel."""
    if not participants_data:
        await ctx.send("❌ Brak uczestników w konkursie!")
        return

    channel = bot.get_channel(channel_id)
    if not channel:
        await ctx.send("❌ Nie znaleziono kanału o podanym ID. Upewnij się, że bot ma dostęp do tego kanału.")
        return

    winner_id = random.choice(participants_data)
    winner = await bot.fetch_user(int(winner_id))
    await channel.send(f"🎉 Zwycięzcą konkursu jest {winner.mention}! Gratulacje! 🎉")

    participants_data.clear()
    save_participants(participants_data)
    await ctx.send("Dane uczestników zostały usunięte.")

@bot.command()
async def liczba(ctx):
    """Count the number of saved user IDs in the participants.json file."""
    count = len(participants_data)
    await ctx.send(f"📊 Aktualna liczba uczestników: {count}")

# Run the bot
bot.run("MTM1NTYwMjAzNjc4NzI1MzMzMA.GPhg1r.rKXpqG-edK2AryNpyGDOZCAMzCHk6gYZ54tV2M")  # Replace with your bot token
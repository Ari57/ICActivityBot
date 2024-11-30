import logging
import discord
import gspread
import os
import json
import sys
from discord.ext import commands
from dotenv import load_dotenv
from gspread import service_account
from google.oauth2 import service_account
from datetime import datetime

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_SHEET_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
ALLOWED_USER_IDS = [163199994919256064]

IC_ROSTER_SHEET_NAME = "Roster"
IC_SHEET_ID = "1GeG5jWsVWNf-FF9Wx1JAbkMpsEX6yK5hBgwsEljLNLM"

testing = sys.argv[1]

if testing == "Y":
    CHANNEL_NAME = "ic-bot-testing"
else:
    CHANNEL_NAME = "activity-warnings"

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
logging.basicConfig(level=logging.INFO)

def GetGoogleSheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        CredsInfo = json.loads(GOOGLE_SHEET_CREDENTIALS)
        creds = service_account.Credentials.from_service_account_info(CredsInfo, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(IC_SHEET_ID).worksheet(IC_ROSTER_SHEET_NAME)
        return sheet
    except Exception as e:
        logging.error(f"Error accessing Google Sheet: {e}")
        return None

def CheckLoa():
    sheet = GetGoogleSheet()
    names = []
    rows = sheet.get_all_values()

    for row in rows:
        name = row[6]
        loa = row[17]
        if name != "" and name != "Name" and name != "dont delete":
            if loa != "ROA" and loa != "LOA":
                names.append(name)

    return names

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    await check_activity()
    await bot.close()

@bot.command(name="shutdown")
@commands.is_owner()
async def shutdown(ctx):
    if ctx.author.id in ALLOWED_USER_IDS:
        await ctx.send("Shutting down the bot")
        await bot.close()
    else:
        await ctx.send("You don't have permission to shut down the bot")

async def check_activity():
    sheet = GetGoogleSheet()
    NameColumn = sheet.col_values(7)
    DiscordIDColumn = sheet.col_values(9) # TODO discord id is missing atm
    print(DiscordIDColumn)
    LastSeenColumn = sheet.col_values(13)
    CurrentDate = datetime.today()

    NonLoaNames = CheckLoa()

    OverFiveDays = []
    FiveDays = []
    FourDays = []
    ThreeDays = []

    for name, DiscordId, lastSeen in zip(NameColumn, DiscordIDColumn, LastSeenColumn):
        if name != "" and name != "Name" and name != "dont delete":
            if lastSeen != "" and lastSeen != "Last Seen":
                if name not in NonLoaNames:
                    continue

                try:
                    LastSeen = datetime.strptime(lastSeen, "%d/%m/%Y")
                    DaysSince = (CurrentDate - LastSeen).days

                    if DaysSince > 5:
                        OverFiveDays.append(f"<@{DiscordId}>")
                    elif DaysSince == 5:
                        FiveDays.append(f"<@{DiscordId}>")
                    elif DaysSince == 4:
                        FourDays.append(f"<@{DiscordId}>")
                    elif DaysSince == 3:
                        ThreeDays.append(f"<@{DiscordId}>")

                except Exception as e:
                    logging.error(f"Unable to convert DaysSince value for {name}: {e}")

    output = []

    if ThreeDays:
        output.append(f"2 days: {' '.join(ThreeDays)}")
    if FourDays:
        output.append(f"1 day: {' '.join(FourDays)}")
    if FiveDays:
        output.append(f"0 days: {' '.join(FiveDays)}")
    if OverFiveDays:
        output.append(f"Inactive: {' '.join(OverFiveDays)}")

    if output:
        response = "\n".join(output)
        channel = discord.utils.get(bot.get_all_channels(), name=CHANNEL_NAME)
        if channel:
            message = f"\n{response}\n\nPlease participate in an event or training to update your activity, if there are any problems DM a member of the IC Officer team\n"
            await channel.send(message)
        else:
            logging.error(f"Unable to find channel: {CHANNEL_NAME}")

bot.run(DISCORD_TOKEN)

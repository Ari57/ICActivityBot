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
        loa = row[18]
        if name != "" and name != "Name" and name != "dont delete":
            if loa == "ROA" or loa == "LOA":
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
    DiscordIDColumn = sheet.col_values(11)
    LastSeenColumn = sheet.col_values(14)
    CurrentDate = datetime.today()

    LoaNames = CheckLoa()

    LessZeroDays = []
    ZeroDays = []
    OneDay = []
    TwoDays = []

    for name, DiscordId, lastSeen in zip(NameColumn, DiscordIDColumn, LastSeenColumn):
        if name != "" and name != "Name" and name != "dont delete":
            if lastSeen != "" and lastSeen != "Last Seen":
                if name in LoaNames:
                    continue

                try:
                    LastSeen = datetime.strptime(lastSeen, "%d/%m/%Y")
                    DaysSince = (CurrentDate - LastSeen).days
                    Inactivity = 6 - DaysSince # same formula as spreadsheet, don't know why it's like this

                    if Inactivity < 0:
                        LessZeroDays.append(f"<@{DiscordId}>")
                    elif Inactivity == 0:
                        ZeroDays.append(f"<@{DiscordId}>")
                    elif Inactivity == 1:
                        OneDay.append(f"<@{DiscordId}>")
                    elif Inactivity == 2:
                        TwoDays.append(f"<@{DiscordId}>")

                except Exception as e:
                    logging.error(f"Unable to convert DaysSince value for {name}: {e}")

    output = []

    if TwoDays:
        output.append(f"2 days: {' '.join(TwoDays)}")
    if OneDay:
        output.append(f"1 day: {' '.join(OneDay)}")
    if ZeroDays:
        output.append(f"0 days: {' '.join(ZeroDays)}")
    if LessZeroDays:
        output.append(f"Removed Troopers: {' '.join(LessZeroDays)}")

    if output:
        response = "\n".join(output)
        channel = discord.utils.get(bot.get_all_channels(), name=CHANNEL_NAME)
        if channel:
            message = f"\n{response}\n\n:warning: If you've been tagged, you're running low on activity days. Jump into an event or training session soon to avoid being marked as inactive and potentially demoted and put on passive.\n"
            await channel.send(message)
        else:
            logging.error(f"Unable to find channel: {CHANNEL_NAME}")

bot.run(DISCORD_TOKEN)

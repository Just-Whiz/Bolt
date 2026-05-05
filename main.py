# Bot name: Bolt
# Author: orbandit (@just_whiz on Discord)
# Date: 2026-05-05
# Description: Discord message logger that logs to Google Sheets
# Version: 0.1.0


# Import essential libraries for the bot's functions (e.g. discord, logging, os, dotenv for environment variables, gspread and google-auth for Google Sheets integration). These libraries provide the necessary tools to create a Discord bot, handle logging, manage environment variables securely, and interact with Google Sheets for data storage.
import discord
from discord.ext import commands
import logging
import os
from dotenv import load_dotenv
from datetime import timezone
import gspread
from google.oauth2.service_account import Credentials

# Load environment variables from a .env file, which is commonly used to store sensitive information like API tokens. This allows you to keep your Discord token secure and not hard-code it into your script. The load_dotenv() function reads the .env file and makes the variables available in the environment, allowing you to access them using os.getenv().
load_dotenv() # Loads environment variables from a .env file into the system's environment variables, making them accessible via os.getenv() in the code. This is a common practice for managing sensitive information like API keys and tokens without hardcoding them into the source code.

# Retrieves variables from the .env file (stored seperately for security reasons) and assigns them to Python variables. These variables include the Discord bot token, the path to the Google credentials JSON file, the ID of the Google Spreadsheet, and the name of the sheet within the spreadsheet where logs will be stored. By using environment variables, you can keep sensitive information secure and easily change configurations without modifying the code.
token = os.getenv('DISCORD_TOKEN') # Retrieves the Discord bot token from the environment variables, which is necessary for authenticating the bot with the Discord API.
CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json') # Retrieves the path to the Google credentials JSON file from the environment variables, with a default value of 'credentials.json' if the variable is not set. This file contains the necessary credentials for authenticating with the Google Sheets API.
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID') # Retrieves the ID of the Google Spreadsheet from the environment variables, which is needed to specify which spreadsheet the bot will log messages to. The SPREADSHEET_ID is a unique identifier for the spreadsheet and can be found in the URL of the Google Sheet.
LOG_SHEET_NAME = os.getenv('LOG_SHEET_NAME', 'Garde Nationale Test Example') # Retrieves the name of the sheet within the Google Spreadsheet where logs will be stored from the environment variables, with a default value of 'Garde Nationale Test Example' if the variable is not set. This allows you to specify which sheet in the spreadsheet will be used for logging messages.

# Google Sheet setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

class SheetsLogger:
    def __init__(self, credentials_path: str, spreadsheet_id: str, sheet_name: str):
        """
        This class function handles authentication with the Google Sheets API using a service account and sets up the connection to the specified spreadsheet and sheet. It uses the gspread library to authorize access to the Google Sheets API with the provided credentials and opens the specified spreadsheet and worksheet for logging messages. The credentials are loaded from a JSON file, and the necessary scopes for accessing spreadsheets 
        and drive are defined to ensure proper permissions for reading and writing data to the Google Sheet.
        """
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        client = gspread.authorize(creds)
        self.sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)

    def log_message(self, message: discord.Message):
        """Extract all desired fields and append a row to the sheet."""

        # Timestamp in UTC ISO format
        timestamp = message.created_at.replace(tzinfo=timezone.utc).isoformat()

        # Message and channel basics
        message_id = str(message.id)
        channel    = f"#{message.channel.name}" if hasattr(message.channel, 'name') else 'DM'

        # Author info
        author          = message.author                # The user object representing the author of the message, which contains various attributes such as username, ID, and roles. This object is essential for extracting information about who sent the message and their associated details.
        author_username = str(author)                   # e.g. "username#0000" or "username"
        author_id       = str(author.id)                # Unique Discord ID for the author, which is a numeric identifier that can be used to reference the user in the Discord API. This ID is important for tracking who sent the message and can be used for various purposes such as logging, moderation, or user-specific actions within the bot's functionality.

        # Author roles (guild members only; bots in DMs won't have roles)
        if isinstance(author, discord.Member):
            # Exclude @everyone, sort by position descending (highest role first)
            roles = [r.name for r in sorted(author.roles, key=lambda r: r.position, reverse=True)
                     if r.name != '@everyone']
            author_roles = ', '.join(roles) if roles else 'None'
        else:
            author_roles = 'N/A'

        # Message content
        content = message.content

        # Mentioned users — name|ID pairs, semicolon-separated
        mentioned = []
        for user in message.mentions: # Iterates through the list of users mentioned in the message (message.mentions) and appends a string in the format "username|userID" to the mentioned list for each user. This allows the bot to keep track of which users were mentioned in the message and their corresponding IDs, which can be useful for logging or further processing of mentions in the context of the bot's functionality.
            mentioned.append(f"{user}|{user.id}") # Appends a string in the format "username|userID" to the mentioned list for each user mentioned in the message. This format allows for easy identification of both the username and the unique ID of each mentioned user, which can be useful for logging purposes or for any further processing that may be needed based on mentions in the message.
        mentioned_str = '; '.join(mentioned) if mentioned else '' # Joins the list of mentioned users into a single string, separated by semicolons. If there are no mentioned users, it sets the string to an empty value. This provides a clear and concise way to represent all mentioned users in a single field when logging the message details to the Google Sheet.

        # Compile the row of data to be appended to the Google Sheet, including all the extracted fields such as timestamp, message ID, channel, author information, message content, and mentioned users. This structured format allows for organized logging of message details in the Google Sheet, making it easier to analyze and reference specific messages based on their attributes.
        row = [
            timestamp,
            message_id,
            channel,
            author_username,
            author_id,
            author_roles,
            content,
            mentioned_str,
        ]

        self.sheet.append_row(row, value_input_option='USER_ENTERED') # Appends the compiled row of message details to the specified Google Sheet using the gspread library. The value_input_option='USER_ENTERED' parameter allows the data to be entered as if it were typed by a user, which means that any formulas or formatting in the Google Sheet will be applied to the new row of data. This is important for ensuring that the logged message details are properly formatted and integrated into the existing structure of the sheet for easy analysis and reference.

# Bot setup
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# Sets up bot intents, which specify what events the bot will listen to. In this case, the bot is configured to listen for message content and member updates, allowing it to respond to messages and track member activity in the server. Intents are a way to optimize the bot's performance by only subscribing to the events it needs to function properly.
intents = discord.Intents.default() # Initializes the default intents, which include basic events like guilds, messages, and reactions. This is a starting point for configuring the bot's event listening capabilities.
intents.message_content = True 
intents.members = True # Required to resolve roles

# Create a new instance of the Bot class with the specified command prefix (in this case the "!") and intents. The command prefix is set to '!', which means that any message starting with '!' will be treated as a command. The intents specify what events the bot will listen to, such as messages and member updates.
bot = commands.Bot(command_prefix='!', intents=intents)

# Initializes a variable to hold an instance of the SheetsLogger class, which will be used for logging messages to Google Sheets. The type hint indicates that this variable can either be an instance of SheetsLogger or None, allowing for flexibility in how the logger is initialized and used within the bot's functionality.
sheets_logger: SheetsLogger | None = None # Initializes a variable to hold an instance of the SheetsLogger class, which will be used for logging messages to Google Sheets. The type hint indicates that this variable can either be an instance of SheetsLogger or None, allowing for flexibility in how the logger is initialized and used within the bot's functionality.

#This bot event is triggered when the bot successfully connects to Discord and is ready to start receiving events. It prints a message to the console indicating that the bot has logged in, along with the bot's username and ID. This is useful for confirming that the bot is running and connected properly (for debugging purposes)
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')
    try:
        global sheets_logger
        sheets_logger = SheetsLogger(CREDENTIALS_PATH, SPREADSHEET_ID, LOG_SHEET_NAME) # Initializes the SheetsLogger instance with the provided credentials path, spreadsheet ID, and sheet name. This sets up the connection to the Google Sheet where message logs will be stored, allowing the bot to log messages as they are received.
        print("Google Sheets logger initialized successfully.")
    except Exception as e:
        print(f"Error initializing Google Sheets logger: {e}") # Catches any exceptions that occur during the initialization of the SheetsLogger and prints an error message to the console. This helps with debugging issues related to connecting to the Google Sheets API or accessing the specified spreadsheet and sheet.

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if sheets_logger:
        try:
            sheets_logger.log_message(message)
        except Exception as e:
            print(f"Error logging message to Google Sheets: {e}") # Catches any exceptions that occur during the logging of a message to Google Sheets and prints an error message to the console. This helps with debugging issues related to the Google Sheets API or problems with the data being logged.
    await bot.process_commands(message) # Allows the bot to continue processing commands after handling the on_message event, ensuring that any commands included in messages are properly recognized and executed by the bot.



# ---------------------------------- TEST COMMANDS TO BE DEPRECATED ------------------------------------------------------------------------------
server_role = "gamer"

#This bot event listens for new members joining the server and sends them a welcome message via direct message. You can customize the welcome message as needed. In this example, it welcomes the new member by name and provides some basic information about the server.
@bot.event
async def on_member_join(member):
    await member.send(f"Welcome to the server {member.name}! We're glad to have you here. If you have any questions, feel free to ask the moderators or check out the rules channel. Enjoy your stay!")

# This bot event listens for messages in the server
async def on_message(message):
    
    # Prevents the bot from responding to its own messages, which could lead to infinite loops
    if message.author == bot.user: # Checks if the author of the message is the bot itself
        return # returns early from the function, preventing any further code from being executed for this message

    # Handles a simple message response such as a server member saying "hello!"
    if 'hello' in message.content.lower(): # Checks if the message content contains the word "hello" (case-insensitive)
        await message.channel.send(f'Hello {message.author.mention}!') # Sends a greeting by pinging the member who said "hello"

    await bot.process_commands(message) # Allows the bot to continue processing the rest of the commands

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}!") # Responds to the !hello command with a greeting that mentions the user who issued the command

@bot.command()
async def assign(ctx):
    role = discord.utils.get(ctx.guild.roles, name=server_role)
    if role:
        await ctx.author.add_roles(role)
        await ctx.send(f"{ctx.author.mention} has now been assigned the {server_role} role.")
    else:
        await ctx.send("Role doesn't exist.")

bot.run(token, log_handler=handler, log_level=logging.DEBUG) # Starts the bot using the provided token and sets up logging to a file named 'discord.log' with a log level of DEBUG, which will capture detailed information about the bot's activity for troubleshooting and monitoring purposes.
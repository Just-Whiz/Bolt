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
import re
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

print(f"[CONFIG] Credentials path: {os.path.abspath(CREDENTIALS_PATH)}") # Prints the absolute path to the Google credentials JSON file to the console for debugging purposes, allowing you to verify that the correct path is being used for authentication with the Google Sheets API.
print(f"[CONFIG] Credentials exist: {os.path.exists}")
print(f"[CONFIG] Spreadsheet ID: {SPREADSHEET_ID}") # Prints the ID of the Google Spreadsheet to the console for debugging purposes.
print(f"[CONFIG] Spreadheet name: '{LOG_SHEET_NAME}'") # Prints the name of the sheet within the Google Spreadsheet where logs will be stored to the console for debugging purposes.

# Google Sheet setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Company mapping with dictionaries (for the spreadsheet sorting)
EUNA_COMPANIES = {'7EME', '8EME', 'FLQC'} # EU/NA companies
ASOC_COMPANIES = {'4EME', '5EME', '6EME', 'FLQC'} # AS/OC companies

# Matches company labels like **7EME** or **FLQG** in the messages
COMPANY_PATTERN = re.compile(r'\*\*([A-Z0-9]+(?:EME|FLQG|FLQC))\*\*') # This regular expression pattern is designed to match company labels in the format of **7EME**, **8EME**, **FLQC**, etc. It looks for text that starts and ends with double asterisks (**) and contains a combination of uppercase letters and numbers followed by either "EME", "FLQG", or "FLQC". This allows the bot to identify and extract company labels from messages for logging purposes.

# Matches user pings like <@123456789012345678> in the messages
MENTION_PATTERN = re.compile(r'<@!?(\d+)>') # This regular expression pattern is designed to match user mentions in the format of <@123456789012345678> or <@!123456789012345678>. It looks for text that starts with "<@", followed by an optional "!" (which is used for nicknamed users), and then captures a sequence of digits (the user ID) until it reaches the closing ">". This allows the bot to identify and extract user mentions from messages for logging purposes.

# Trigger phrase that identifies the GN Induction graduation msgs
GRADUATION_TRIGGER = "Garde Nationale Graduates"

def get_timezone(company: str) -> str:
    """
    Returns the timezone for a given company based on predefined sets of companies. 
    This function checks if the provided company name is in the EUNA_COMPANIES set or 
    the ASOC_COMPANIES set and returns the corresponding timezone string. If the 
    company is not found in either set, it returns 'Unknown'. 
    This is useful for categorizing messages based on the company mentioned in them, 
    allowing for better organization and analysis of logged data in the Google Sheet.
    """
    if company in EUNA_COMPANIES: # Checks if the provided company name is in the EUNA_COMPANIES set, which contains company labels associated with the EU/NA timezone. If the company is found in this set, it indicates that the message is related to a company that operates in the EU/NA region.
        return 'EUNA' # Returns the string 'EUNA' to indicate that the company belongs to the EU/NA timezone, which can be used for categorizing messages in the Google Sheet based on their associated company and timezone.
    elif company in ASOC_COMPANIES: # Checks if the provided company name is in the ASOC_COMPANIES set, which contains company labels associated with the AS/OC timezone. If the company is found in this set, it indicates that the message is related to a company that operates in the AS/OC region.
        return 'ASOC' # Returns the string 'ASOC' to indicate that the company belongs to the AS/OC timezone, which can be used for categorizing messages in the Google Sheet based on their associated company and timezone.
    else: # If the company is not found in either the EUNA_COMPANIES or ASOC_COMPANIES sets, it means that the company label does not match any of the predefined categories for timezones. In this case, the function will return 'Unknown' to indicate that the timezone for the given company cannot be determined based on the provided sets.
        return 'Unknown' # Returns the string 'Unknown' to indicate that the timezone for the given company cannot be determined based on the provided sets, which can be useful for handling cases where the company label does not match any of the expected categories when logging messages in the Google Sheet.
    

class SheetsLogger:
    def __init__(self, credentials_path: str, spreadsheet_id: str, sheet_name: str):
        """
        This class function handles authentication with the Google Sheets API using a service account and sets up the connection to the specified spreadsheet and sheet. It uses the gspread library to authorize access to the Google Sheets API with the provided credentials and opens the specified spreadsheet and worksheet for logging messages. The credentials are loaded from a JSON file, and the necessary scopes for accessing spreadsheets 
        and drive are defined to ensure proper permissions for reading and writing data to the Google Sheet.
        """
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES) # Loads the service account credentials from the specified JSON file and sets the required scopes for accessing the Google Sheets API. This allows the bot to authenticate with Google and gain the necessary permissions to read and write data to the specified spreadsheet.
        client = gspread.authorize(creds) # Authorizes the gspread client with the loaded credentials, allowing it to interact with the Google Sheets API using the authenticated service account. This step is essential for enabling the bot to access and modify the specified spreadsheet and sheet for logging messages.
        self.sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name) # Opens the specified Google Spreadsheet using its unique ID and selects the specified worksheet (sheet) within that spreadsheet for logging messages. This sets up the connection to the Google Sheet where the bot will append rows of message data as it logs messages received in Discord.
    
    def ensure_headers(self):
        """
        This function writes column headers if the sheet is empty. 
        It checks if the first row of the sheet is empty, and if so, it appends a row of 
        predefined headers to the sheet. This ensures that the logged data will have 
        appropriate column labels for better organization and readability when viewing 
        the Google Sheet. 
        The headers include fields such as 'Timestamp', 'Author', 'Content', 'Company', 'Timezone', and 'Mentions', which correspond to the details of the messages being logged.
        """
        first_row = self.sheet.row_values(1) # Retrieves the values of the first row in the sheet to check if it is empty. If the first row is empty, it indicates that there are no headers present in the sheet, and the function will proceed to append the predefined headers to the sheet for better organization of logged data.
        if not first_row: # Checks if the first row is empty (i.e., contains no values). If this condition is true, it means that the sheet does not have any headers, and the function will proceed to append the predefined headers to the sheet.
            headers = [
                'Timestamp',
                'Recruit Username',
                'Discord ID',
                'Class Date',
                'Date Left',
                'EUNA/ASOC',
                'Company',
                'GN Host',
            ]
            self.sheet.append_row(headers, value_input_option='USER_ENTERED') # Appends the predefined headers to the first row of the sheet using the append_row method. The value_input_option='USER_ENTERED' parameter ensures that the values are treated as if they were entered by a user, allowing for proper formatting and display in the Google Sheet.

    def log_recruits(self, rows: list[list]): # Defines a method to log multiple recruit rows at once by appending them to the Google Sheet. The method takes a list of lists (rows) as input, where each inner list represents a row of recruit data to be logged. If the list of rows is not empty, it uses the append_rows method to add all the rows to the sheet in one operation, with the value_input_option set to 'USER_ENTERED' to ensure that the data is formatted correctly in the Google Sheet. This allows for efficient logging of multiple recruits at once, reducing the number of API calls and improving performance when logging large batches of recruit data.
        """Appends multiple recruit rows at once."""
        if rows: # Checks if the list of rows is not empty before attempting to append them to the sheet. If the list is empty, it means there are no recruit rows to log, and the function will simply return without making any API calls to append data to the sheet.
            self.sheet.append_rows(rows, value_input_option='USER_ENTERED') # Appends multiple rows of recruit data to the sheet using the append_rows method. The value_input_option='USER_ENTERED' parameter ensures that the values are treated as if they were entered by a user, allowing for proper formatting and display in the Google Sheet. This method is more efficient than appending rows one by one, especially when logging large batches of recruit data.

async def parse_graduation_message(message: discord.Message) -> list[list]:
    """
    Parse a graduation message and return a list of rows, one per recruit.
    Each row: [Timestamp, Recruit Username, Discord ID, Class Date, Date Left, EUNA/ASOC, Company, GN Host]
    """
    content = message.content # Extracts the content of the message, which contains the text that will be parsed to identify company labels and user mentions. This content is used as the basis for extracting relevant information about recruits and their associated companies for logging to the Google Sheet.
    host = str(message.author) # Extracts the host (the author of the message) as a string, which will be logged in the Google Sheet to indicate who posted the graduation message. This provides context for the logged data, allowing for better tracking and analysis of graduation messages based on who is hosting them in the Discord server.

    # Class date from message timestamp, formatted as M/D/YYYY
    dt = message.created_at.replace(tzinfo=timezone.utc) # Gets the creation timestamp of the message and sets its timezone to UTC. This ensures that the timestamp is standardized and can be correctly formatted regardless of the server's local timezone settings. By using UTC, the bot can maintain consistency in how it logs timestamps to the Google Sheet, making it easier to sort and analyze data based on when messages were created.
    class_date = f"{dt.month}/{dt.day}/{dt.year}" # Extracts the class date from the message's creation timestamp and formats it as M/D/YYYY. This provides a standardized way to represent the date of the graduation class in the Google Sheet, allowing for easier sorting and filtering of logged data based on class dates.
    timestamp = dt.isoformat() # ISO format timestamp for logging purposes, which provides a standardized way to represent date and time information in the Google Sheet. This allows for easier sorting and filtering of logged data based on the timestamp of when the graduation message was created.

    rows = []

    # Split the message into segments by company label.
    # We find the position of every **COMPANY** label, then collect
    # all <@userID> pings that appear between it and the next label.
    segments = []
    last_end = 0
    current_company = None

    # Walk through all company matches in order
    for match in COMPANY_PATTERN.finditer(content): # Iterates through all matches of the COMPANY_PATTERN regular expression in the message content. For each match, it extracts the company name and the segment of text that follows it until the next company label. This allows the bot to associate user mentions with the correct company based on the structure of the message, which is important for logging accurate data to the Google Sheet.
        company_name = match.group(1) # Extracts the company name from the matched company label in the message content. The regular expression captures the company name (e.g., "7EME", "FLQC") from the text that matches the pattern of **COMPANY**, allowing the bot to identify which company is associated with the user mentions that follow it in the message.
        segment_text = content[last_end:match.start()] # Extracts the segment of text between the end of the last match and the start of the current match. This segment contains the user mentions that are associated with the current company label. By capturing this segment, the bot can later extract the user IDs from it and associate them with the correct company when logging to Google Sheets.

        # If we already had a company, the text before this match belongs to it
        if current_company is not None:
            segments.append((current_company, segment_text))

        current_company = company_name # Updates the current company to the one found in the match, which will be used for the next segment of text until the next company label is found. This allows the bot to associate user mentions with the correct company based on the structure of the message, ensuring that the logged data in the Google Sheet accurately reflects which recruits are associated with which companies.
        last_end = match.end() # Updates the last_end variable to the end position of the current match, which will be used as the starting point for the next segment of text when the next company label is found. This ensures that the bot correctly captures the text between company labels for accurate parsing of user mentions and logging to the Google Sheet.

    # Don't forget the final segment after the last company label
    if current_company is not None:
        segments.append((current_company, content[last_end:]))

    # Now extract user IDs from each segment and build rows
    for company, segment_text in segments: # Iterates through each segment of the message that was split by company labels. For each segment, it extracts the company name and the corresponding text that follows it. This allows the bot to associate user mentions with the correct company based on the structure of the message, which is important for logging accurate data to the Google Sheet.
        timezone_label = get_timezone(company) # Calls the get_timezone function to determine the timezone label (EUNA, ASOC, or Unknown) based on the company name extracted from the segment. This helps categorize the recruit data in the Google Sheet according to the associated company and its corresponding timezone.
        user_ids = MENTION_PATTERN.findall(segment_text) # Uses the MENTION_PATTERN regular expression to find all user mentions in the segment text and extract their user IDs. This allows the bot to identify which users are associated with each company segment in the message, enabling it to log the correct recruit information (such as username and Discord ID) to the Google Sheet for each mentioned user.

        for user_id in user_ids: # Iterates through each user ID extracted from the segment text. For each user ID, it attempts to resolve the username from the guild (server) using the Discord API. This is necessary to log the recruit's username along with their Discord ID in the Google Sheet, providing more meaningful information about the recruits being logged.
            # Attempt to resolve username from the guild
            username = ''
            try:
                member = message.guild.get_member(int(user_id))
                if member:
                    username = str(member)  # e.g. "just_whiz" or "just_whiz#0000"
                else:
                    # Not in cache — fetch from API
                    member = await message.guild.fetch_member(int(user_id)) # Fetches the member information from the Discord API using the user ID. This is necessary if the member is not found in the guild's member cache, which can happen if the member has not been active recently or if the bot has just started and hasn't cached all members yet. By fetching the member information directly from the API, the bot can still resolve the username for logging purposes even if it's not available in the cache.
                    username = str(member)
            except Exception:
                username = f'Unknown ({user_id})'

            row = [ # Builds a row of data for each recruit, containing the timestamp of the message, the recruit's username, their Discord ID, the class date, a blank field for the date they left (to be filled manually later), the timezone label based on their company, the company name, and the host of the graduation message. This structured data will be logged to the Google Sheet for record-keeping and analysis of graduation messages in the Discord server.
                timestamp, 
                username,
                user_id,
                class_date,
                '',           # Date Left — blank, to be filled manually
                timezone_label,
                company,
                host,
            ]
            rows.append(row)

    return rows # Returns a list of rows, where each row contains details about a recruit such as timestamp, username, Discord ID, class date, timezone, company, and host. This structured data can then be logged to Google Sheets for record-keeping and analysis of graduation messages in the Discord server.

# ------------------------------ BOT SETUP & EVENT LISTENERS/HANDLERS ---------------------------------------------------------------

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w') # Sets up a logging handler that writes log messages to a file named 'discord.log' with UTF-8 encoding. The mode='w' parameter means that the log file will be overwritten each time the bot is run, ensuring that only the most recent logs are kept. This logging setup allows for tracking the bot's activity and debugging any issues that may arise during its operation.

# Sets up bot intents, which specify what events the bot will listen to. In this case, the bot is configured to listen for message content and member updates, allowing it to respond to messages and track member activity in the server. Intents are a way to optimize the bot's performance by only subscribing to the events it needs to function properly.
intents = discord.Intents.default() # Initializes the default intents, which include basic events like guilds, messages, and reactions. This is a starting point for configuring the bot's event listening capabilities.
intents.message_content = True 
intents.members = True # Required to resolve roles

# Create a new instance of the Bot class with the specified command prefix (in this case the "!") and intents. The command prefix is set to '!', which means that any message starting with '!' will be treated as a command. The intents specify what events the bot will listen to, such as messages and member updates.
bot = commands.Bot(command_prefix='!', intents=intents)

# Initializes a variable to hold an instance of the SheetsLogger class, which will be used for logging messages to Google Sheets. The type hint indicates that this variable can either be an instance of SheetsLogger or None, allowing for flexibility in how the logger is initialized and used within the bot's functionality.
sheets_logger: SheetsLogger | None = None # Initializes a variable to hold an instance of the SheetsLogger class, which will be used for logging messages to Google Sheets. The type hint indicates that this variable can either be an instance of SheetsLogger or None, allowing for flexibility in how the logger is initialized and used within the bot's functionality.

@bot.event # This decorator registers the on_ready function as an event handler for the 'ready' event, which is triggered when the bot has successfully connected to Discord and is ready to start processing events. This allows the bot to perform any necessary setup or initialization tasks (such as setting up the Google Sheets logger) once it is fully connected and operational.
async def on_ready(): # This event handler is called when the bot has successfully connected to Discord and is ready to start processing events. It prints a message to the console indicating that the bot is logged in, along with the bot's username and ID. It also initializes the SheetsLogger instance for logging messages to Google Sheets, ensuring that the necessary headers are set up in the sheet. If there is an error during initialization, it catches the exception and prints an error message to the console for debugging purposes.
    global sheets_logger
    print(f'Logged in as {bot.user.name} - {bot.user.id}') # Prints a message to the console indicating that the bot has successfully logged in, along with the bot's username and ID. This confirms that the bot is connected to Discord and ready to start processing events.
    try:
        sheets_logger = SheetsLogger(CREDENTIALS_PATH, SPREADSHEET_ID, LOG_SHEET_NAME)
        sheets_logger.ensure_headers()
        print("Google Sheets logger initialized successfully.")
    except Exception as e: # Catches any exceptions that occur during the initialization of the SheetsLogger and prints an error message to the console. This helps with debugging by providing information about what went wrong during the setup of the Google Sheets logger, such as issues with authentication, incorrect spreadsheet ID, or problems with the credentials file.
        print(f"Error initializing Google Sheets logger: {type(e).__name__}: {e}")


@bot.event # This decorator registers the on_message function as an event handler for the 'message' event, which is triggered whenever a new message is sent in any channel that the bot has access to. This allows the bot to process incoming messages and perform actions based on their content, such as logging graduation messages to Google Sheets or responding to commands.
async def on_message(message):
    if message.author == bot.user: # Checks if the author of the message is the bot itself. This is a common practice to prevent the bot from responding to its own messages, which could lead to infinite loops or unintended behavior. If the message was sent by the bot, it simply returns without processing the message further.
        return

    # Only process graduation messages
    if GRADUATION_TRIGGER not in message.content: # Checks if the graduation trigger phrase is not present in the message content. If the trigger phrase is not found, it means that the message is not a graduation message that the bot is designed to log, so it allows other commands to be processed by calling await bot.process_commands(message) and then returns without further processing. This ensures that the bot only focuses on logging messages that are relevant to its intended functionality (i.e., graduation messages) while still allowing it to respond to other commands as needed.
        await bot.process_commands(message) # Allows the bot to continue processing other commands if the message does not contain the graduation trigger phrase, ensuring that the bot can still respond to other interactions in the server while ignoring messages that are not relevant to its logging functionality.
        return

    print(f"[GRADUATION] Detected graduation message from {message.author} in #{message.channel.name}")

    if sheets_logger: # Checks if the sheets_logger instance has been initialized successfully before attempting to log messages to Google Sheets. If the logger is available, it proceeds to parse the graduation message and log the recruit data to the sheet. If there was an issue with initializing the logger (e.g., due to authentication errors or incorrect configuration), it will skip the logging step and print an error message instead.
        try:
            rows = await parse_graduation_message(message) # Calls the parse_graduation_message function to extract recruit data from the graduation message and returns a list of rows, where each row contains details about a recruit such as timestamp, username, Discord ID, class date, timezone, company, and host. This function processes the message content to identify company labels and user mentions, allowing it to build structured data for logging to Google Sheets.
            sheets_logger.log_recruits(rows) # Uses the log_recruits method of the sheets_logger instance to append the extracted recruit data rows to the Google Sheet. This method takes care of formatting the data correctly and ensuring that it is added to the sheet in an efficient manner, allowing for proper record-keeping of graduation messages in the Discord server.
            print(f"[GRADUATION] Logged {len(rows)} recruit(s) to Google Sheets.") # Prints a message to the console indicating how many recruits were logged to Google Sheets from the graduation message. This provides feedback on the logging process and helps with monitoring the bot's activity when processing graduation messages.
        except Exception as e: # Catches any exceptions that occur during the parsing of the graduation message or the logging of recruit data to Google Sheets, and prints an error message to the console for debugging purposes. This helps identify issues that may arise during the processing of graduation messages, such as problems with message formatting, issues with the Google Sheets API, or other unexpected errors that could occur while handling the message content.
            print(f"[GRADUATION] Error logging to Google Sheets: {type(e).__name__}: {e}") # Prints an error message to the console indicating that there was an issue logging the graduation message to Google Sheets, along with the type and details of the exception that occurred. This information is crucial for debugging and resolving any issues that may arise during the logging process.

    await bot.process_commands(message)


# ---------------------------------- TEST COMMANDS; TO BE DEPRECATED ------------------------------------------------------------------------------
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
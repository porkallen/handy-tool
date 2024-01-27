import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime
import time
import re
from email.message import EmailMessage

import google.auth
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import logging

# Configure the logging system
LOG_FILE = 'script.log'
MAX_LOG_SIZE = 1024 * 1024  # 1 MB

# Configure the logging system
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def check_log_size(log_file):
    return os.path.getsize(log_file)

def clean_up_log(log_file, max_size):
    current_size = check_log_size(log_file)
    if current_size > max_size:
        # Backup the existing log file and create a new one
        backup_log_file = log_file + '.bak'
        os.rename(log_file, backup_log_file)
        logging.info(f"Log file exceeded {max_size} bytes. Creating a new log file.")
    else:
        logging.debug(f"Log file size: {current_size} bytes")

def extract_emails(line):
    # Using regular expression to find all email addresses in a line
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    return email_pattern.findall(line)

def read_recipients_from_file(file_path):
    recipients = []
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            for line in file:
                # Skip lines starting with '#'
                if line.startswith('#'):
                    continue
                # Extract emails from the line
                recipients += extract_emails(line)

        return [email.strip() for email in recipients]
    else:
        raise FileNotFoundError(f"The file {file_path} does not exist, and no default recipients provided.")

def read_config_file(file_path):
    config_map = {}

    with open(file_path, 'r') as file:
        lines = file.readlines()

    for line in lines:
        # Use regular expressions to extract key-value pairs
        match = re.match(r'(\w+)\s*=\s*[\'"](.+)[\'"]', line)
        if match:
            key, value = match.groups()
            config_map[key] = value

    return config_map

def get_gmail_credentials(id, secret):
    # Your OAuth client ID and client secret from the Google API Console
    client_id = id
    client_secret = secret

    # The file token.json stores the user's access and refresh tokens
    token_file = 'token.json'

    # Define the Gmail API scopes
    scopes = ['https://www.googleapis.com/auth/gmail.send']

    # Create flow instance and fetch token if exists, otherwise start the authorization process
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', scopes=scopes)

    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = flow.run_local_server(port=0)
        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    return creds

def gmail_send_message(subject, body, bcc_emails):
    # Get client_id, client_secret, and from from config.txt
    try:
        config = read_config_file('config.txt')
        # Assign values to variables
        client_id = config.get('client_id', '')
        client_secret = config.get('client_secret', '')
        sender_email = config.get('from', '')
    except FileNotFoundError:
        logging.error(f"The file {config_file_path} does not exist.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")

    """Create and send an email message
    Print the returned  message id
    Returns: Message object, including message id
    """
    creds = get_gmail_credentials(client_id, client_secret)

    try:
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()

        message.set_content(body)

        message['Bcc'] = ', '.join(bcc_emails)
        message["From"] = sender_email
        message["Subject"] = subject

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"raw": encoded_message}
        # pylint: disable=E1101
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )
        logging.info(f'Message Id: {send_message["id"]}')
    except HttpError as error:
        logging.error(f"An error occurred: {error}")
        send_message = None

    return send_message

def should_send_email():
    # Check if today is the 1st day of January, April, July, or October
    today = datetime.date.today()
    if today.month in [1, 4, 7, 10] and today.day == 15:
        logging.info(f"Today: {today.month}/{today.day}")
        return True
    return False

if __name__ == "__main__":
    try:
        email_subject = "Quarterly HOA Fee Reminder"
        email_body = "==A gentle reminder==\r\nThe quarterly HOA Fee has been posted in your Buildium account. Due is end of this month.\r\nBest Regards\r\nAltair HOA"
        config = read_config_file('config.txt')

        # For debugging
        #should_send_email()
        #recipient_emails = ['']
        #logging.info(f"recipient_emails: {recipient_emails}")
        #gmail_send_message(email_subject, email_body, recipient_emails)
        #logging.info("Email sent successfully.")

        # Check and clean up log file if needed
        while True:
            if should_send_email():
                recipient_emails = read_recipients_from_file('recipients.txt')
                gmail_send_message(email_subject, email_body, recipient_emails)
                print("Email sent successfully.")

            clean_up_log(LOG_FILE, MAX_LOG_SIZE)
            # Sleep for a day before checking again
            time.sleep(24 * 3600)  # 24 hours
    except KeyboardInterrupt:
        print("Script terminated by user.")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
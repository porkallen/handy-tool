import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime
import time
from email.message import EmailMessage

import google.auth
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow

RECIPEINT_LIST = ['allenms886@gmail.com']

def read_recipients_from_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            recipients = file.read().split(',')

        return [email.strip() for email in recipients]
    else:
        return RECIPEINT_LIST

def get_gmail_credentials():
    # Your OAuth client ID and client secret from the Google API Console
    client_id = '891863790185-ae0vggjp9peq4tsmn6k0o1u868hgogko.apps.googleusercontent.com'
    client_secret = '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'

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
    """Create and send an email message
    Print the returned  message id
    Returns: Message object, including message id

    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    creds = get_gmail_credentials()

    try:
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()

        message.set_content(body)

        print(', '.join(bcc_emails))
        message['Bcc'] = ', '.join(bcc_emails)
        message["From"] = 'altairhoa@gmail.com'
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
        print(f'Message Id: {send_message["id"]}')
    except HttpError as error:
        print(f"An error occurred: {error}")
        send_message = None

    return send_message

def send_email(subject, body, bcc_emails):
    # Your Gmail credentials
    gmail_user = 'altairhoa@gmail.com'
    gmail_password = 'your_password'

    # Create the email message
    message = MIMEMultipart()
    message['From'] = gmail_user
    message['Bcc'] = ', '.join(bcc_emails)
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    # Connect to Gmail's SMTP server
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(gmail_user, gmail_password)

        # Send the email
        server.send_message(message)

def should_send_email():
    # Check if today is the 1st day of January, April, July, or October
    today = datetime.date.today()
    return today.month in [1, 4, 7, 10] and today.day == 15


# if __name__ == "__main__":
#     try:
#         while True:
#             if should_send_email():
#                 # Set your email details
#                 email_subject = "Quarterly Update"
#                 email_body = "This is a quarterly update email."

#                 send_email(email_subject, email_body, RECIPEINT_LIST)
#                 print("Email sent successfully.")

#             # Sleep for a day before checking again
#             time.sleep(24 * 3600)  # 24 hours
#     except KeyboardInterrupt:
#         print("Script terminated by user.")

if __name__ == "__main__":
    try:
        email_subject = "Quarterly HOA Fee Reminder"
        email_body = "==A gentle reminder==\r\nThe quarterly HOA Fee has been posted in your Buildium account.\r\nBest Regards\r\nAltair HOA"
        recipient_emails = read_recipients_from_file('recipients.txt')

        gmail_send_message(email_subject, email_body, recipient_emails)
        print("Email sent successfully.")
    except KeyboardInterrupt:
        print("Script terminated by user.")
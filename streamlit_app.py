from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.errors import SlackApiError
import smtplib
from email.mime.text import MIMEText
import os

from cachetools import LRUCache
import streamlit as st
# Track recently processed event_ids with a max of 10000 entries
processed_events = LRUCache(maxsize=10000)

SLACK_BOT_TOKEN = st.secrets["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = st.secrets["SLACK_APP_TOKEN"]
CHANNEL_ID = st.secrets["CHANNEL_ID"]
EMAIL_USER = st.secrets["EMAIL_USER"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
SMTP_SERVER = st.secrets["SMTP_SERVER"]
SMTP_PORT = st.secrets["SMTP_PORT"]

# Slack Setup
client = WebClient(token=SLACK_BOT_TOKEN)
socket_client = SocketModeClient(app_token=SLACK_APP_TOKEN, web_client=client)


# Get Bot's user ID once
bot_user_id = client.auth_test()["user_id"]

def get_user_info(slack_user_id):
    try:
        user_info = client.users_info(user=slack_user_id)
        profile = user_info['user']['profile']
        email = profile.get('email')
        real_name = profile.get('real_name', 'there')  # fallback if name missing
        return email, real_name
    except SlackApiError as e:
        print(f"Error fetching user info: {e.response['error']}")
        return None, None
    
def send_offboarding_initiated_message(user_name):
    try:
        message = f"Hello {user_name} Your offboarding process has been initiated✅ . Please check your email for further instructions."
        response = client.chat_postMessage(
            channel=CHANNEL_ID,
            text=message
        )
        print(f"✅ Offboarding initiation message sent to {user_name}")
    except SlackApiError as e:
        print(f"Error sending message to user: {e.response['error']}")

def send_offboarding_email(to_email, user_name):
    from_email = EMAIL_USER
    password = EMAIL_PASSWORD  # Use App password if using Gmail 2FA
    subject = "Offboarding Instructions"

    
    body = f"""
<html>
  <body style="font-family: Arial, sans-serif; font-size: 14px; color: #000000;">
    <p>Hello {user_name},</p>

    <p>We certainly appreciate your time working with us. There are just a few steps you'll need to complete first, which you'll find listed below. Please ignore any steps that you may have already completed. If you have any questions, don't hesitate to reach out to the HR Team.</p>

    <ul>
      <li>Inform your team leader or Point of Contact (POC) of your decision to offboard</li>
      <li>Craft and send a resignation letter to the HR Team at: <a href="mailto:humanresources@cdreams.org">humanresources@cdreams.org</a></li>
      <li>Return access or permissions from any tools, email accounts, drives, etc., and hand them over to your lead</li>
      <li>Conclude all outstanding projects and tasks</li>
      <li>Offboard yourself from all CDF-related systems and tools (log out on the agreed-upon date)</li>
      <li>Provide your official end date (final working day with CDF)</li>
      <li>Complete the <a href="https://docs.google.com/forms/d/e/1FAIpQLSci_4uN20RO3vkmcA7nacPIjAw4epJM2sAC0_VjDe0edg9TWg/viewform" target="_blank">Exit Survey</a> <strong>(Mandatory)</strong></li>
    </ul>

    <p>Thank you!</p>
    <p><strong>Human Resources</strong><br>
    Community Dreams Foundation</p>
  </body>
</html>
"""



    msg = MIMEText(body,"html")
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(from_email, password)
            server.send_message(msg)
            print(f"✅ Offboarding email successfully sent to {to_email}")
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")

def process(client: SocketModeClient, req: SocketModeRequest):
    if req.type == "events_api":
        # Acknowledge the event immediately to prevent retries
        response = SocketModeResponse(envelope_id=req.envelope_id)
        client.send_socket_mode_response(response)
        payload = req.payload
        event = payload.get("event", {})
        event_id = payload.get("event_id")

        # Skip if already processed
        if event_id in processed_events:
            print(f"⚠️ Duplicate event {event_id} skipped")
            return
        processed_events[event_id] = True  # Mark as processed

        if event.get("type") == "message" and 'text' in event:
            text = event['text'].lower()
            user_id = event.get('user')
            channel_id = event.get('channel')

            # # Skip bot's own messages
            if user_id is None or user_id == bot_user_id:
                return
            if channel_id != 'C08MEC4L942':
                return

            print(f"📩 New message: {text} from {channel_id}")

            if "resign" in text:
                print("🔔 Detected resignation/offboarding message!")
                user_email, user_name = get_user_info(user_id)
                if user_email:
                    send_offboarding_email(user_email, user_name)
                    send_offboarding_initiated_message(user_name)
                else:
                    print("❌ Could not find user email.")

# Attach event listener
socket_client.socket_mode_request_listeners.append(process)

# Start the client
if __name__ == "__main__":
    print("👀 Listening for messages... (Press CTRL+C to stop)")
    socket_client.connect()
    import time
    while True:
        time.sleep(0.5)

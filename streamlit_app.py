import streamlit as st

st.title("Offboarding Bot Server")
st.write(
    "Server Running🔥)."
)
st.sidebar.success("✅ Bot connected successfully!")
st.toast("Message sent!")
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.errors import SlackApiError
import smtplib
from email.mime.text import MIMEText
import os
import streamlit as st

from cachetools import LRUCache

# Track recently processed event_ids with a max of 10000 entries
processed_events = LRUCache(maxsize=10000)

SLACK_BOT_TOKEN = st.secrets["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = st.secrets["SLACK_APP_TOKEN"]
CHANNEL_ID = st.secrets["CHANNEL_ID"]
EMAIL_USER = st.secrets["EMAIL_USER"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
SMTP_SERVER = st.secrets["SMTP_SERVER"]
SMTP_PORT = st.secrets["SMTP_PORT"]


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
        st.toast(f"✅ Offboarding initiation message sent to {user_name}")
    except SlackApiError as e:
        print(f"Error sending message to user: {e.response['error']}")

def send_offboarding_email(to_email, user_name):
    from_email = EMAIL_USER
    password = EMAIL_PASSWORD # Use App password if using Gmail 2FA
    subject = "Offboarding Instructions"

    
    body =f"""
Hello {user_name},
Thank you for reaching out. Please follow these steps to complete your offboarding:

    1. Inform your team leader.
    2. Send a resignation letter to hr@cdreams.org.
    3. Return all company property.
    4. Finish outstanding tasks.
    5. Log out of all CDF systems.
    6. Provide your final working day.
    7. Complete the Exit Survey here: [Exit Survey Link]

    Thank you!
    """

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(from_email, password)
            server.send_message(msg)
            st.toast(f"✅ Offboarding email successfully sent to {to_email}")
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

            # Skip bot's own messages
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

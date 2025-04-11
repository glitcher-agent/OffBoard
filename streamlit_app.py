import streamlit as st


SLACK_BOT_TOKEN = st.secrets["SLACK_BOT_TOKEN"]
print(SLACK_BOT_TOKEN)

st.title("Offboarding Bot Server"+ SLACK_BOT_TOKEN)
st.write(
    "Server Running🔥)."
)

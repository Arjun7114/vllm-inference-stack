"""
Thin Streamlit chat UI.

Its only jobs: keep the conversation in session state, render it, take user input,
call the app layer's streaming endpoint, and show tokens as they arrive. No
business logic lives here -- that's all in the FastAPI app layer. The UI is
deliberately thin because the serving layer is the star of this project.
"""

import json
import os

import httpx
import streamlit as st

# Where the FastAPI app layer lives, and the API key to authenticate with.
API_URL = os.environ.get("APP_API_URL", "http://127.0.0.1:8080/v1/chat/completions")
API_KEY = os.environ.get("APP_API_KEY", "dev-key-change-me")

st.set_page_config(page_title="vLLM Inference Stack", page_icon="[chat]")
st.title("vLLM Inference Stack")
st.caption("Thin chat UI -> FastAPI app layer -> model backend")

# --- conversation history persists across Streamlit re-runs ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- render the history as chat bubbles ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


def stream_reply(messages):
    """
    Generator: POST to the streaming endpoint and yield each token as it arrives.
    Parses the OpenAI-style SSE lines (data: {...}) and pulls out the content
    delta. `st.write_stream` consumes this and renders tokens live.
    """
    body = {"messages": messages, "stream": True}
    headers = {"Authorization": f"Bearer {API_KEY}"}
    with httpx.stream("POST", API_URL, headers=headers, json=body, timeout=60) as r:
        if r.status_code != 200:
            yield f"[error {r.status_code}] {r.read().decode(errors='ignore')}"
            return
        for line in r.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            data = line[len("data: "):]
            if data.strip() == "[DONE]":
                break
            try:
                chunk = json.loads(data)
                delta = chunk["choices"][0]["delta"]
                piece = delta.get("content", "")
                if piece:
                    yield piece
            except (json.JSONDecodeError, KeyError, IndexError):
                continue


# --- input box at the bottom ---
if prompt := st.chat_input("Type a message..."):
    # show the user's message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # stream the assistant's reply live
    with st.chat_message("assistant"):
        full = st.write_stream(stream_reply(st.session_state.messages))

    # remember the assistant's reply for the next turn
    st.session_state.messages.append({"role": "assistant", "content": full})

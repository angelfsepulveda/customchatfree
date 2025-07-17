# MIT License
#
# Copyright (c) 2025
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import streamlit as st
import services.models_response as models_response
import sqlite3
import services.database as db_service

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Chat for free API",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.title("🤖 Chat for free API")
# st.caption("A chat interface built with Streamlit")

# --- INITIALIZE DATABASE ---
db_service.initialize_database()

# --- LOAD HISTORY IF EXISTS ---
if "chat_history" not in st.session_state or not st.session_state["chat_history"]:
    user_id = db_service.get_user_id("default_user")
    conversations = db_service.get_conversations_by_user(user_id)
    st.session_state.chat_history = {}
    conversation_id_map = {}
    role_id_map = {}
    for idx, conv in enumerate(conversations):
        conv_id = conv["conversation_id"]
        messages = db_service.get_messages_by_conversation(conv_id)
        st.session_state.chat_history[idx+1] = messages
        conversation_id_map[idx+1] = conv_id
        role_id_map[idx+1] = conv.get("role_id")
    if conversations:
        st.session_state.current_chat_id = 1
        st.session_state.chat_id_counter = len(conversations)
        st.session_state.current_db_conversation_id = conversation_id_map[1]
        st.session_state.current_role_id = role_id_map[1]

# --- SESSION STATE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = {}

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

if "chat_id_counter" not in st.session_state:
    st.session_state.chat_id_counter = 0

if "current_role_id" not in st.session_state:
    st.session_state.current_role_id = None

# Instantiate the ModelsData class to handle models
models_data = models_response.ModelsData()

# --- HELPER FUNCTIONS ---
def get_deepseek_response(message: str, system_message: str = None) -> str:
    """
    Sends a message to the selected model via OpenRouter and returns the response.
    If system_message is provided, it is sent as a system prompt.
    """
    if modelo_seleccionado == "gemini_flash":
        return models_data.gemini_flash(message, image_url=image_data_url if image_data_url else None, system_message=system_message)
    else:
        return models_data.get_response(message, modelo_seleccionado, system_message=system_message)


def create_new_chat():
    """Creates a new chat and sets it as the current chat."""
    st.session_state.chat_id_counter += 1
    new_id = st.session_state.chat_id_counter
    st.session_state.chat_history[new_id] = []
    st.session_state.current_chat_id = new_id

    # Start conversation in the database
    conn = sqlite3.connect(db_service.DATABASE_FILE)
    try:
        cursor = conn.cursor()
        user_id = db_service.get_user_id("default_user")  # No authentication yet
        role_id = st.session_state.current_role_id
        conversation_id = db_service.create_conversation(user_id, cursor=cursor)
        if role_id:
            db_service.assign_role_to_conversation(conversation_id, role_id)
        st.session_state.current_db_conversation_id = conversation_id
        db_service.log_action("New chat started", f"User ID: {user_id}, Role ID: {role_id}", cursor=cursor)
        conn.commit()
    finally:
        conn.close()

# --- SIDEBAR ---

with st.sidebar:
    st.header("My Chats")
    if st.button("➕ New Chat", use_container_width=True):
        create_new_chat()

    st.subheader("Roles (Persona/Context)")
    user_id = db_service.get_user_id("default_user")
    roles = db_service.get_roles_by_user(user_id)
    role_options = [f"{r['name']} - {r['description'][:20]}..." if r['description'] else r['name'] for r in roles]
    role_ids = [r['role_id'] for r in roles]
    if roles:
        selected_role_idx = st.selectbox("Select a role for this chat", list(range(len(roles))), format_func=lambda i: role_options[i], key="role_select")
        st.session_state.current_role_id = role_ids[selected_role_idx]
        st.markdown(f"**Current role:** {roles[selected_role_idx]['name']}\n\n{roles[selected_role_idx]['description']}")
    else:
        st.session_state.current_role_id = None
        st.info("No roles found. Please create one below.")
    with st.expander("Create new role"):
        new_role_name = st.text_input("Role name", key="new_role_name")
        new_role_desc = st.text_area("Role description (system prompt)", key="new_role_desc")
        if st.button("Create role", key="create_role_btn"):
            if new_role_name and new_role_desc:
                db_service.create_role(user_id, new_role_name, new_role_desc)
                st.experimental_rerun()
            else:
                st.warning("Please provide both a name and a description.")

    st.subheader("Select model")
    modelo_seleccionado = st.selectbox(
        "Model",
        ["deepseek_v3", "kimi", "gemini_flash", "qwq_32b", "mistral_nemo"],
        format_func=lambda x: {
            "deepseek_v3": "DeepSeek v3",
            "kimi": "Kimi",
            "gemini_flash": "Gemini 2.0 Flash",
            "qwq_32b": "Qwen QWQ-32B",
            "mistral_nemo": "Mistral Nemo"
        }[x]
    )
    # No image URL field in the sidebar anymore

    st.subheader("History")
    # Show chats in reverse order (newest first)
    for chat_id in sorted(st.session_state.chat_history.keys(), reverse=True):
        # Use the user's first message as the chat title
        messages = st.session_state.chat_history[chat_id]
        chat_title = f"Chat {chat_id}"
        if messages:
            chat_title = messages[0]["content"][:30] + "..."

        # Button to switch to the selected chat
        if st.button(chat_title, key=f"switch_{chat_id}", use_container_width=True):
            st.session_state.current_chat_id = chat_id
            if "conversation_id_map" in locals():
                st.session_state.current_db_conversation_id = conversation_id_map[chat_id]
            if "role_id_map" in locals():
                st.session_state.current_role_id = role_id_map[chat_id]

# --- MAIN CHAT LOGIC ---

if st.session_state.current_chat_id is None:
    st.info("Select a chat or create a new one to start.")
else:
    # Show messages of the current chat
    current_messages = st.session_state.chat_history[st.session_state.current_chat_id]
    # Get current system prompt (role description)
    system_message = None
    if st.session_state.current_role_id:
        role_info = db_service.get_role_by_id(st.session_state.current_role_id)
        if role_info:
            system_message = role_info["description"]
    for message in current_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input at the bottom of the page
    image_bytes = None
    if modelo_seleccionado == "gemini_flash":
        uploaded_file = st.file_uploader("Upload an image (optional)", type=["png", "jpg", "jpeg"], key="image_uploader")
        if uploaded_file is not None:
            import base64
            image_bytes = uploaded_file.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            image_data_url = f"data:image/{uploaded_file.type.split('/')[-1]};base64,{image_b64}"
        else:
            image_data_url = None
    else:
        image_data_url = None

    if prompt := st.chat_input("Type your message here..."):
        # Add and show the user's message
        current_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            if modelo_seleccionado == "gemini_flash" and image_data_url:
                st.image(image_bytes, caption="Image sent", use_column_width=True)

        # Save the user's message in the database
        conn = sqlite3.connect(db_service.DATABASE_FILE)
        try:
            cursor = conn.cursor()
            db_service.add_message(st.session_state.current_db_conversation_id, "user", prompt, "user_input", cursor=cursor)
            # Generate and show the assistant's response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        if modelo_seleccionado == "gemini_flash":
                            response = models_data.gemini_flash(prompt, image_url=image_data_url, system_message=system_message)
                        else:
                            response = get_deepseek_response(prompt, system_message=system_message)
                        st.markdown(response)
                        # Save the assistant's response in the database
                        db_service.add_message(st.session_state.current_db_conversation_id, "assistant", response, "deepseekchimera", cursor=cursor)
                        # Add the assistant's response to the history
                        current_messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {e}")
            conn.commit()
        finally:
            conn.close()
# Chat for Free API

**License:** MIT (2025)

A modern, extensible chat application built with Streamlit that allows you to interact with multiple Large Language Models (LLMs) via the OpenRouter API. You can create and manage multiple chats, select from various models (including image-capable models), and define custom roles/personas to influence the assistant's behavior in each conversation.

## Features

- **Multi-model support:** Easily switch between models like DeepSeek v3, Kimi, Gemini 2.0 Flash (with image support), Qwen QWQ-32B, and Mistral Nemo.
- **Custom roles/personas:** Define and persist custom roles (system prompts) to guide the assistant's behavior. Each chat can have its own role.
- **Image input:** For models that support images (e.g., Gemini 2.0 Flash), you can upload images directly from your computer.
- **Chat history:** All conversations and messages are stored in a local SQLite database. You can revisit and continue previous chats.
- **User-friendly interface:** Built with Streamlit for a clean, interactive experience.

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd wrapperopenroute
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Add your OpenRouter API key:**
   - Create a file named `secrets.json` in the project root with the following content:
     ```json
     {
       "openroute_api_key": "YOUR_OPENROUTER_API_KEY"
     }
     ```

4. **Run the app:**
   ```bash
   streamlit run app.py
   ```

## Usage

- **Start a new chat:** Click "➕ New Chat" in the sidebar.
- **Select a model:** Choose from the available models in the sidebar. Some models (like Gemini 2.0 Flash) allow image uploads.
- **Create/select a role:** In the sidebar, create a new role/persona (system prompt) or select an existing one. Each chat can have its own role.
- **Send messages:** Type your message at the bottom and press Enter. For image-capable models, you can also upload an image.
- **View history:** All your chats are listed in the sidebar. Click any to revisit and continue the conversation.

## Example

1. Create a role called "Chef" with the description: `You are a professional chef who gives cooking advice.`
2. Start a new chat, select the "Chef" role, and choose a model.
3. Type: `What is a good recipe for dinner?`
4. (Optional) If using Gemini 2.0 Flash, upload an image of ingredients.
5. The assistant will respond, influenced by the selected role.

## Technologies Used
- [Streamlit](https://streamlit.io/)
- [OpenRouter API](https://openrouter.ai/)
- [SQLite](https://www.sqlite.org/)
- [OpenAI Python SDK](https://github.com/openai/openai-python)

## License
MIT (c) 2025 
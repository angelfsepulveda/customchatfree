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

from openai import OpenAI
import json
import requests


def _load_api_key() -> str:
    """
    Carga la API key desde un archivo secrets.json local.
    Asume que el archivo está en el directorio raíz del proyecto.
    """
    try:
        with open("secrets.json", "r") as f:
            secrets = json.load(f)
        return secrets
    except FileNotFoundError:
        raise FileNotFoundError("El archivo 'secrets.json' no se encontró. Asegúrate de que exista en el directorio raíz.")
    except KeyError:
        raise KeyError("La clave 'openroute_api_key' no se encontró en secrets.json.")


def get_client():
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=_load_api_key()['openroute_api_key'],  # Carga la key desde el archivo JSON
    )


class ModelsData:
    """
    Clase para gestionar respuestas de modelos OpenRouter compatibles con OpenAI.
    Usa el patrón Factory Method para seleccionar el modelo.
    """
    def __init__(self):
        secrets = _load_api_key()
        self.api_key = secrets['openroute_api_key']
        self.client = get_client()
        self.extra_headers = {
            "HTTP-Referer": "https://tuapp.streamlit.app",  # Opcional
            "X-Title": "Mi Streamlit App",  # Opcional
        }
        self.extra_body = {}

    def get_response(self, message: str, model_name: str, system_message: str = None) -> str:
        """
        Factory Method para obtener la respuesta de un modelo dado su nombre.
        Permite incluir un mensaje de sistema (system prompt) si se proporciona.
        """
        model_methods = {
            "deepseek_v3": self.deepseek_v3,
            "kimi": self.kimi,
            "gemini_flash": self.gemini_flash,
            "qwq_32b": self.qwq_32b,
            "mistral_nemo": self.mistral_nemo,
        }
        method = model_methods.get(model_name)
        if not method:
            return f"[Modelo '{model_name}' no soportado]"
        return method(message, system_message=system_message) if model_name == "gemini_flash" else method(message, system_message) if system_message else method(message)

    def deepseek_v3(self, message: str, system_message: str = None) -> str:
        """
        Envía un mensaje a DeepSeek Chat v3 (deepseek/deepseek-chat-v3-0324:free).
        """
        try:
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": message})
            completion = self.client.chat.completions.create(
                extra_headers=self.extra_headers,
                extra_body=self.extra_body,
                model="deepseek/deepseek-chat-v3-0324:free",
                messages=messages
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"[Error al contactar a DeepSeek Chat v3: {e}]"

    def kimi(self, message: str, system_message: str = None) -> str:
        """
        Envía un mensaje a Kimi (moonshotai/kimi-k2:free).
        """
        try:
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": message})
            completion = self.client.chat.completions.create(
                extra_headers=self.extra_headers,
                extra_body=self.extra_body,
                model="moonshotai/kimi-k2:free",
                messages=messages
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"[Error al contactar a Kimi: {e}]"

    def gemini_flash(self, message: str, image_url: str = None, system_message: str = None) -> str:
        """
        Envía un mensaje a Gemini 2.0 Flash (google/gemini-2.0-flash-exp:free).
        Si image_url se proporciona, envía texto e imagen; si no, solo texto.
        Si system_message se proporciona, lo envía como mensaje de sistema.
        """
        try:
            content = []
            if system_message:
                content.append({"type": "text", "text": system_message})
            content.append({"type": "text", "text": message})
            if image_url:
                content.append({"type": "image_url", "image_url": {"url": image_url}})
            messages = [
                {
                    "role": "user" if not system_message else "system",
                    "content": content if not system_message else [{"type": "text", "text": system_message}],
                }
            ]
            if system_message:
                # system + user (+ image)
                messages = [
                    {"role": "system", "content": [{"type": "text", "text": system_message}]},
                    {"role": "user", "content": [{"type": "text", "text": message}] + ([{"type": "image_url", "image_url": {"url": image_url}}] if image_url else [])}
                ]
            completion = self.client.chat.completions.create(
                extra_headers=self.extra_headers,
                extra_body=self.extra_body,
                model="google/gemini-2.0-flash-exp:free",
                messages=messages
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"[Error al contactar a Gemini 2.0 Flash: {e}]"

    def qwq_32b(self, message: str, system_message: str = None) -> str:
        """
        Envía un mensaje a Qwen QWQ-32B (qwen/qwq-32b:free).
        """
        try:
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": message})
            completion = self.client.chat.completions.create(
                extra_headers=self.extra_headers,
                extra_body=self.extra_body,
                model="qwen/qwq-32b:free",
                messages=messages
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"[Error al contactar a Qwen QWQ-32B: {e}]"

    def mistral_nemo(self, message: str, system_message: str = None) -> str:
        """
        Envía un mensaje a Mistral Nemo (mistralai/mistral-nemo:free).
        """
        try:
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": message})
            completion = self.client.chat.completions.create(
                extra_headers=self.extra_headers,
                extra_body=self.extra_body,
                model="mistralai/mistral-nemo:free",
                messages=messages
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"[Error al contactar a Mistral Nemo: {e}]"


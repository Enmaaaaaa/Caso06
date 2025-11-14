import streamlit as st
from pymongo import MongoClient
from bson import ObjectId
import google.generativeai as genai
import json
import re
import os

# ======================================================
# CONFIG STREAMLIT (ESTILO)
# ======================================================
st.set_page_config(page_title="Restaurante IA", page_icon="🍽", layout="wide")

st.markdown("""
    <style>
        .titulo {
            font-size: 40px;
            font-weight: bold;
            color: #FF6F3C;
            text-align: center;
        }
        .subtitulo {
            font-size: 22px;
            font-weight: bold;
            color: #444444;
        }
        .card {
            padding: 20px;
            border-radius: 12px;
            background-color: #FFF3E0;
            border: 1px solid #FFB07C;
            margin-top: 10px;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# ======================================================
# CONFIG GEMINI (Con variables de entorno secure)
# ======================================================
GEMINI_API_KEY = os.getenv("AIzaSyAoebzpsto9Az8tEp_Bc3C-PkLrbIhCuIk")
if not GEMINI_API_KEY:
    st.error("❌ Falta la variable de entorno GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)
modelo = genai.GenerativeModel("gemini-1.5-flash")

# ======================================================
# PROMPT Conversacional del Chatbot
# ======================================================
SYSTEM_PROMPT = """
Eres un chatbot especializado en pedidos de restaurante.

Tu trabajo:
- Saludar con cortesía.
- Preguntar qué desea pedir el cliente.
- Identificar productos, cantidades y observaciones.
- Guiar paso a paso hasta completar el pedido.
- SOLO cuando el pedido esté completo, devolver un JSON válido con el formato:

{
    "cliente": "",
    "items": [
        {"producto": "", "cantidad": 0}
    ],
    "observaciones": ""
}

IMPORTANTE:
- No escribas explicaciones fuera del JSON final.
- Si el pedido NO está completo, responde de forma conversacional.
"""

# ======================================================
# GENERAR RESPUESTA DEL CHATBOT
# ======================================================
def generar_respuesta(history, user_msg):
    mensajes = [{"role": "user", "parts": SYSTEM_PROMPT}]
    mensajes.extend(history)
    mensajes.append({"role": "user", "parts": user_msg})

    respuesta = modelo.generate_content(mensajes)
    return respuesta.text

# ======================================================
# EXTRACCIÓN DE JSON
# ======================================================
def limpiar_json(texto):
    texto = texto.replace("```json", "").replace("```", "")
    match = re.search(r"\{[\s\S]*\}", texto)
    return match.group(0) if match else None

# ======================================================
# CONFIG MONGO
# ======================================================
MONGO_URI = os.getenv("mongodb+srv://enmacondor_db_user:12344321@clustercaso06.azxhney.mongodb.net/?retryWrites=true&w=majority")
if not MONGO_URI:
    st.error("❌ Falta la variable de entorno MONGO_URI")
    st.stop()

client = MongoClient(MONGO_URI)
db = client["restaurante_smartbuild"]
pedidos = db["pedidos"]

# CRUD
def crear_pedido(data):
    return pedidos.insert_one(data)

def listar_pedidos():
    return list(pedidos.find())

def actualizar_pedido(id, data):
    return pedidos.update_one({"_id": ObjectId(id)}, {"$set": data})

def eliminar_pedido(id):
    return pedidos.delete_one({"_id": ObjectId(id)})

# ======================================================
# UI - TABS
# ======================================================
tab1, tab2 = st.tabs(["🤖 Chatbot conversacional", "📂 Gestión de pedidos"])

# ======================================================
# TAB 1 — CHATBOT
# ======================================================
with tab1:
    st.markdown('<p class="titulo">🤖 Chatbot Inteligente para Pedidos</p>', unsafe_allow_html=True)

    if "history" not in st.session_state:
        st.session_state.history = []
    if "chat" not in st.session_state:
        st.session_state.chat = []

    # Mostrar historial
    for role, msg in st.session_state.chat:
        if role == "user":
            st.markdown(f"**👤 Tú:** {msg}")
        else:
            st.markdown(f"**🤖 Bot:** {msg}")

    user_input = st.text_input("Escribe tu mensaje:")

    if st.button("Enviar"):
        if user_input.strip() == "":
            st.warning("Ingresa un mensaje.")
        else:
            st.session_state.chat.append(("user", user_input))
            st.session_state.history.append({"role": "user", "parts": user_input})

            respuesta = generar_respuesta(st.session_state.history, user_input)

            st.session_state.chat.append(("bot", respuesta))
            st.session_state.history.append({"role": "model", "parts": respuesta})

            st.rerun()

    st.markdown("---")
    st.markdown("### 🧾 Intento de extracción JSON")

    if st.session_state.chat:
        ultimo = st.session_state.chat[-1][1]
        json_detectado = limpiar_json(ultimo)

        if json_detectado:
            try:
                pedido_json = json.loads(json_detectado)
                st.success("JSON válido detectado")
                st.json(pedido_json)

                if st.button("💾 Guardar Pedido"):
                    crear_pedido(pedido_json)
                    st.success("✔ Pedido guardado correctamente")
                    st.session_state.history = []
                    st.session_state.chat = []
                    st.rerun()
            except:
                st.error("❌ El JSON detectado no es válido.")
        else:
            st.info("Aún no hay JSON. Sigue conversando para completar el pedido.")

# ======================================================
# TAB 2 — CRUD
# ======================================================
with tab2:
    st.markdown('<p class="titulo">📂 Gestión de Pedidos</p>', unsafe_allow_html=True)

    lista = listar_pedidos()

    if not lista:
        st.info("No hay pedidos registrados aún.")
    else:
        for p in lista:
            st.markdown('<div class="card">', unsafe_allow_html=True)

            st.markdown(f"### 🧾 ID Pedido: {p['_id']}")
            st.json(p)

            nuevo_cliente = st.text_input(
                "Editar nombre del cliente:",
                value=p.get("cliente", ""),
                key=f"cliente_{p['_id']}"
            )

            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("Actualizar", key=f"update_{p['_id']}"):
                    actualizar_pedido(p["_id"], {"cliente": nuevo_cliente})
                    st.success("✔ Pedido actualizado")
                    st.experimental_rerun()

            with col2:
                if st.button("Eliminar", key=f"delete_{p['_id']}"):
                    eliminar_pedido(p["_id"])
                    st.error("🗑 Pedido eliminado")
                    st.experimental_rerun()

            st.markdown('</div>', unsafe_allow_html=True)

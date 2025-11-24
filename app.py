import streamlit as st
from openai import OpenAI
import os
import base64

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Sister Hope - IVF Companion",
    page_icon="🇸🇬",
    layout="centered"
)

# --- CSS FOR CHAT STYLING ---
st.markdown("""
<style>
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
    }
    .user-message {
        background-color: #e6f3ff;
    }
    .bot-message {
        background-color: #fff0f5;
    }
</style>
""", unsafe_allow_html=True)

# --- INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Check if the key is in the "Secrets" (Cloud) or Session State
if "openai_api_key" not in st.session_state:
    # Try to load from Streamlit Secrets
    if "OPENAI_API_KEY" in st.secrets:
        st.session_state.openai_api_key = st.secrets["OPENAI_API_KEY"]
    else:
        st.session_state.openai_api_key = ""

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.title("⚙️ Settings")
    
    # Only show input if we don't have a key yet
    if not st.session_state.openai_api_key:
        api_key_input = st.text_input("OpenAI API Key", type="password")
        if api_key_input:
            st.session_state.openai_api_key = api_key_input
    else:
        st.success("✅ System Connected (Sister Hope is ready)")
    
    st.divider()
    enable_audio = st.toggle("Enable Audio Response (Hear Sister Hope)", value=False)
    st.info("Note: Enabling audio consumes more tokens/credits.")
    
    st.divider()
    st.markdown("**Disclaimer:** *I am an AI, not a doctor. My advice is for comfort and info only. Please always consult your fertility specialist in Singapore.*")

# --- HELPER FUNCTIONS ---

def get_ai_client():
    if not st.session_state.openai_api_key:
        return None
    return OpenAI(api_key=st.session_state.openai_api_key)

def text_to_speech(client, text):
    """Converts text to speech using OpenAI TTS"""
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="shimmer", # 'Shimmer' has a warm, female tone
            input=text
        )
        # Save to a temporary file or stream directly
        # Here we stream to base64 for streamlit audio player
        audio_bytes = response.content
        return audio_bytes
    except Exception as e:
        st.error(f"Error generating audio: {e}")
        return None

def speech_to_text(client, audio_file):
    """Converts uploaded audio to text using Whisper"""
    try:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
        )
        return transcription.text
    except Exception as e:
        st.error(f"Error transcribing audio: {e}")
        return None

def get_singlish_response(client, user_input):
    """The core logic with the Persona Prompt"""
    
    system_prompt = """
    You are "Sister Hope", a warm, compassionate, and encouraging IVF companion for women in Singapore. 
    
    Your Persona:
    1. **Tone:** Big sister energy. Gentle, non-judgmental, optimistic but realistic.
    2. **Language Style:** Use Singaporean English (Singlish) naturally. Use particles like 'lah', 'lor', 'meh', 'sia', 'can', 'don't worry'. 
    3. **Terms:** Use terms like 'sayang' (dear/love), 'jiayou' (keep going), 'baby dust'.
    4. **Knowledge:** You are an expert on IVF processes (stimulation, retrieval, transfer, TWW). 
    5. **Context:** References local context like KK Hospital, NUH, Thomson, CPF Medisave usage for IVF if asked.
    
    Crucial Rules:
    - If the user seems stressed, comfort them first before answering facts.
    - ALWAYS include a gentle disclaimer that you are not a doctor and they should see their specialist for medical decisions.
    - Keep responses concise and easy to read on a phone.
    """

    # Prepare the conversation history for the API
    messages = [{"role": "system", "content": system_prompt}]
    # Add last few messages for context (keep it lightweight)
    for msg in st.session_state.messages[-5:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="gpt-4o", # or gpt-3.5-turbo
        messages=messages,
        temperature=0.7
    )
    return response.choices[0].message.content

# --- MAIN APP INTERFACE ---

st.title("Sayang IVF Bot 🇸🇬 ❤️")
st.write("Hi Sayang, got questions about IVF? Or just need someone to talk to? Sister Hope is here for you.")

# Warning if no key
if not st.session_state.openai_api_key:
    st.warning("⚠️ Please enter your OpenAI API Key in the sidebar to start chatting!")
    st.stop()

client = get_ai_client()

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- INPUT AREA (Text or Voice) ---
input_cols = st.columns([4, 1])

# Audio Input (Streamlit 1.39+ feature)
audio_value = st.audio_input("Record your question (or type below)")

user_input = None

# Check if Audio was recorded
if audio_value:
    # Only process if we haven't processed this specific audio buffer yet
    # (Streamlit reruns script on interaction, simple check to prevent double submit)
    with st.spinner("Listening ah..."):
        transcribed_text = speech_to_text(client, audio_value)
        if transcribed_text:
            user_input = transcribed_text

# Check for Text Input (Standard chat input)
if prompt := st.chat_input("Type your message here..."):
    user_input = prompt

# --- PROCESSING RESPONSE ---
if user_input:
    # 1. Add user message to state
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2. Generate AI Response
    with st.chat_message("assistant"):
        with st.spinner("Sister Hope is thinking..."):
            response_text = get_singlish_response(client, user_input)
            st.markdown(response_text)
            
            # 3. Generate Audio if enabled
            if enable_audio:
                audio_data = text_to_speech(client, response_text)
                if audio_data:
                    st.audio(audio_data, format="audio/mp3", autoplay=True)

    # 4. Save assistant message to state
    st.session_state.messages.append({"role": "assistant", "content": response_text})
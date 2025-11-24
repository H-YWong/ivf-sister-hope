import streamlit as st
from openai import OpenAI
import os

# --- 1. PAGE CONFIGURATION (KKIVF BRANDING) ---
st.set_page_config(
    page_title="KKIVF - Journey Companion",
    page_icon="🏥",
    layout="centered"
)

# --- CSS STYLING ---
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
    /* Logo Style Header */
    .header-text {
        color: #d63384; 
        font-weight: bold;
        font-size: 3em;
        margin-bottom: 0px;
    }
    .sub-text {
        color: #666;
        font-size: 1.2em;
        margin-top: -10px;
        margin-bottom: 30px;
    }
</style>
""", unsafe_allow_html=True)

# --- INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- API KEY HANDLING (SECRETS OR MANUAL) ---
# This allows you to deploy it and pay for it, OR let users enter their own key
if "openai_api_key" not in st.session_state:
    if "OPENAI_API_KEY" in st.secrets:
        st.session_state.openai_api_key = st.secrets["OPENAI_API_KEY"]
    else:
        st.session_state.openai_api_key = ""

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Only ask for Key if not found in Secrets
    if not st.session_state.openai_api_key:
        api_key_input = st.text_input("OpenAI API Key", type="password")
        if api_key_input:
            st.session_state.openai_api_key = api_key_input
    else:
        st.success("✅ System Online (KKIVF Access)")
    
    st.divider()
    enable_audio = st.toggle("Enable Voice Response", value=False)
    
    st.divider()
    st.info("**Emergency:** If you experience severe pain or heavy bleeding, please proceed to KKH O&G 24-hour Urgent Care Centre immediately.")

# --- HELPER FUNCTIONS ---

def get_ai_client():
    if not st.session_state.openai_api_key:
        return None
    return OpenAI(api_key=st.session_state.openai_api_key)

def text_to_speech(client, text):
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="shimmer",
            input=text
        )
        return response.content
    except Exception as e:
        st.error(f"Audio Error: {e}")
        return None

def speech_to_text(client, audio_file):
    try:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file
        )
        return transcription.text
    except Exception as e:
        st.error(f"Transcription Error: {e}")
        return None

def get_singlish_response(client, user_input):
    """
    STRICT SINGAPORE CONTEXT PROMPT
    """
    system_prompt = """
    You are the "KKIVF Companion", a digital support assistant for patients undergoing IVF at KK Women's and Children's Hospital (KKH) in Singapore.
    
    **Your Persona:**
    1.  **Tone:** Warm, "Big Sister", compassionate, and distinctly Singaporean. Use particles like 'lah', 'lor', 'mah', 'can', 'don't worry'.
    2.  **Role:** Offer emotional support and practical information specific to Singapore.

    **Your Knowledge Base (STRICTLY SINGAPOREAN):**
    1.  **Financial:** When asked about cost, mention **Medisave** withdrawal limits (e.g., $6,000 for first cycle, $5,000 for second) and **Government Co-Funding** (up to 75% for eligible couples). 
    2.  **Locations:** Refer to KKH IVF Centre, KKH O&G Urgent Care (for emergencies), or generic polyclinic referrals.
    3.  **Process:** Explain the standard protocol: Stimulation -> Egg Retrieval (OT) -> Transfer -> TWW (Two Week Wait) -> Blood Test at clinic.
    4.  **Support:** Suggest local things like "drink warm water", "eat chicken essence/bird nest" (if culturally appropriate), or "take MC and rest".
    
    **Safety Rules:**
    - ALWAYS include a disclaimer: "I am an AI companion, not a doctor. Please check with your KKH coordinator or specialist."
    - If the user mentions heavy bleeding or severe pain, tell them to go to KKH O&G Urgent Care immediately.
    """

    messages = [{"role": "system", "content": system_prompt}]
    for msg in st.session_state.messages[-5:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    messages.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="gpt-4o", 
        messages=messages,
        temperature=0.7
    )
    return response.choices[0].message.content

# --- MAIN APP INTERFACE ---

# Custom Branding Header
st.markdown('<p class="header-text">KKIVF 🏥</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-text">Your compassionate guide through the IVF journey.</p>', unsafe_allow_html=True)

if not st.session_state.openai_api_key:
    st.warning("⚠️ Please provide an API Key in the sidebar (or configure Secrets) to start.")
    st.stop()

client = get_ai_client()

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- INPUT AREA ---
audio_value = st.audio_input("Record your question (tap microphone)")
user_input = None

if audio_value:
    with st.spinner("Listening..."):
        transcribed_text = speech_to_text(client, audio_value)
        if transcribed_text:
            user_input = transcribed_text

if prompt := st.chat_input("Type your message here..."):
    user_input = prompt

# --- PROCESSING ---
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response_text = get_singlish_response(client, user_input)
            st.markdown(response_text)
            
            if enable_audio:
                audio_data = text_to_speech(client, response_text)
                if audio_data:
                    st.audio(audio_data, format="audio/mp3", autoplay=True)

    st.session_state.messages.append({"role": "assistant", "content": response_text})

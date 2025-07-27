import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
from dotenv import load_dotenv
import os
import re
from gtts import gTTS
import tempfile
from googletrans import Translator
import pandas as pd
from datetime import datetime

# Load Gemini API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash-8b")

# Translator for language detection
translator = Translator()

# Save feedback to CSV
FEEDBACK_FILE = "feedback.csv"

def save_feedback(email, feedback):
    df = pd.DataFrame([{
        "timestamp": datetime.now().isoformat(),
        "email": email,
        "feedback": feedback
    }])
    
    if os.path.exists(FEEDBACK_FILE):
        df.to_csv(FEEDBACK_FILE, mode="a", index=False, header=False, encoding="utf-8")
    else:
        df.to_csv(FEEDBACK_FILE, index=False, encoding="utf-8")

# Clean PDF text
def clean_text(text):
    return re.sub(r'\s+', ' ', text.strip().lower())

def extract_text_from_pdf(pdf_file):
    doc = fitz.open(pdf_file)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    return clean_text(full_text)

# Answer generation
def generate_answers(content, query):
    prompt = f'''
    You are a perfect Islamic banking bot. Based on the following content:
    {content}

    Answer the following query:
    {query}

    Provide a concise, relevant and precise Shari'ah based answer. If query is about any hadees or Quran verse, provide arabic and english translation both
    '''
    try:
        response = model.generate_content(prompt)
        return response.candidates[0].content.parts[0].text if response.candidates else "No answer generated."
    except Exception as e:
        return f"Error: {str(e)}"

# Detect language for TTS
def detect_language(text):
    try:
        detected = translator.detect(text)
        return detected.lang if detected.lang in ["en", "ar", "ur"] else "en"
    except:
        return "en"


# Text-to-speech
def text_to_speech(text, lang="en"):
    try:
        # Only use supported languages
        supported_langs = ["en", "ar", "ur"]
        lang = lang if lang in supported_langs else "en"
        
        tts = gTTS(text=text, lang=lang, slow=False)
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp_file.name)
        return tmp_file.name
    except Exception as e:
        print("TTS Error:", e)
        return None
# Streamlit page setup
st.set_page_config(page_title="🕌 Shari’ah Guide", layout="centered")
st.header("🕌 Shari’ah Guide – Islamic Banking Chatbot")
st.markdown("🕌 *Ask anything about Islamic Banking and get a Shari’ah-compliant answer powered by AI.*")


# Load and cache PDF content
@st.cache_data
def load_pdf_content():
    return extract_text_from_pdf("islamic banking.pdf")

if "pdf_content" not in st.session_state:
    st.session_state["pdf_content"] = load_pdf_content()

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("audio"):
            st.audio(msg["audio"], format="audio/mp3")

# Input field
user_query = st.chat_input("Ask about Islamic banking...")

# Only respond to Islamic finance related queries
def is_islamic_banking_query(query):
    keywords = [
        "islamic", "halal", "haram", "shariah", "shari’ah", "riba",
        "interest", "mudarabah", "musharakah", "ijarah", "murabaha",
        "takaful", "profit", "loan", "finance", "bank", "investment",
        "islamic banking", "karz", "sood", "bay", "sukuk"
    ]
    query = query.lower()
    return any(k in query for k in keywords)

# Handle user query
if user_query:
    with st.chat_message("user"):
        st.markdown(user_query)
    st.session_state.messages.append({"role": "user", "content": user_query})

    if is_islamic_banking_query(user_query):
        with st.chat_message("assistant"):
            with st.spinner("🔍 Generating answer..."):
                answer = generate_answers(st.session_state["pdf_content"], user_query)
                st.markdown(answer)
                lang = detect_language(answer)
                with st.spinner(f"🔊 Generating audio ({lang})..."):
                    audio_path = text_to_speech(answer, lang=lang)
                    audio_bytes = open(audio_path, "rb").read()
                    st.audio(audio_bytes, format="audio/mp3")
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "audio": audio_bytes
        })
    else:
        warning = "⚠️This bot is specifically designed for **Islamic Banking**, Please ask a relevant question only."
        with st.chat_message("assistant"):
            st.warning(warning)
        st.session_state.messages.append({"role": "assistant", "content": warning})
        # 📢 Sidebar Feedback
    st.sidebar.title("📢 Feedback")
    st.sidebar.markdown("We value your feedback to improve the bot.")

    with st.sidebar.form("feedback_form"):
        user_email = st.text_input("📧 Your Email (optional)")
        user_feedback = st.text_area("💬 Your Feedback", placeholder="Type your comments...")
        submitted = st.form_submit_button("Submit")
    if submitted:
        save_feedback(user_email, user_feedback)
        st.sidebar.success("✅ Thank you for your feedback!")

st.sidebar.markdown("---")  
st.sidebar.header("👨‍💻 About the Developer")
st.sidebar.markdown("""
**Name:** Maria Hameed  
**Role:** Islamic Banking AI Developer  
**Email:** hameed.maria06@gmail.com 
**LinkedIn:** www.linkedin.com/in/maria-hameed1987
""")

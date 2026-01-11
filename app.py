import streamlit as st
import requests
from bs4 import BeautifulSoup
from google import genai
import time
from streamlit_autorefresh import st_autorefresh

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Pogoda & Air Śląsk AI", page_icon="🌤️")

# --- FUNKCJE POMOCNICZE ---
def get_weather_theme(text):
    text = text.lower()
    if "deszcz" in text: return "linear-gradient(180deg, #1e3c72 0%, #2a5298 100%)", "🌧️"
    if "śnieg" in text: return "linear-gradient(180deg, #83a4d4 0%, #b6fbff 100%)", "❄️"
    if "słońce" in text or "słoneczn" in text: return "linear-gradient(180deg, #f8b500 0%, #fceabb 100%)", "☀️"
    if "pochmurno" in text or "chmury" in text: return "linear-gradient(180deg, #373b44 0%, #4286f4 100%)", "☁️"
    return "linear-gradient(180deg, #0f2027 0%, #2c5364 100%)", "🌤️"

def fetch_data():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        res = requests.get("https://pogodadlaslaska.pl/", timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        tekst_strony = soup.get_text(separator=' ', strip=True)[:8000]

        client = genai.Client(api_key=api_key)
        prompt = (
            "Przygotuj prognozę dla Śląska. Format odpowiedzi:\n"
            "Linia 1: temperatura,wiatr,jakość_powietrza(opisowa)\n"
            "Linia 2: JEDNA INTELIGENTNA RADA (np. o praniu, rowerze, aucie)\n"
            "Reszta: Krótki opis tekstowy z ikonami.\n\n"
            f"Dane: {tekst_strony}"
        )
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        st.session_state['last_forecast'] = response.text
        st.session_state['last_update'] = time.strftime("%H:%M:%S")
    except Exception as e:
        st.error(f"Błąd: {e}")

# --- LOGIKA SESJI ---
if 'last_forecast' not in st.session_state:
    st.session_state['last_forecast'] = None

# Auto-refresh co 1h
st_autorefresh(interval=3600000, key="fscounter")

# --- INTERFEJS I STYLE ---
if st.session_state['last_forecast']:
    raw_text = st.session_state['last_forecast']
    lines = raw_text.split('\n')
    data = lines[0].split(',')
    temp, wind, air = data[0], data[1], data[2]
    advice = lines[1]
    main_text = "\n".join(lines[2:])
    
    bg_color, main_icon = get_weather_theme(main_text)

    # DYNAMICZNY CSS
    st.markdown(f"""
        <style>
        .stApp {{
            background: {bg_color};
            color: white;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            margin-bottom: 10px;
        }}
        .advice-card {{
            background: rgba(0, 255, 127, 0.2);
            padding: 15px;
            border-left: 5px solid #00ff7f;
            border-radius: 10px;
            font-style: italic;
        }}
        </style>
    """, unsafe_allow_html=True)

    # WYŚWIETLANIE
    st.title("🌤️ Śląsk AI Dashboard")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(f"<h1 style='font-size: 80px;'>{main_icon}</h1>", unsafe_allow_html=True)
        st.metric("Temperatura", f"{temp}°C")
    with col2:
        st.write("") # Odstęp
        st.write(f"💨 Wiatr: **{wind} km/h**")
        st.write(f"🌫️ Powietrze: **{air}**")
        if st.button("ODŚWIEŻ"): fetch_data()

    st.markdown(f"<div class='advice-card'>💡 <b>Rada AI:</b> {advice}</div>", unsafe_allow_html=True)
    
    st.markdown("### 📝 Prognoza szczegółowa")
    st.markdown(f"<div class='card'>{main_text}</div>", unsafe_allow_html=True)
    
    st.caption(f"Aktualizacja: {st.session_state.get('last_update', '---')}")

else:
    st.title("🌤️ Śląsk AI")
    if st.button("URUCHOM APLIKACJĘ"): fetch_data()

import streamlit as st
import requests
from bs4 import BeautifulSoup
from google import genai
import time
import re
from streamlit_autorefresh import st_autorefresh

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Śląski Bard: Pogoda AI", page_icon="⚒️", layout="centered")

def get_weather_theme(text):
    text = text.lower()
    if any(word in text for word in ["deszcz", "loć", "opady"]):
        return "linear-gradient(180deg, #1e3c72 0%, #2a5298 100%)", "🌧️", "white"
    if any(word in text for word in ["śnieg", "mróz", "zimno"]):
        return "linear-gradient(180deg, #83a4d4 0%, #b6fbff 100%)", "❄️", "#1e3c72"
    if any(word in text for word in ["słońce", "słoneczn", "pogodn", "ciepło"]):
        return "linear-gradient(180deg, #f8b500 0%, #fceabb 100%)", "☀️", "#212121"
    return "linear-gradient(180deg, #0f2027 0%, #2c5364 100%)", "🌤️", "white"

# --- 2. POBIERANIE PRECYZYJNEJ TEMP (METEO API) ---
def get_precise_temp():
    """Pobiera aktualną temperaturę z profesjonalnego API (jak Google)."""
    try:
        # Lokalizacja: Rybnik/Śląsk
        url = "https://api.open-meteo.com/v1/forecast?latitude=50.0971&longitude=18.5417&current_weather=true"
        response = requests.get(url).json()
        return response['current_weather']['temperature']
    except:
        return None

# --- 3. SILNIK AI (PROGNOZA LOKALNA) ---
def fetch_data():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        
        # Pobieramy precyzyjną temp z API zamiast polegać tylko na tekście
        precise_now = get_precise_temp()
        
        # Pobieramy opis barda ze strony
        res = requests.get("https://pogodadlaslaska.pl/", timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        tekst_strony = soup.get_text(separator=' ', strip=True)[:10000]

        client = genai.Client(api_key=api_key)
        
        prompt = (
            f"Analizuj dane: \n{tekst_strony}\n\n"
            f"Jesteś Śląskim Bardem. Mówisz zrozumiale po polsku z lekkim akcentem. \n"
            f"Zasugeruj się, że teraz jest około {precise_now}°C.\n"
            f"Odpowiedz DOKŁADNIE tak:\n"
            f"INFO: [wiatr km/h], [jakość powietrza]\n"
            f"RADA: [krótka rada z humorem]\n"
            f"PROGNOZA_LISTA:\n"
            f"[Ikona] [Pora]| [Temp]| [Opis zrozumiały]"
        )
        
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        
        st.session_state['last_forecast'] = response.text
        st.session_state['current_temp'] = precise_now
        st.session_state['last_update'] = time.strftime("%H:%M:%S")
    except Exception as e:
        st.error(f"Feler: {e}")

# --- 4. INTERFEJS ---
if 'last_forecast' not in st.session_state:
    st.session_state['last_forecast'] = None

st_autorefresh(interval=3600000, key="weather_refresh")

if st.session_state['last_forecast']:
    raw_text = st.session_state['last_forecast']
    
    # Wyciąganie danych
    info_match = re.search(r"INFO:\s*(.*)", raw_text)
    rada_match = re.search(r"RADA:\s*(.*)", raw_text)
    
    info_text = info_match.group(1).split('\n')[0] if info_match else "Brak danych"
    advice = rada_match.group(1).split('\n')[0] if rada_match else "Głowa do góry!"
    clean_temp = st.session_state.get('current_temp', '??')

    # Lista prognozy
    list_part = raw_text.split("PROGNOZA_LISTA:")[-1].strip()
    forecast_lines = [l.strip() for l in list_part.split('\n') if "|" in l]

    bg_color, main_icon, font_color = get_weather_theme(raw_text)

    st.markdown(f"""
        <style>
        .stApp {{ background: {bg_color}; background-attachment: fixed; }}
        h1, h2, h3, p, span, div {{ color: {font_color} !important; font-family: 'Segoe UI'; }}
        .main-card {{ background: rgba(0,0,0,0.1); padding: 30px; border-radius: 30px; text-align: center; border: 1px solid rgba(255,255,255,0.1); }}
        .advice-card {{ background: rgba(255, 255, 255, 0.25); padding: 15px; border-radius: 15px; margin: 20px 0; border-left: 5px solid orange; }}
        .forecast-card {{ background: rgba(255, 255, 255, 0.15); padding: 15px; border-radius: 20px; margin-bottom: 10px; backdrop-filter: blur(10px); }}
        </style>
    """, unsafe_allow_html=True)

    st.title("⚒️ Pogoda u Kamila")

    # --- SEKCJA GÓRNA: AKTUALNA TEMP (Z API) ---
    st.markdown(f"""
        <div class="main-card">
            <div style="font-size: 80px; margin-bottom: 5px;">{main_icon}</div>
            <div style="font-size: 20px; text-transform: uppercase; letter-spacing: 2px; opacity: 0.8;">Teraz jest</div>
            <div style="font-size: 100px; font-weight: 900; line-height: 1;">{clean_temp}°</div>
            <div style="font-size: 18px; margin-top: 15px; opacity: 0.9;">{info_text}</div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"<div class='advice-card'>💡 {advice}</div>", unsafe_allow_html=True)

    # --- SEKCJA DOLNA: PROGNOZA (Z AI) ---
    st.markdown("### 🗓️ Co nos czeka (według Damiana D.):")
    for line in forecast_lines:
        parts = line.split('|')
        if len(parts) >= 3:
            st.markdown(f"""
                <div class="forecast-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: bold;">{parts[0].strip()}</span>
                        <span style="background: rgba(0,0,0,0.1); padding: 3px 12px; border-radius: 10px; font-weight: 900;">{parts[1].strip()}</span>
                    </div>
                    <div style="margin-top: 5px; font-size: 0.95em;">{parts[2].strip()}</div>
                </div>
            """, unsafe_allow_html=True)

    if st.button("Odśwież pogodę"):
        fetch_data()
        st.rerun()

else:
    fetch_data()
    st.rerun()


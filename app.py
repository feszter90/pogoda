import streamlit as st
import requests
from bs4 import BeautifulSoup
from google import genai
import time
import re
from streamlit_autorefresh import st_autorefresh

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Śląski Bard: Pogoda AI", page_icon="⚒️", layout="centered")

# --- 2. LOGIKA DYNAMICZNEGO WYGLĄDU (Z KOLOREM CZCIONKI) ---
def get_weather_theme(text):
    text = text.lower()
    # Motyw Deszczowy (Ciemny)
    if any(word in text for word in ["deszcz", "loć", "opady", "mżawka"]):
        return "linear-gradient(180deg, #1e3c72 0%, #2a5298 100%)", "🌧️", "white"
    # Motyw Zimowy (Jasny błękit)
    if any(word in text for word in ["śnieg", "mróz", "pizgo", "bioło"]):
        return "linear-gradient(180deg, #83a4d4 0%, #b6fbff 100%)", "❄️", "#1e3c72"
    # Motyw Słoneczny (Jasny żółty) -> TUTAJ ZMIENIAMY NA CZARNY TEKST
    if any(word in text for word in ["słońce", "słoneczn", "pogodn", "hic", "bezchmurnie"]):
        return "linear-gradient(180deg, #f8b500 0%, #fceabb 100%)", "☀️", "#212121"
    # Motyw Domyślny / Pochmurny (Ciemny)
    return "linear-gradient(180deg, #0f2027 0%, #2c5364 100%)", "🌤️", "white"

# --- 3. SILNIK AI (GEMINI 2.5 FLASH) ---
def fetch_data():
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        res = requests.get("https://pogodadlaslaska.pl/", timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        tekst_strony = soup.get_text(separator=' ', strip=True)[:10000]

        client = genai.Client(api_key=api_key)
        
        prompt = (
            f"Jesteś Śląskim Bardem. Zanalizuj dane i przygotuj raport PO ŚLĄSKU (gwarą). \n\n"
            f"DANE: \n{tekst_strony}\n\n"
            f"ZWRÓĆ ODPOWIEDŹ DOKŁADNIE W TYM FORMACIE:\n"
            f"Linia 1: [temp_teraz],[wiatr_kmh],[jakość_powietrza]\n"
            f"Linia 2: [Błyskotliwa, mądra rada po śląsku]\n"
            f"Reszta: Każda pora dnia w nowej linii według schematu: [Ikona] [Pora dnia]|[Zakres temp]|[Krótki opis po śląsku]"
        )
        
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        
        st.session_state['last_forecast'] = response.text
        st.session_state['last_update'] = time.strftime("%H:%M:%S")
        st.session_state['update_status'] = "success"
    except Exception as e:
        st.session_state['update_status'] = "error"
        st.error(f"Feler przy pobieraniu danych: {e}")

# --- 4. SESJA I AUTO-REFRESH ---
if 'last_forecast' not in st.session_state:
    st.session_state['last_forecast'] = None

st_autorefresh(interval=3600000, key="weather_refresh")

# --- 5. INTERFEJS UŻYTKOWNIKA ---
if st.session_state['last_forecast']:
    try:
        lines = st.session_state['last_forecast'].strip().split('\n')
        data_line = lines[0].split(',')
        clean_temp = "".join(re.findall(r"[-+]?\d+", data_line[0]))
        wind, air = data_line[1], data_line[2]
        advice = lines[1]
        forecast_body = lines[2:]
        
        # Pobieramy tło, ikonę i dynamiczny kolor czcionki
        bg_color, main_icon, font_color = get_weather_theme(st.session_state['last_forecast'])

        # STYLE CSS (Z poprawionym kontrastem)
        st.markdown(f"""
            <style>
            .stApp {{ background: {bg_color}; background-attachment: fixed; }}
            
            /* Kontener główny - dopasowanie koloru czcionki */
            h1, h2, h3, p, span, div {{ 
                color: {font_color} !important; 
                font-family: 'Arial'; 
            }}

            .main-card {{ 
                background: rgba(0, 0, 0, 0.1); 
                padding: 20px; 
                border-radius: 25px; 
                text-align: center; 
                margin-bottom: 20px; 
                border: 1px solid rgba(255,255,255,0.2);
            }}

            .advice-card {{ 
                background: rgba(0, 255, 127, 0.2); 
                padding: 15px; 
                border-radius: 15px; 
                border-left: 5px solid #008f4f; 
                margin-bottom: 20px; 
                font-style: italic;
                color: {font_color} !important;
            }}

            .forecast-card {{
                background: rgba(255, 255, 255, 0.2); 
                padding: 15px; 
                border-radius: 18px; 
                margin-bottom: 12px; 
                border: 1px solid rgba(0,0,0,0.05);
                backdrop-filter: blur(10px);
            }}
            
            /* Naprawienie widoczności przycisków */
            .stButton>button {{
                color: {font_color};
                border: 1px solid {font_color};
                background: rgba(255,255,255,0.1);
            }}
            </style>
        """, unsafe_allow_html=True)

        st.title("⚒️ Śląski Bard godo:")

        st.markdown(f"""
            <div class="main-card">
                <div style="font-size: 80px;">{main_icon}</div>
                <div style="font-size: 60px; font-weight: bold; color: {font_color} !important;">{clean_temp}°C</div>
                <div style="font-size: 16px; opacity: 0.9;">Wiatr: {wind} km/h | Luft: {air}</div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown(f"<div class='advice-card'>💡 {advice}</div>", unsafe_allow_html=True)

        st.markdown("### 🗓️ Co nos czeko:")
        for line in forecast_body:
            if '|' in line:
                parts = line.split('|')
                time_label, temp_val, desc = parts[0], parts[1], parts[2]
                
                st.markdown(f"""
                    <div class="forecast-card">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <b style="font-size: 1.1em; color: {font_color} !important;">{time_label}</b>
                            <span style="background: rgba(0,0,0,0.1); padding: 3px 12px; border-radius: 10px; font-weight: bold; color: {font_color} !important;">{temp_val}</span>
                        </div>
                        <div style="margin-top: 8px; font-size: 0.95em; opacity: 0.9; color: {font_color} !important;">{desc}</div>
                    </div>
                """, unsafe_allow_html=True)

        if st.button("Odśwież dane"):
            fetch_data()
            st.rerun()

        st.caption(f"Aktualizacja: {st.session_state.get('last_update', '---')}")

    except Exception as e:
        st.error(f"Feler w wyświetlaniu: {e}")
        if st.button("Spróbuj jeszcze roz"):
            fetch_data()
            st.rerun()
else:
    st.title("⚒️ Śląsk AI")
    st.info("Czekej chwilka, Bard szuko rymów o pogodzie...")
    fetch_data()
    st.rerun()

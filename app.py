import streamlit as st
import requests
from bs4 import BeautifulSoup
from google import genai
import time
import re
from streamlit_autorefresh import st_autorefresh

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Pogoda & Air Śląsk AI", page_icon="🌤️", layout="centered")

# --- 2. LOGIKA WYGLĄDU (DYNAMICZNE TŁA) ---
def get_weather_theme(text):
    """Dobiera kolor tła CSS i ikonę na podstawie analizy tekstu z AI."""
    text = text.lower()
    if any(word in text for word in ["deszcz", "opady", "mżawka", "ulewa"]):
        return "linear-gradient(180deg, #1e3c72 0%, #2a5298 100%)", "🌧️"
    if any(word in text for word in ["śnieg", "mróz", "śnieżyca"]):
        return "linear-gradient(180deg, #83a4d4 0%, #b6fbff 100%)", "❄️"
    if any(word in text for word in ["słońce", "słoneczn", "pogodn", "jasno", "bezchmurnie"]):
        return "linear-gradient(180deg, #f8b500 0%, #fceabb 100%)", "☀️"
    if any(word in text for word in ["pochmurno", "chmury", "zachmurzenie", "mgła"]):
        return "linear-gradient(180deg, #373b44 0%, #4286f4 100%)", "☁️"
    return "linear-gradient(180deg, #0f2027 0%, #2c5364 100%)", "🌤️"

# --- 3. POBIERANIE I ANALIZA DANYCH (SILNIK AI) ---
def fetch_data():
    """Główna funkcja pobierająca dane i komunikująca się z Gemini 2.5 Flash."""
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        
        # Pobieranie danych ze strony źródłowej
        res = requests.get("https://pogodadlaslaska.pl/", timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Bierzemy obszerny fragment tekstu (płatny plan pozwala na więcej tokenów)
        tekst_strony = soup.get_text(separator=' ', strip=True)[:12000]

        client = genai.Client(api_key=api_key)
        
        # NOWY, PROFESJONALNY PROMPT
        prompt = (
           f"Jesteś Śląskim Bardem – mądrym, dowcipnym i dumnym mieszkańcem regionu, który o pogodzie opowiada z pasją. "
            f"Twoim zadaniem jest przeanalizowanie poniższych danych i przygotowanie raportu PO ŚLĄSKU (gwarą). \n\n"
            f"DANE WEJŚCIOWE: \n{tekst_strony}\n\n"
            f"ZWRÓĆ ODPOWIEDŹ DOKŁADNIE W TYM FORMACIE:\n"
            f"Linia 1: [liczba_temp_teraz],[wiatr_kmh],[jakość_powietrza_opis]\n"
            f"Linia 2: [Błyskotliwa, rymowana lub mądra rada po śląsku od barda na dzisiej]\n"
            f"Reszta: Szczegółowa prognoza po śląsku. Użyj formatu: \n"
            f"• [Ikona] [Pora dnia]: [Zakres temp, np. 2-5°C] - [Opis po śląsku, np. 'Bydzie loć', 'Gryfne słonko', 'Pizgo złem']\n"
            f"Na końcu dodaj krótkie pozdrowienie 'Szczęść Boże' lub 'Z Panem Bogiem'."
        )
        
        # Wywołanie modelu Gemini 2.5 Flash (Paid Tier)
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        
        # Zapis do sesji
        st.session_state['last_forecast'] = response.text
        st.session_state['last_update'] = time.strftime("%H:%M:%S")
        st.session_state['update_status'] = "success"
    except Exception as e:
        st.session_state['update_status'] = "error"
        st.error(f"Błąd podczas pobierania danych: {e}")

# --- 4. ZARZĄDZANIE SESJĄ I AUTO-REFRESH ---
if 'last_forecast' not in st.session_state:
    st.session_state['last_forecast'] = None
if 'update_status' not in st.session_state:
    st.session_state['update_status'] = "idle"

# Automatyczne odświeżanie co 1 godzinę (dla płatnego planu to koszt bliski zeru)
st_autorefresh(interval=3600000, key="weather_refresh")

# --- 5. INTERFEJS UŻYTKOWNIKA (MOBILE FIRST) ---
if st.session_state['last_forecast']:
    try:
        # Przetwarzanie odpowiedzi od AI
        lines = st.session_state['last_forecast'].split('\n')
        data_line = lines[0].split(',')
        
        # Rozpakowanie Linii 1 (Temp, Wiatr, Powietrze)
        raw_temp = data_line[0]
        wind = data_line[1]
        air = data_line[2]
        
        # Linia 2 (Rada) i Reszta (Prognoza)
        advice = lines[1]
        main_text = "\n".join(lines[2:])
        
        # Oczyszczanie temperatury do samej liczby
        clean_temp = "".join(re.findall(r"[-+]?\d+", raw_temp))
        
        # Dobór motywu wizualnego
        bg_color, main_icon = get_weather_theme(main_text)

        # Style CSS dla efektu iPhone / Glassmorphism
        st.markdown(f"""
            <style>
            .stApp {{ background: {bg_color}; background-attachment: fixed; color: white !important; }}
            .card {{ 
                background: rgba(255, 255, 255, 0.15); 
                padding: 20px; 
                border-radius: 20px; 
                backdrop-filter: blur(15px); 
                border: 1px solid rgba(255, 255, 255, 0.2); 
                margin-top: 15px; 
            }}
            .advice-card {{ 
                background: rgba(0, 255, 127, 0.2); 
                padding: 15px; 
                border-left: 5px solid #00ff7f; 
                border-radius: 12px; 
                margin: 15px 0; 
                font-weight: 500;
            }}
            h1, h2, h3, p, span, div {{ color: white !important; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
            </style>
        """, unsafe_allow_html=True)

    # --- NAGŁÓWEK ---
        st.title("🌤️ Śląsk AI Dashboard")
        
        # SEKCJA GŁÓWNA (Temperatura i ikona)
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown(f"""
                <div style="display: flex; align-items: center; justify-content: center; background: rgba(0,0,0,0.2); border-radius: 25px; padding: 15px;">
                    <span style="font-size: 80px;">{main_icon}</span>
                    <span style="font-size: 65px; font-weight: 900; margin-left: 15px;">{clean_temp}°</span>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.write(f"💨 Wiatr: **{wind} km/h**")
            st.write(f"🌫️ Powietrze: **{air}**")
            if st.button("ODŚWIEŻ TERAZ"):
                fetch_data()
                st.rerun()

        # RADA DNIA
        st.markdown(f"<div class='advice-card'>💡 {advice}</div>", unsafe_allow_html=True)

        # PROGNOZA SZCZEGÓŁOWA
        st.markdown("### 🗓️ Prognoza na dziś i jutro")
        st.markdown(f"<div class='card'>{main_text}</div>", unsafe_allow_html=True)
        
        st.caption(f"Dane zaktualizowane: {st.session_state.get('last_update', '---')}")

    except Exception as e:
        st.error("Wystąpił problem z formatowaniem danych.")
        if st.button("Spróbuj ponownie"):
            fetch_data()
            st.rerun()
else:
    # Pierwsze uruchomienie aplikacji
    st.title("🌤️ Śląsk AI")
    st.info("Inicjalizacja systemu i pobieranie danych pogodowych...")
    fetch_data()
    st.rerun()


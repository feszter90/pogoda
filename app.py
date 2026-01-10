import streamlit as st
import requests
from bs4 import BeautifulSoup
from google import genai

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Pogoda Śląsk AI",
    page_icon="🌤️",
    initial_sidebar_state="collapsed"
)

# Własny styl CSS dla Dark Mode i wyglądu mobilnego
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #007acc; color: white; }
    </style>
    """, unsafe_allow_html=True)

st.title("🌤️ Pogoda dla Śląska")
st.subheader("Analiza Gemini 2.5 Flash")

# Pole na klucz API (możesz wpisać na stałe lub podawać w apce)
api_key = st.secrets["GEMINI_API_KEY"]

if st.button("POBIERZ AKTUALNĄ PROGNOZĘ"):
    if not api_key:
        st.error("Musisz podać klucz API!")
    else:
        with st.spinner("Pobieram dane ze strony i pytam AI..."):
            try:
                # 1. Scraping
                url = "https://pogodadlaslaska.pl/"
                res = requests.get(url, timeout=15)
                soup = BeautifulSoup(res.text, 'html.parser')
                tekst = soup.get_text(separator=' ', strip=True)[:10000]

                # 2. AI
                client = genai.Client(api_key=api_key)
                prompt = (
                    "Jesteś profesjonalnym pogodynką. Na podstawie treści strony: "
                    f"{tekst} przygotuj konkretną i czytelną prognozę dla Śląska. "
                    "Użyj ikon pogodowych, pogrubień i wypunktowania. "
                    "Podziel prognozę na: Dziś, Jutro i Kolejne dni."
                )
                
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )

                # 3. Wyświetlenie wyniku
                st.success("Prognoza gotowa!")
                st.markdown("---")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"Wystąpił błąd: {e}")

st.divider()

st.caption("Źródło danych: pogodadlaslaska.pl")

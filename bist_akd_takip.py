import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import ast
import re

st.set_page_config(page_title="Kurumsal Takip (Çift Ekran)", page_icon="🦅", layout="wide")

st.title("🦅 BİST Kurumsal Takip: Profesyonel Çift Ekran Terminali")
st.markdown("İki farklı tahtayı veya aynı tahtanın farklı saatlerdeki durumunu yükleyip, yapay zeka destekli gün içi trader analizi alabilirsiniz.")

with st.sidebar:
    st.header("⚙️ Ayarlar")
    
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ API Anahtarı sistem kasasından otomatik yüklendi!")
    else:
        api_key = st.text_input("Gemini API Anahtarı:", type="password")
        st.markdown("[Ücretsiz API Anahtarınızı Buradan Alabilirsiniz](https://aistudio.google.com/app/apikey)")
        
    st.markdown("---")
    st.info("💡 Sadece ekran görüntüsünü alıp sürükleyin. Kesme (Crop) yapmanıza bile gerek yoktur.")

KRITIK_KURUMLAR = ["BANK OF AMERICA", "BOFA", "TERA", "CITIBANK", "CİTİBANK", "DEUTSCHE"]

def kurum_tespit(kurum_adi):
    return any(k in str(kurum_adi).upper() for k in KRITIK_KURUMLAR)

def analiz_motoru(resim_dosyasi, api_key):
    genai.configure(api_key=api_key.strip())
    img = Image.open(resim_dosyasi)
    
    # PROMPT'U MARKDOWN JSON FORMATINA ZORLUYORUZ
    prompt = '''
    SEN UZMAN BİR DAY-TRADER VE BİLGİSAYAR SİSTEMİSİN.
    Ekran görüntüsündeki aracı kurum dağılımı (AKD) tablosunu oku.
    
    Bana SADECE VE SADECE aşağıdaki formatta, ```json ve ``` etiketleri arasına alınmış bir veri döndür.
    Bunun dışında 'Data extraction', 'Header', 'Rows' gibi analiz adımlarını KESİNLİKLE yazma.
    
    ```json
    {
      "yorum": "Buraya tabloya bakarak 3-4 cümlelik Türkçe day-trader yorumunu yaz (Kim tahtayı sürüklüyor? Fiyat baskı yönü ne?).",
      "veri": [
        {"Kurum": "YAPI KREDI", "Net Lot": 2096877, "Maliyet": 12.134},
        {"Kurum": "BANK OF AMERICA", "Net Lot": 5668458, "Maliyet": 12.471},
        {"Kurum": "Diğer", "Net Lot": 62956611, "Maliyet": 0}
      ]
    }

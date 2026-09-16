import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import ast
import re # YENİ: Yapay zekanın gevezeliğini filtrelemek için metin cerrahı

st.set_page_config(page_title="Kurumsal Takip (Yapay Zeka)", page_icon="🦅", layout="wide")

st.title("🦅 BİST Kurumsal Takip: Görüntü İşleme (OCR) Sürümü")
st.markdown("Matriks'in **'İlk 10'** veya **'İlk 10 Toplam'** ekran görüntüsünü yükleyin. Yapay Zeka tabloyu otomatik okusun.")

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

yuklenen_resim = st.file_uploader(
    "Matriks Ekran Görüntüsünü Yükleyin (PNG, JPG)", 
    type=['png', 'jpg', 'jpeg']
)

if yuklenen_resim:
    st.image(yuklenen_resim, caption="Yüklenen Ekran Görüntüsü", use_container_width=True)
    
    if not api_key:
        st.warning("⚠️ Lütfen tabloyu okuyabilmem için soldaki menüden Gemini API Anahtarınızı girin.")
    else:
        if st.button("🚀 Görüntüyü Analiz Et (Yapay Zeka'yı Başlat)"):
            with st.spinner("Kartal gözüyle ekran okunuyor... (10-15 saniye sürebilir)"):
                try:
                    temiz_api_key = api_key.strip()
                    genai.configure(api_key=temiz_api_key)
                    img = Image.open(yuklenen_resim)
                    
                    # SUSTURUCU TAKILMIŞ PROMPT
                    prompt = """
                    SEN BİR BİLGİSAYAR SİSTEMİSİN.
                    Ekran görüntüsündeki aracı kurum dağılımı (AKD) tablosunu oku.
                    
                    ÇOK ÖNEMLİ KURALLAR:
                    1. Kendi kendine düşünme, "Data extraction" veya "Refining" gibi analiz adımlarını KESİNLİKLE YAZMA.
                    2. SADECE aşağıdaki gibi bir JSON dizisi ile cevap ver. Başka tek bir kelime dahi etme.
                    3. Rakamlarda binlik ayracı KULLANMA (5.668.458 yerine 5668458 yaz).
                    
                    Örnek Çıktı:
                    [
                      {"Kurum": "YAPI KREDI", "Net Lot": 2096877, "Maliyet": 12.134},
                      {"Kurum": "BANK OF AMERICA", "Net Lot": 5668458, "Maliyet": 12.471},
                      {"Kurum": "IS", "Net Lot": -6663155, "Maliyet": 12.162}
                    ]
                    """
                    
                    mevcut_modeller = []
                    for m in genai.list_models():
                        if 'generateContent' in m.supported_generation_methods:
                            mevcut_modeller.append(m.name)
                            
                    if not mevcut_modeller:
                        st.error("❌ Google bu API anahtarına hiçbir model için yetki vermemiş.")
                        st.stop()
                        
                    st.info(f"🔍 Google API ile bağlantı kuruldu. Erişilebilen Modeller: {', '.join([m.replace('models/', '') for m in mevcut_modeller[:3]])}...")
                    
                    calisan_model = None
                    response = None
                    
                    for m_isim in mevcut_modeller:
                        try:
                            kisa_isim = m_isim.replace("models/", "")
                            model = genai.GenerativeModel(kisa_isim)
                            response = model.generate_content([prompt, img])
                            calisan_model = kisa_isim
                            break 
                        except Exception:
                            continue
                            
                    if not response:
                        raise Exception("Bulunan yetkili modellerin hiçbiri bu görseli okumayı başaramadı.")
                    
                    raw_text = response.text
                    json_metni = ""
                    
                    # CIMBIZLA VERİ ÇIKARMA (REGEX VE MARKDOWN ANALİZİ)
                    if "```json" in raw_text:
                        json_metni = raw_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in raw_text:
                        json_metni = raw_text.split("

import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json

st.set_page_config(page_title="Kurumsal Takip (Yapay Zeka)", page_icon="🦅", layout="wide")

st.title("🦅 BİST Kurumsal Takip: Görüntü İşleme (OCR) Sürümü")
st.markdown("Matriks'in **'İlk 10'** veya **'İlk 10 Toplam'** ekran görüntüsünü yükleyin. Yapay Zeka tabloyu otomatik okusun.")

# Güvenlik için API Key Giriş Alanı (Sol Menü)
with st.sidebar:
    st.header("⚙️ Ayarlar")
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
                    # Gemini Modelini Bağla
                    genai.configure(api_key=api_key)
                    img = Image.open(yuklenen_resim)
                    
                    # Yapay Zekaya Talimat (Prompt)
                    prompt = """
                    Sen uzman bir Borsa İstanbul veri analistisin.
                    Bu ekran görüntüsündeki aracı kurum dağılımı (AKD) tablosunu incele.
                    Tablodaki kurum isimlerini, 'Net Adet' (veya Net) miktarlarını ve 'Maliyet' verilerini çıkar.
                    Bana SADECE geçerli bir JSON formatında şu yapıda veri döndür:
                    [
                      {"Kurum": "BANK OF AMERICA", "Net Lot": 1500000, "Maliyet": 12.50},
                      {"Kurum": "İŞ YATIRIM", "Net Lot": -500000, "Maliyet": 12.45}
                    ]
                    Başka hiçbir açıklama metni ekleme. Sayılarda binlik ayracı kullanma, ondalıklar için nokta kullan.
                    Eksi (-) işaretlerine ve milyonluk rakamlara çok dikkat et.
                    """
                    
                    # OTOMATİK MODEL SEÇİCİ (404 Hatasını Ezip Geçer)
                    model_isimleri = [
                        'gemini-1.5-flash', 
                        'gemini-1.5-pro', 
                        'gemini-pro-vision', 
                        'gemini-1.0-pro-vision-latest'
                    ]
                    
                    response = None
                    calisan_model = ""
                    
                    for m in model_isimleri:
                        try:
                            model = genai.GenerativeModel(m)
                            response = model.generate_content([prompt, img])
                            calisan_model = m
                            break # Eğer model çalışırsa döngüyü hemen kır ve devam et
                        except Exception:
                            continue # Çalışmazsa sessizce diğer modele geç
                            
                    if not response:
                        raise Exception("Google API anahtarınız bu modellerin hiçbirine erişim sağlayamadı.")
                    
                    # Gelen metni temizle ve JSON'a çevir
                    raw_text = response.text.strip()
                    if raw_text.startswith("```json"):
                        raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                    elif raw_text.startswith("```"):
                        raw_text = raw_text.replace("

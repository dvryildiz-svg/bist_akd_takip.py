import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json

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
                    
                    # LAZER KESİCİ: Sadece JSON başlangıç ve bitiş parantezlerinin arasını al
                    baslangic = raw_text.find('[')
                    bitis = raw_text.rfind(']')
                    
                    if baslangic != -1 and bitis != -1:
                        json_metni = raw_text[baslangic:bitis+1]
                        veri_listesi = json.loads(json_metni)
                    else:
                        raise Exception(f"Yapay zeka veriyi okudu ama beklenen formata çeviremedi. Gelen yanıt: {raw_text}")
                        
                    df_clean = pd.DataFrame(veri_listesi)
                    
                    if df_clean.empty:
                        raise Exception("Tablo okundu ancak geçerli veri bulunamadı.")
                    
                    df_clean["Net Lot"] = pd.to_numeric(df_clean["Net Lot"], errors='coerce').fillna(0)
                    df_clean["Maliyet"] = pd.to_numeric(df_clean["Maliyet"], errors='coerce').fillna(0)
                    
                    df_clean = df_clean[df_clean["Net Lot"] != 0].sort_values(by="Net Lot", ascending=False)
                    
                    st.markdown("---")
                    st.subheader(f"🎯 Net Kurumsal Analiz (Okuyan Model: {calisan_model})")
                    
                    c1, c2 = st.columns([2, 1.5])
                    
                    with c1:
                        st.dataframe(df_clean, use_container_width=True, hide_index=True)
                        
                    with c2:
                        df_kritik = df_clean[df_clean["Kurum"].apply(kurum_tespit)].copy()
                        toplam_baski = df_kritik["Net Lot"].sum() if not df_kritik.empty else 0
                        
                        st.markdown("### 🦅 Kritik Kurum Baskısı")
                        if toplam_baski > 0:
                            st.success(f"**🟢 GÜÇLÜ ALIM**\nNet +{toplam_baski:,.0f} Lot")
                        elif toplam_baski < 0:
                            st.error(f"**🔴 CİDDİ SATIŞ**\nNet {toplam_baski:,.0f} Lot")
                        else:
                            st.info("**🟡 NÖTR BEKLEYİŞ VEYA İŞLEM YOK**")
                            
                        if not df_kritik.empty:
                            st.dataframe(df_kritik.style.format({"Net Lot": "{:,.0f}", "Maliyet": "{:,.3f}"}), use_container_width=True, hide_index=True)
                            
                except Exception as e:
                    st.error(f"❌ Bir hata oluştu: {e}")

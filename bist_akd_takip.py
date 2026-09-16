import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import ast

st.set_page_config(page_title="Kurumsal Takip (Tek Ekran)", page_icon="🦅", layout="centered")

st.title("🦅 BİST Kurumsal Takip: Hızlı Day-Trade Terminali")
st.markdown("Matriks AKD ekran görüntüsünü yükleyin veya panodan yapıştırın, anında trader analizi alın.")

with st.sidebar:
    st.header("⚙️ Ayarlar")
    
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ API Anahtarı sistem kasasından otomatik yüklendi!")
    else:
        api_key = st.text_input("Gemini API Anahtarı:", type="password")
        st.markdown("[Ücretsiz API Anahtarınızı Buradan Alabilirsiniz](https://aistudio.google.com/app/apikey)")
        
    st.markdown("---")
    st.info("💡 **İpucu:** Ekran alıntısı (Win+Shift+S) aldıktan sonra dosyayı kaydetmeden doğrudan buraya sürükleyip bırakabilirsiniz.")

KRITIK_KURUMLAR = ["BANK OF AMERICA", "BOFA", "TERA", "CITIBANK", "CİTİBANK", "DEUTSCHE"]

def kurum_tespit(kurum_adi):
    return any(k in str(kurum_adi).upper() for k in KRITIK_KURUMLAR)

def analiz_motoru(resim_dosyasi, api_key):
    genai.configure(api_key=api_key.strip())
    img = Image.open(resim_dosyasi)
    
    # Hız odaklı Flash model öncelikli arama
    mevcut_modeller = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    if not mevcut_modeller:
        raise Exception("Yetkili model bulunamadı.")
        
    # Önceliği hız için flash modellere verelim
    mevcut_modeller.sort(key=lambda x: 0 if 'flash' in x.lower() else 1)
    
    prompt = """
    SEN UZMAN BİR DAY-TRADER VE BİLGİSAYAR SİSTEMİSİN.
    Ekran görüntüsündeki aracı kurum dağılımı (AKD) tablosunu oku.
    
    Bana SADECE VE SADECE aşağıdaki formatta bir JSON döndür. Başka hiçbir açıklama yazma.
    
    {
      "yorum": "Buraya tabloya bakarak 3-4 cümlelik Türkçe day-trader yorumunu yaz (Kim tahtayı sürüklüyor? Fiyat baskı yönü ne?).",
      "veri": [
        {"Kurum": "YAPI KREDI", "Net Lot": 2096877, "Maliyet": 12.134},
        {"Kurum": "BANK OF AMERICA", "Net Lot": 5668458, "Maliyet": 12.471},
        {"Kurum": "Diğer", "Net Lot": 62956611, "Maliyet": 0}
      ]
    }
    
    KURALLAR: Rakamlarda binlik ayracı kullanma, ondalık için nokta kullan, 'Diğer' maliyeti 0 olsun.
    """
    
    calisan_model = None
    response = None
    
    for m_isim in mevcut_modeller:
        kisa_isim = m_isim.replace("models/", "")
        try:
            model = genai.GenerativeModel(kisa_isim)
            response = model.generate_content([prompt, img])
            calisan_model = kisa_isim
            break 
        except Exception:
            continue
            
    if not response:
        raise Exception("Yetkili modeller bu görseli okuyamadı.")
    
    raw_text = response.text
    
    start_idx = raw_text.find('{')
    end_idx = raw_text.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        json_metni = raw_text[start_idx:end_idx+1]
    else:
        raise Exception(f"JSON bulunamadı. Yanıt:\n{raw_text}")
        
    json_metni = json_metni.replace("0,000", "0").replace("0.000", "0").replace("0000", "0")
    
    try:
        data = json.loads(json_metni)
    except Exception:
        try:
            data = ast.literal_eval(json_metni)
        except Exception as e:
            raise Exception(f"JSON Çeviri Hatası: {e}\n\nVèri:\n{json_metni}")
            
    yorum = data.get("yorum", "Yorum üretilemedi.")
    veri_listesi = data.get("veri", [])
        
    df = pd.DataFrame(veri_listesi)
    if df.empty:
        raise Exception("Tablo boş.")
        
    df["Net Lot"] = pd.to_numeric(df["Net Lot"], errors='coerce').fillna(0)
    df["Maliyet"] = pd.to_numeric(df["Maliyet"], errors='coerce').fillna(0)
    df = df[df["Net Lot"] != 0].sort_values(by="Net Lot", ascending=False)
    
    return yorum, df, calisan_model

# TEK EKRAN & DOSYA / YAPIŞTIRMA ALANI
yuklenen_dosya = st.file_uploader("Matriks Ekran Görüntüsünü Yükleyin veya Sürükleyip Bırakın", type=['png', 'jpg', 'jpeg'])

if yuklenen_dosya:
    st.image(yuklenen_dosya, use_container_width=True)
    
    if not api_key:
        st.warning("⚠️ Lütfen API Anahtarınızı girin.")
    else:
        if st.button("🚀 Hızlı Analizi Başlat", use_container_width=True):
            with st.spinner("Kartal gözüyle inceleniyor..."):
                try:
                    yorum, df, model_adi = analiz_motoru(yuklenen_dosya, api_key)
                    
                    st.info(f"💡 **Trader Yorumu:**\n\n{yorum}")
                    st.caption(f"Hızlı Okuyan Model: {model_adi}")
                    
                    st.dataframe(df.style.format({"Net Lot": "{:,.0f}", "Maliyet": "{:,.3f}"}), use_container_width=True, hide_index=True)
                    
                    df_kritik = df[df["Kurum"].apply(kurum_tespit)].copy()
                    baski = df_kritik["Net Lot"].sum() if not df_kritik.empty else 0
                    if baski > 0:
                        st.success(f"🟢 **Kritik Kurumlar:** Net +{baski:,.0f} Lot Alımda")
                    elif baski < 0:
                        st.error(f"🔴 **Kritik Kurumlar:** Net {baski:,.0f} Lot Satışta")
                except Exception as e:
                    st.error(f"❌ Analiz Hatası: {e}")

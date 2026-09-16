import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import ast
from datetime import datetime
import requests

st.set_page_config(page_title="Kurumsal Takip (Google Sheets Bulut Arşivli)", page_icon="🦅", layout="centered")

st.title("🦅 BİST Kurumsal Takip: Bulut Arşivli Karar Terminali")
st.markdown("Matriks AKD ekran görüntüsünü yükleyin; sistem hisseyi tanısın, sinyal üretsin ve **Google E-Tablolar** arşivine kaydetsin.")

with st.sidebar:
    st.header("⚙️ Ayarlar")
    
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ Gemini API kasadan yüklendi!")
    else:
        api_key = st.text_input("Gemini API Anahtarı:", type="password")
        st.markdown("[Ücretsiz API Anahtarınızı Buradan Alabilirsiniz](https://aistudio.google.com/app/apikey)")
        
    st.markdown("---")
    st.info("💡 Her analiz doğrudan buluttaki Google Sheets arşivine tarih ve hisse bazlı işlenir.")

KRITIK_KURUMLAR = ["BANK OF AMERICA", "BOFA", "TERA", "CITIBANK", "CİTİBANK", "DEUTSCHE"]
GOOGLE_SHEET_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwPdejL3zlyh9xIHd3lgyFR5rSc3BzCT5PMK1hW7fZQULmIdhDii2RpYEEXd3mhIsNJbw/exec"

def kurum_tespit(kurum_adi):
    return any(k in str(kurum_adi).upper() for k in KRITIK_KURUMLAR)

def google_sheets_e_isle(tarih_saat, hisse, sinyal, gerekce, df_veri, kritik_baski):
    try:
        # Kurum isimlerini temizleyelim ve Diğer / Diger varyasyonlarını tamamen eleyelim
        df_temiz = df_veri.copy()
        df_temiz["Kurum_Temiz"] = df_temiz["Kurum"].astype(str).str.upper().str.strip()
        
        yasakli_kelimeler = ["DİĞER", "DIGER", "DIĞER", "DİGER"]
        df_kurumlar = df_temiz[~df_temiz["Kurum_Temiz"].isin(yasakli_kelimeler)]
        
        if not df_kurumlar.empty:
            en_ust_alici = df_kurumlar.iloc[0]["Kurum"]
            en_ust_alici_lot = df_kurumlar.iloc[0]["Net Lot"]
        else:
            en_ust_alici = "YOK"
            en_ust_alici_lot = 0
        
        payload = {
            "tarih": str(tarih_saat),
            "hisse": str(hisse),
            "sinyal": str(sinyal),
            "kurum": str(en_ust_alici),
            "lot": float(en_ust_alici_lot),
            "baski": float(kritik_baski),
            "gerekce": str(gerekce)
        }
        
        response = requests.post(GOOGLE_SHEET_WEB_APP_URL, json=payload)
        if response.status_code == 200:
            return True
        else:
            st.error(f"Bulut kayıt yanıt kodu: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"Bulut Arşiv Kayıt Hatası: {e}")
        return False

def karar_destek_analizi(resim_dosyasi, api_key):
    genai.configure(api_key=api_key.strip())
    img = Image.open(resim_dosyasi)
    
    model = genai.GenerativeModel('gemini-3.6-flash')
    
    prompt = """
    SEN UZMAN BİR DAY-TRADER VE RİSK YÖNETİCİSİSİN.
    Ekran görüntüsündeki aracı kurum dağılımı (AKD) tablosunu ve başlık kısımlarını incele.
    
    Bana SADECE VE SADECE aşağıdaki formatta bir JSON döndür. Başka hiçbir açıklama yazma.
    
    {
      "hisse_adi": "ENERYA",
      "sinyal": "AL", 
      "gerekce": "Buraya 3-4 cümlelik Türkçe trader yorumunu yaz: Hangi kurum alıyor/satıyor, maliyetlerin fiyata etkisi nedir ve neden bu sinyal üretildi?",
      "veri": [
        {"Kurum": "YAPI KREDI", "Net Lot": 2096877, "Maliyet": 12.134},
        {"Kurum": "BANK OF AMERICA", "Net Lot": 5668458, "Maliyet": 12.471},
        {"Kurum": "Diğer", "Net Lot": 62956611, "Maliyet": 0}
      ]
    }
    
    NOT 1: "hisse_adi" alanına görselde yazan hisse kodunu (Örn: THYAO, ENERYA, EREGL vb.) büyük harfle yaz. Bulamazsan "BİLİNMEYEN" yaz.
    NOT 2: "sinyal" alanı KESİNLİKLE sadece "AL", "SAT" veya "TUT" kelimelerinden biri olmalıdır.
    KURALLAR: Rakamlarda binlik ayracı kullanma, ondalık için nokta kullan, 'Diğer' maliyeti 0 olsun.
    """
    
    response = model.generate_content([prompt, img])
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
            raise Exception(f"Çeviri Hatası: {e}\n\nVeri:\n{json_metni}")
            
    hisse_adi = data.get("hisse_adi", "HİSSE").upper()
    sinyal = data.get("sinyal", "TUT").upper()
    gerekce = data.get("gerekce", "Yorum üretilemedi.")
    veri_listesi = data.get("veri", [])
        
    df = pd.DataFrame(veri_listesi)
    if df.empty:
        raise Exception("Tablo boş.")
        
    df["Net Lot"] = pd.to_numeric(df["Net Lot"], errors='coerce').fillna(0)
    df["Maliyet"] = pd.to_numeric(df["Maliyet"], errors='coerce').fillna(0)
    df = df[df["Net Lot"] != 0].sort_values(by="Net Lot", ascending=False)
    
    return hisse_adi, sinyal, gerekce, df

# ARAYÜZ
yuklenen_dosya = st.file_uploader("Matriks Ekran Görüntüsünü Yükleyin", type=['png', 'jpg', 'jpeg'])

if yuklenen_dosya:
    st.image(yuklenen_dosya, use_container_width=True)
    
    if not api_key:
        st.warning("⚠️ Lütfen API Anahtarınızı girin.")
    else:
        if st.button("🚀 Analizi Başlat ve Buluta Kaydet", use_container_width=True):
            with st.spinner("Piyasa röntgeni çekiliyor ve Google Sheets'e işleniyor..."):
                try:
                    hisse_adi, sinyal, gerekce, df = karar_destek_analizi(yuklenen_dosya, api_key)
                    # Saat formatı düzeltildi (%Y-%m-%d %H:%M:%S)
                    simdiki_zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Kritik kurumlar toplamı
                    df_kritik = df[df["Kurum"].apply(kurum_tespit)].copy()
                    baski = df_kritik["Net Lot"].sum() if not df_kritik.empty else 0
                    
                    # Google Sheets tablosuna kaydet
                    basarili = google_sheets_e_isle(simdiki_zaman, hisse_adi, sinyal, gerekce, df, baski)
                    
                    # GÖRSEL ÇIKTILAR
                    st.markdown(f"### 🎯 Hisse: **{hisse_adi}** | ⏱️ {simdiki_zaman}")
                    
                    if sinyal == "AL":
                        st.success(f"🟢 **SİNYAL: GÜÇLÜ AL**\n\n**Gerekçe:** {gerekce}")
                    elif sinyal == "SAT":
                        st.error(f"🔴 **SİNYAL: GÜÇLÜ SAT**\n\n**Gerekçe:** {gerekce}")
                    else:
                        st.warning(f"🟡 **SİNYAL: TUT / BEKLE**\n\n**Gerekçe:** {gerekce}")
                    
                    st.dataframe(df.style.format({"Net Lot": "{:,.0f}", "Maliyet": "{:,.3f}"}), use_container_width=True, hide_index=True)
                    
                    if baski > 0:
                        st.info(f"📊 **Kritik Kurumlar Toplamı:** Net +{baski:,.0f} Lot")
                    else:
                        st.info(f"📊 **Kritik Kurumlar Toplamı:** Net {baski:,.0f} Lot")
                        
                    if basarili:
                        st.success("☁️ Bu analiz Google Sheets arşivine kalıcı olarak işlendi!")
                    
                except Exception as e:
                    st.error(f"❌ Analiz Hatası: {e}")

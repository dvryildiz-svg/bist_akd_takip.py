import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import ast

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
    
    prompt = """
    SEN UZMAN BİR DAY-TRADER VE BİLGİSAYAR SİSTEMİSİN.
    Ekran görüntüsündeki aracı kurum dağılımı (AKD) tablosunu oku.
    
    Bana SADECE VE SADECE aşağıdaki formatta bir JSON döndür.
    Bunun dışında 'Data extraction', 'Header', 'Rows' gibi analiz adımlarını KESİNLİKLE yazma.
    
    {
      "yorum": "Buraya tabloya bakarak 3-4 cümlelik Türkçe day-trader yorumunu yaz (Kim tahtayı sürüklüyor? Fiyat baskı yönü ne?).",
      "veri": [
        {"Kurum": "YAPI KREDI", "Net Lot": 2096877, "Maliyet": 12.134},
        {"Kurum": "BANK OF AMERICA", "Net Lot": 5668458, "Maliyet": 12.471},
        {"Kurum": "Diğer", "Net Lot": 62956611, "Maliyet": 0}
      ]
    }
    
    ÖNEMLİ KURALLAR:
    1. Rakamlarda binlik ayracı (nokta) KESİNLİKLE KULLANMA (Örn: 2096877 yaz).
    2. Ondalık kısımlar için VİRGÜL YERİNE NOKTA kullan (Örn: 12.134 yaz).
    3. 'Diğer' satırında maliyet '0,000' ise SADECE 0 yaz. Sayıların başına sıfır ekleme.
    """
    
    mevcut_modeller = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    if not mevcut_modeller:
        raise Exception("Yetkili model bulunamadı.")
        
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
    
    # EN GÜÇLÜ JSON CIMBIZI: Markdown dinlemez, doğrudan { ve } arasını alır.
    start_idx = raw_text.find('{')
    end_idx = raw_text.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        json_metni = raw_text[start_idx:end_idx+1]
    else:
        raise Exception(f"JSON süslü parantezleri bulunamadı. Yapay Zeka Yanıtı:\n{raw_text}")
        
    # Sıfır hatası zırhı
    json_metni = json_metni.replace("0,000", "0").replace("0.000", "0").replace("0000", "0")
    
    try:
        data = json.loads(json_metni)
    except Exception:
        try:
            data = ast.literal_eval(json_metni)
        except Exception as e:
            raise Exception(f"JSON Çeviri Hatası: {e}\n\nHatalı Veri:\n{json_metni}")
            
    yorum = data.get("yorum", "Yapay zeka yorum üretemedi, ancak veriler çekildi.")
    veri_listesi = data.get("veri", [])
        
    df = pd.DataFrame(veri_listesi)
    if df.empty:
        raise Exception("Tablo boş.")
        
    df["Net Lot"] = pd.to_numeric(df["Net Lot"], errors='coerce').fillna(0)
    df["Maliyet"] = pd.to_numeric(df["Maliyet"], errors='coerce').fillna(0)
    df = df[df["Net Lot"] != 0].sort_values(by="Net Lot", ascending=False)
    
    return yorum, df, calisan_model

# ÇİFT EKRAN ARAYÜZÜ
c_sol, c_sag = st.columns(2)

with c_sol:
    st.subheader("🖥️ 1. Ekran (Örn: Sabah veya Hisse A)")
    resim_1 = st.file_uploader("1. Matriks Tablosu", type=['png', 'jpg', 'jpeg'], key="r1")
    if resim_1:
        st.image(resim_1, use_container_width=True)

with c_sag:
    st.subheader("🖥️ 2. Ekran (Örn: Öğleden Sonra veya Hisse B)")
    resim_2 = st.file_uploader("2. Matriks Tablosu", type=['png', 'jpg', 'jpeg'], key="r2")
    if resim_2:
        st.image(resim_2, use_container_width=True)

if resim_1 or resim_2:
    if not api_key:
        st.warning("⚠️ Lütfen API Anahtarınızı girin.")
    else:
        if st.button("🚀 Yüklenen Ekranları Analiz Et (Yapay Zeka'yı Başlat)", use_container_width=True):
            
            res_sol, res_sag = st.columns(2)
            
            if resim_1:
                with res_sol:
                    with st.spinner("1. Ekran analiz ediliyor..."):
                        try:
                            yorum1, df1, model1 = analiz_motoru(resim_1, api_key)
                            st.info(f"💡 **Trader Yorumu:**\n\n{yorum1}")
                            st.caption(f"Okuyan Model: {model1}")
                            
                            st.dataframe(df1.style.format({"Net Lot": "{:,.0f}", "Maliyet": "{:,.3f}"}), use_container_width=True, hide_index=True)
                            
                            df1_kritik = df1[df1["Kurum"].apply(kurum_tespit)].copy()
                            baski1 = df1_kritik["Net Lot"].sum() if not df1_kritik.empty else 0
                            if baski1 > 0:
                                st.success(f"🟢 **Kritik Kurumlar:** Net +{baski1:,.0f} Lot Alımda")
                            elif baski1 < 0:
                                st.error(f"🔴 **Kritik Kurumlar:** Net {baski1:,.0f} Lot Satışta")
                        except Exception as e:
                            st.error(f"❌ 1. Ekran Hatası: {e}")
                            
            if resim_2:
                with res_sag:
                    with st.spinner("2. Ekran analiz ediliyor..."):
                        try:
                            yorum2, df2, model2 = analiz_motoru(resim_2, api_key)
                            st.info(f"💡 **Trader Yorumu:**\n\n{yorum2}")
                            st.caption(f"Okuyan Model: {model2}")
                            
                            st.dataframe(df2.style.format({"Net Lot": "{:,.0f}", "Maliyet": "{:,.3f}"}), use_container_width=True, hide_index=True)
                            
                            df2_kritik = df2[df2["Kurum"].apply(kurum_tespit)].copy()
                            baski2 = df2_kritik["Net Lot"].sum() if not df2_kritik.empty else 0
                            if baski2 > 0:
                                st.success(f"🟢 **Kritik Kurumlar:** Net +{baski2:,.0f} Lot Alımda")
                            elif baski2 < 0:
                                st.error(f"🔴 **Kritik Kurumlar:** Net {baski2:,.0f} Lot Satışta")
                        except Exception as e:
                            st.error(f"❌ 2. Ekran Hatası: {e}")

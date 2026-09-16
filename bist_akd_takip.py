import pandas as pd
import streamlit as st

st.set_page_config(page_title="Kurumsal Takip Terminali", page_icon="🦅", layout="wide")

st.title("🦅 BİST Kurumsal Takip: SASA & ENERYA Odak Paneli")
st.markdown("Matriks AKD verilerini yükleyerek **BofA, Tera ve Yabancı** kurumların tahta baskısını analiz edin.")

# Hedef Hisseler ve Kurumlar
HEDEF_HISSELER = ["SASA", "ENERYA"]
KRITIK_KURUMLAR = ["BANK OF AMERICA", "BOFA", "TERA", "CITIBANK", "CİTİBANK", "DEUTSCHE"]

def kurum_tespit(kurum_adi):
    """Gelen kurum adının kritik kurumlardan biri olup olmadığını kontrol eder."""
    kurum_adi = str(kurum_adi).upper()
    for k in KRITIK_KURUMLAR:
        if k in kurum_adi:
            return True
    return False

# Matriks'ten alınan veriyi yükleme alanı
yuklenen_dosya = st.file_uploader("Matriks AKD Excel veya CSV Dosyanızı Yükleyin", type=['csv', 'xlsx'])

if yuklenen_dosya is not None:
    try:
        # Dosya tipine göre Pandas ile oku
        if yuklenen_dosya.name.endswith('csv'):
            df = pd.read_csv(yuklenen_dosya, sep=None, engine='python')
        else:
            df = pd.read_excel(yuklenen_dosya)
            
        st.success("Veri başarıyla yüklendi ve analiz ediliyor...")
        
        # Sütun isimlerini standartlaştırma (Matriks formatına uyum için varsayımlar)
        # Gerçek Matriks dosyanın sütun isimlerine göre buraları güncelleyebiliriz
        df.columns = df.columns.str.strip().str.upper()
        
        # Olası sütun isimlerini eşleştirme (Hisse, Kurum, Net Lot)
        hisse_sutunu = [col for col in df.columns if "HISSE" in col or "SEMBOL" in col or "KOD" in col][0]
        kurum_sutunu = [col for col in df.columns if "KURUM" in col or "ARACI" in col][0]
        net_lot_sutunu = [col for col in df.columns if "NET" in col and "LOT" in col][0]
        
        # Sadece SASA ve ENERYA'yı filtrele
        df_hedef = df[df[hisse_sutunu].astype(str).str.upper().isin(HEDEF_HISSELER)]
        
        if df_hedef.empty:
            st.warning("Yüklenen dosyada SASA veya ENERYA verisi bulunamadı.")
        else:
            for hisse in HEDEF_HISSELER:
                df_hisse = df_hedef[df_hedef[hisse_sutunu].astype(str).str.upper() == hisse]
                if not df_hisse.empty:
                    st.markdown(f"---")
                    st.subheader(f"🎯 {hisse} - Kurumsal Baskı Analizi")
                    
                    # Sadece BofA, Tera ve Yabancıları filtrele
                    df_kritik = df_hisse[df_hisse[kurum_sutunu].apply(kurum_tespit)]
                    
                    toplam_net_lot = 0
                    if not df_kritik.empty:
                        toplam_net_lot = df_kritik[net_lot_sutunu].sum()
                        
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.dataframe(df_kritik[[kurum_sutunu, net_lot_sutunu]], use_container_width=True)
                        
                        with col2:
                            # Akıllı Sinyal Mantığı
                            if toplam_net_lot > 0:
                                st.success(f"### 🟢 GÜÇLÜ ALIM\n**Net {toplam_net_lot:,.0f} Lot Girişi**")
                                st.markdown("BofA, Tera ve Yabancılar şu an tahtada **mal topluyor**. Teknik göstergeler (RSI) de destekliyorsa alım yönlü fırsat olabilir.")
                            elif toplam_net_lot < 0:
                                st.error(f"### 🔴 CİDDİ SATIŞ\n**Net {toplam_net_lot:,.0f} Lot Çıkışı**")
                                st.markdown("Kritik kurumlar tahtada **satış baskısı** kuruyor. Kar realizasyonu veya dağıtım süreci olabilir, dikkatli olunmalı.")
                            else:
                                st.info("### 🟡 NÖTR")
                                st.markdown("Kritik kurumların net bir yön tayini yok.")
                    else:
                        st.info(f"{hisse} tahtasında şu an BofA, Tera veya Yabancı (Citi/Deutsche) işlemi tespit edilmedi.")

    except Exception as e:
        st.error(f"Dosya okunurken bir hata oluştu. Matriks sütun formatınız farklı olabilir. Hata Detayı: {e}")

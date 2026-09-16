import pandas as pd
import streamlit as st

st.set_page_config(page_title="Kurumsal Takip Terminali", page_icon="🦅", layout="wide")

st.title("🦅 BİST Kurumsal Takip: Çoklu Hisse Paneli")
st.markdown("Matriks'ten aldığınız **birden fazla** AKD Excel dosyasını (SASA, ENERYA vb.) aynı anda yükleyin.")

KRITIK_KURUMLAR = ["BANK OF AMERICA", "BOFA", "TERA", "CITIBANK", "CİTİBANK", "DEUTSCHE"]

def kurum_tespit(kurum_adi):
    """Gelen kurum adının kritik kurumlardan biri olup olmadığını kontrol eder."""
    kurum_adi = str(kurum_adi).upper()
    return any(k in kurum_adi for k in KRITIK_KURUMLAR)

# DİKKAT: accept_multiple_files=True ile artık birden fazla dosya seçilebilir!
yuklenen_dosyalar = st.file_uploader(
    "Matriks Excel Dosyalarınızı Topluca Sürükleyip Bırakın", 
    type=['csv', 'xlsx', 'xls'], 
    accept_multiple_files=True
)

if yuklenen_dosyalar:
    for dosya in yuklenen_dosyalar:
        # Hisse adını dosya isminden otomatik yakala (Örn: "SASA_AKD.xlsx" -> "SASA")
        hisse_adi = dosya.name.split('.')[0].upper().replace("_AKD", "").replace("AKD", "")
        
        try:
            if dosya.name.endswith('csv'):
                df = pd.read_csv(dosya, sep=None, engine='python')
            else:
                df = pd.read_excel(dosya)
                
            # Sütun başlıklarındaki boşlukları temizle ve büyüt
            df.columns = df.columns.str.strip().str.upper()
            
            # Matriks'in olası sütun isimlerini esnek arama
            kurum_sutunu = [col for col in df.columns if "KURUM" in col or "ARACI" in col or "ALICI" in col or "SATICI" in col]
            net_lot_sutunu = [col for col in df.columns if "NET" in col and ("LOT" in col or "MİKTAR" in col or "MIKTAR" in col or "HACIM" in col)]
            
            if not kurum_sutunu or not net_lot_sutunu:
                st.warning(f"⚠️ {dosya.name} dosyasında 'Kurum' veya 'Net Miktar' sütunları standart formatta bulunamadı.")
                continue # Diğer dosyaya geç
                
            kurum_col = kurum_sutunu[0]
            lot_col = net_lot_sutunu[0]
            
            # Sadece BofA, Tera ve Yabancıları filtrele
            df_kritik = df[df[kurum_col].apply(kurum_tespit)]
            
            st.markdown("---")
            st.subheader(f"🎯 {hisse_adi} - Kurumsal Baskı Analizi")
            
            if not df_kritik.empty:
                # Lot sütunundaki olası virgül/nokta string hatalarını sayıya (float) çevirme
                df_kritik.loc[:, lot_col] = pd.to_numeric(df_kritik[lot_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                toplam_net_lot = df_kritik[lot_col].sum()
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    # Tabloyu ekranda göster
                    st.dataframe(df_kritik[[kurum_col, lot_col]], use_container_width=True)
                
                with col2:
                    # Akıllı Sinyal Mantığı
                    if toplam_net_lot > 0:
                        st.success(f"### 🟢 GÜÇLÜ ALIM\n**Net {toplam_net_lot:,.0f} Lot Girişi**")
                        st.markdown("BofA/Tera/Yabancılar tahtada **mal topluyor**.")
                    elif toplam_net_lot < 0:
                        st.error(f"### 🔴 CİDDİ SATIŞ\n**Net {toplam_net_lot:,.0f} Lot Çıkışı**")
                        st.markdown("Kritik kurumlar tahtada **satış baskısı** kuruyor.")
                    else:
                        st.info("### 🟡 NÖTR\nNet yön tayini yok.")
            else:
                st.info(f"{hisse_adi} tahtasında şu an BofA, Tera veya Yabancı (Citi/Deutsche) işlemi bulunmuyor.")

        except Exception as e:
            st.error(f"❌ {dosya.name} okunurken bir hata oluştu: {e}")
            

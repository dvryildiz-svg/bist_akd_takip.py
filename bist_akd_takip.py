import pandas as pd
import streamlit as st

st.set_page_config(page_title="Kurumsal Takip Terminali", page_icon="🦅", layout="wide")

st.title("🦅 BİST Kurumsal Takip: Profesyonel Sürüm")
st.markdown("Matriks'teki **'İlk 10 Toplam'** sekmesinden kopyalanan net verilerle çalışır.")

KRITIK_KURUMLAR = ["BANK OF AMERICA", "BOFA", "TERA", "CITIBANK", "CİTİBANK", "DEUTSCHE"]

def kurum_tespit(kurum_adi):
    return any(k in str(kurum_adi).upper() for k in KRITIK_KURUMLAR)

def temizle_ve_cevir(deger):
    """Matriks'in noktalı/virgüllü rakam formatını Python sayısına çevirir."""
    try:
        deger = str(deger).replace('.', '').replace(',', '.')
        return float(deger)
    except:
        return 0.0

yuklenen_dosyalar = st.file_uploader(
    "Matriks 'İlk 10 Toplam' Excel Dosyanızı Yükleyin", 
    type=['csv', 'xlsx', 'xls'], 
    accept_multiple_files=True
)

if yuklenen_dosyalar:
    for dosya in yuklenen_dosyalar:
        hisse_adi = dosya.name.split('.')[0].upper().replace(" (2)", "").replace(" (1)", "")
        
        try:
            # Başlıkları dikkate almadan ham veriyi okuyoruz (hata riskini sıfırlar)
            df = pd.read_excel(dosya, header=None) if not dosya.name.endswith('csv') else pd.read_csv(dosya, header=None)
            
            # Eğer dosya çok eksik kopyalanmışsa uyar
            if df.shape[1] < 4:
                st.warning("⚠️ Excel dosyasında yeterli sütun yok. Lütfen Matriks'ten tabloyu tam seçtiğine emin ol.")
                continue

            # Eğer ilk satırda "Açıklama" veya "Kurum" gibi bir başlık varsa, o satırı yoksay
            if "AÇIKLAMA" in str(df.iloc[0, 0]).upper() or "KURUM" in str(df.iloc[0, 0]).upper():
                df = df.iloc[1:].copy()
            
            # Matriks 'İlk 10 Toplam' standart dizilimi: 0(Kurum), 1(%), 2(Net), 3(Maliyet), 4(Toplam)
            df_clean = pd.DataFrame()
            df_clean["Kurum"] = df.iloc[:, 0].astype(str).str.strip()
            df_clean["Net Lot"] = df.iloc[:, 2].apply(temizle_ve_cevir)
            df_clean["Maliyet"] = df.iloc[:, 3].apply(temizle_ve_cevir)
            
            # Boş olanları ve Diğer kısmını temizle
            df_clean = df_clean[~df_clean["Kurum"].isin(["nan", "None", "", "Diğer"])]
            
            # Lotu 0 olanları gizle, en çok alandan en çok satana doğru sırala
            df_clean = df_clean[df_clean["Net Lot"] != 0].sort_values(by="Net Lot", ascending=False)
            
            st.markdown("---")
            st.subheader(f"🎯 {hisse_adi} - Net Kurumsal Analiz")
            
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
                    # Rakamları daha okunaklı formatta göster
                    st.dataframe(df_kritik.style.format({"Net Lot": "{:,.0f}", "Maliyet": "{:,.3f}"}), use_container_width=True, hide_index=True)
                    
        except Exception as e:
            st.error(f"❌ Excel verisi beklenenden farklı. Hata detayı: {e}")

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
            # Standart okuma
            df = pd.read_excel(dosya) if not dosya.name.endswith('csv') else pd.read_csv(dosya)
            df.columns = df.columns.astype(str).str.strip().str.upper()
            
            # Sütun isimlerini dinamik yakala
            kurum_col = [c for c in df.columns if "AÇIKLAMA" in c or "KURUM" in c][0]
            net_col = [c for c in df.columns if "NET" in c][0]
            maliyet_col = [c for c in df.columns if "MALIYET" in c or "MALİYET" in c][0]
            
            # Sadece ihtiyacımız olan sütunları al ve boş satırları at
            df = df[[kurum_col, net_col, maliyet_col]].dropna()
            
            # Sayıları dönüştür
            df[net_col] = df[net_col].apply(temizle_ve_cevir)
            df[maliyet_col] = df[maliyet_col].apply(temizle_ve_cevir)
            
            # Lotu 0 olanları gizle, en çok alandan en çok satana doğru sırala
            df = df[df[net_col] != 0].sort_values(by=net_col, ascending=False)
            
            st.markdown("---")
            st.subheader(f"🎯 {hisse_adi} - Net Kurumsal Analiz")
            
            c1, c2 = st.columns([2, 1.5])
            
            with c1:
                st.dataframe(df, use_container_width=True, hide_index=True)
                
            with c2:
                df_kritik = df[df[kurum_col].apply(kurum_tespit)].copy()
                toplam_baski = df_kritik[net_col].sum() if not df_kritik.empty else 0
                
                st.markdown("### 🦅 Kritik Kurum Baskısı")
                if toplam_baski > 0:
                    st.success(f"**🟢 GÜÇLÜ ALIM**\nNet +{toplam_baski:,.0f} Lot")
                elif toplam_baski < 0:
                    st.error(f"**🔴 CİDDİ SATIŞ**\nNet {toplam_baski:,.0f} Lot")
                else:
                    st.info("**🟡 NÖTR BEKLEYİŞ VEYA İŞLEM YOK**")
                    
                if not df_kritik.empty:
                    # Rakamları daha okunaklı formatta göster
                    st.dataframe(df_kritik.style.format({net_col: "{:,.0f}", maliyet_col: "{:,.3f}"}), use_container_width=True, hide_index=True)
                    
        except Exception as e:
            st.error(f"❌ Dosya okunamadı. Lütfen 'İlk 10 Toplam' sekmesini kopyaladığınızdan emin olun. Hata detayı: {e}")

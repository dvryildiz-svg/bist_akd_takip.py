import pandas as pd
import streamlit as st

st.set_page_config(page_title="Kurumsal Takip Terminali", page_icon="🦅", layout="wide")

st.title("🦅 BİST Kurumsal Takip: Matriks Otomatik Çözücü")
st.markdown("Matriks Web'den kopyaladığınız **'kaymış'** veya **'alt alta inmiş'** ham Excel dosyalarını olduğu gibi yükleyin. Sistem isimleri ve verileri otomatik olarak yan yana dikecektir.")

KRITIK_KURUMLAR = ["BANK OF AMERICA", "BOFA", "TERA", "CITIBANK", "CİTİBANK", "DEUTSCHE"]

def kurum_tespit(kurum_adi):
    return any(k in str(kurum_adi).upper() for k in KRITIK_KURUMLAR)

yuklenen_dosyalar = st.file_uploader(
    "Alt Alta Kayan Matriks Dosyalarınızı Sürükleyip Bırakın", 
    type=['csv', 'xlsx', 'xls'], 
    accept_multiple_files=True
)

if yuklenen_dosyalar:
    for dosya in yuklenen_dosyalar:
        hisse_adi = dosya.name.split('.')[0].upper().replace("_AKD", "").replace("AKD", "")
        
        try:
            # Veriyi başlık olmadan ham olarak okuyoruz (Kaymış yapıyı görmek için)
            df_raw = pd.read_excel(dosya, header=None) if not dosya.name.endswith('csv') else pd.read_csv(dosya, header=None, sep=None, engine='python')
            
            # "Açıklama" (Kurum isimleri) satırlarını bul
            isim_satirlari = df_raw[df_raw.apply(lambda r: r.astype(str).str.contains("Açıklama", na=False, case=False).any(), axis=1)].index
            
            # "Net Adet" (Sayılar bloğu) satırlarını bul
            veri_satirlari = df_raw[df_raw.apply(lambda r: r.astype(str).str.contains("Net Adet", na=False, case=False).any(), axis=1)].index
            
            if len(isim_satirlari) > 0 and len(veri_satirlari) > 0:
                tum_kurumlar_listesi = []
                
                # Kopyalanan her bir tablo bloğunu kendi içinde birleştir
                for i in range(len(isim_satirlari)):
                    # Kurum isimlerini çek (Başlığın altındaki 11 satır)
                    bas_isim = isim_satirlari[i] + 1
                    bit_isim = bas_isim + 11
                    kurumlar = df_raw.iloc[bas_isim:bit_isim, 0].reset_index(drop=True)
                    
                    # Sayısal verileri çek (Net adet başlığının altındaki 11 satır)
                    bas_veri = veri_satirlari[i] + 1
                    bit_veri = bas_veri + 11
                    
                    veri_basliklari = df_raw.iloc[veri_satirlari[i]].dropna().values
                    veriler = df_raw.iloc[bas_veri:bit_veri, :len(veri_basliklari)].reset_index(drop=True)
                    veriler.columns = [str(col).strip() for col in veri_basliklari]
                    
                    # Kopuk blokları YAN YANA birleştir
                    temp_df = pd.DataFrame({"Kurum": kurumlar})
                    temp_df = pd.concat([temp_df, veriler], axis=1)
                    tum_kurumlar_listesi.append(temp_df)

                # Parçaları toparla
                final_df = pd.concat(tum_kurumlar_listesi).dropna(subset=["Kurum"])
                
                # Rakamlardaki Matriks formatını (Nokta binlik, virgül ondalık) Python'a çevir
                for col in final_df.columns:
                    if col != "Kurum":
                        final_df[col] = final_df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
                        final_df[col] = pd.to_numeric(final_df[col], errors='coerce').fillna(0)
                    
                # Aynı kurum iki kere varsa lotlarını topla, maliyetin ortalamasını al
                final_df = final_df.groupby("Kurum", as_index=False).agg({
                    "Net Adet": "sum", 
                    "Maliyet": "mean" if "Maliyet" in final_df.columns else "first"
                })
                
                final_df = final_df[final_df["Net Adet"] != 0].sort_values(by="Net Adet", ascending=False)
                
                st.markdown("---")
                st.subheader(f"🎯 {hisse_adi} - Otomatik Çözülmüş AKD")
                
                col1, col2 = st.columns([2, 1.5])
                
                with col1:
                    st.dataframe(final_df, use_container_width=True, hide_index=True)
                    
                with col2:
                    df_kritik = final_df[final_df["Kurum"].apply(kurum_tespit)].copy()
                    toplam_baski = df_kritik["Net Adet"].sum() if not df_kritik.empty else 0
                    
                    st.markdown("### 🦅 Kritik Kurum Baskısı")
                    if toplam_baski > 0:
                        st.success(f"**🟢 GÜÇLÜ ALIM**\nNet +{toplam_baski:,.0f} Lot")
                    elif toplam_baski < 0:
                        st.error(f"**🔴 CİDDİ SATIŞ**\nNet {toplam_baski:,.0f} Lot")
                    else:
                        st.info("**🟡 NÖTR BEKLEYİŞ**")
                        
                    if not df_kritik.empty:
                        st.dataframe(df_kritik[["Kurum", "Net Adet", "Maliyet"]], use_container_width=True, hide_index=True)
                        
            else:
                st.warning(f"⚠️ {dosya.name} içinde Matriks formatı bulunamadı. Lütfen veriyi doğru kopyaladığınızdan emin olun.")
        except Exception as e:
            st.error(f"❌ {dosya.name} işlenirken hata: {e}")

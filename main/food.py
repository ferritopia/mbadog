import streamlit as st
from groq import Groq
import os
from PIL import Image
import io
import base64
import pandas as pd
import logging

# Konfigurasi halaman
st.set_page_config(
    page_title="Mbadog: Cek mikronutrisi makanan",
    page_icon="🥗",
    layout="centered"
)

# Inisialisasi Groq client
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

os.environ["GROQ_API_KEY"] = GROQ_API_KEY
client = Groq()

logging.basicConfig(level=logging.DEBUG)

def analisis_gambar(image_base64):
    """Analisis makanan dalam gambar menggunakan model vision Groq"""
    try:
        # Debug log untuk memastikan fungsi dipanggil
        logging.debug("Memulai analisis gambar...")
        
        completion = client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Apa saja makanan yang ada dalam gambar ini? Berikan dalam format sederhana:\nmakanan 1: [nama makanan]"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "low"
                            }
                        }
                    ]
                }
            ],
            temperature=0.3,
            max_tokens=1024,
            top_p=1,
            stream=False,
        )
        
        # Debug log untuk response
        response = completion.choices[0].message.content
        logging.debug(f"Raw response from model: {response}")
        
        # Parsing hasil deteksi ke dalam list dengan penanganan error yang lebih baik
        makanan_list = []
        if response:
            lines = response.split('\n')
            for line in lines:
                # Debug log untuk setiap baris
                logging.debug(f"Processing line: {line}")
                
                if ':' in line:
                    # Ekstrak nama makanan setelah ':'
                    makanan = line.split(':', 1)[1].strip()
                    if makanan:
                        makanan_list.append(makanan)
                        logging.debug(f"Added food item: {makanan}")
        
        # Debug log untuk hasil akhir
        logging.debug(f"Final food list: {makanan_list}")
        
        # Jika tidak ada makanan terdeteksi, raise exception
        if not makanan_list:
            raise ValueError("Tidak ada makanan yang terdeteksi dalam gambar")
            
        return makanan_list
        
    except Exception as e:
        logging.error(f"Error dalam analisis_gambar: {str(e)}")
        raise e

def dapatkan_info_gizi(nama_makanan, gram):
    """Dapatkan informasi gizi menggunakan model teks Groq"""
    prompt = f"""Analisis nutrisi untuk {gram}g {nama_makanan}.
    Berikan hasil dalam format tabel dengan kolom berikut:
    Makanan | Gram | Kalori (kkal) | Protein (g) | Karbohidrat (g) | Lemak (g) | Nutrisi Penting
    
    Contoh format:
    nasi | 100 | 130 | 2.7 | 28.6 | 0.3 | Fosfor, Mangan, Vitamin B6
    
    Berikan hanya satu baris data tanpa header, separator, atau informasi tambahan."""

    info_gizi = ""
    stream = client.chat.completions.create(
        model="llama-3.2-90b-text-preview",
        messages=[
            {
                "role": "system",
                "content": "Anda adalah ahli gizi yang memberikan informasi dalam format tabel yang diminta. Berikan hanya data tanpa kalimat tambahan."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_tokens=1024,
        top_p=1,
        stream=True,
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content:
            info_gizi += chunk.choices[0].delta.content
    
    return info_gizi.strip()

# Aplikasi utama
st.title("🥗 Mbadog: Cek dulu makanan mu!")
st.write("Unggah foto makanan atau ambil foto untuk menganalisis kandungan mikronutriennya")

# Bagian input gambar
sumber_gambar = st.radio("Pilih sumber gambar:", ("Unggah Gambar", "Ambil Foto"))

if sumber_gambar == "Unggah Gambar":
    file_terunggah = st.file_uploader("Pilih gambar...", type=["jpg", "jpeg", "png"])
    if file_terunggah is not None:
        image = Image.open(file_terunggah)
        st.image(image, caption="Gambar yang Diunggah", use_column_width=True)
else:
    foto_kamera = st.camera_input("Ambil foto")
    if foto_kamera is not None:
        image = Image.open(foto_kamera)
        st.image(image, caption="Foto yang Diambil", use_column_width=True)

# Bagian analisis
if 'image' in locals():
    if st.button("Deteksi Makanan"):
        with st.spinner("Sedang menganalisis gambar..."):
            try:
                # Konversi gambar ke base64
                buffered = io.BytesIO()
                image.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                # Debug log untuk base64 image (partial)
                logging.debug(f"Base64 image (first 100 chars): {img_str[:100]}...")
                
                # Dapatkan hasil deteksi makanan
                makanan_terdeteksi = analisis_gambar(img_str)
                
                # Tampilkan hasil deteksi langsung
                if makanan_terdeteksi:
                    st.success("Berhasil mendeteksi makanan!")
                    st.session_state['makanan_terdeteksi'] = makanan_terdeteksi
                else:
                    st.warning("Tidak ada makanan yang terdeteksi dalam gambar")
                    
            except Exception as e:
                st.error("Terjadi kesalahan saat menganalisis gambar.")
                st.error(f"Detail error: {str(e)}")
                logging.error(f"Full error details: {str(e)}", exc_info=True)

if 'makanan_terdeteksi' in st.session_state:
    st.subheader("📋 Hasil Deteksi Makanan")
    
    # Tampilkan hasil deteksi dalam format yang diinginkan
    for idx, makanan in enumerate(st.session_state['makanan_terdeteksi'], 1):
        st.write(f"makanan {idx}: {makanan}")
    
    st.subheader("✏️ Perbaiki Deteksi jika Tidak Tepat")
    st.write("Silakan periksa dan sesuaikan nama makanan serta beratnya jika diperlukan.")
    
    # Form untuk setiap makanan yang terdeteksi
    with st.form(key='makanan_form'):
        makanan_data = {}
        all_gizi_data = []
        
        for idx, makanan in enumerate(st.session_state['makanan_terdeteksi']):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                makanan_terkoreksi = st.text_input(
                    f"Makanan {idx + 1}:",
                    value=makanan,
                    key=f"makanan_{idx}"
                )
            
            with col2:
                berat_gram = st.number_input(
                    f"Berat (g):",
                    min_value=1,
                    max_value=1000,
                    value=100,
                    key=f"berat_{idx}"
                )
            
            makanan_data[makanan_terkoreksi] = berat_gram
        
        submit_button = st.form_submit_button("Analisis Kandungan Gizi")
        
        if submit_button:
            st.subheader("📊 Hasil Analisis Nutrisi")
            
            # Buat header tabel
            columns = ["Makanan", "Gram", "Kalori (kkal)", "Protein (g)", "Karbohidrat (g)", "Lemak (g)", "Nutrisi Penting"]
            
            # Kumpulkan data untuk tabel
            table_data = []
            
            for makanan, berat in makanan_data.items():
                with st.spinner(f"Menganalisis {makanan}..."):
                    try:
                        hasil_gizi = dapatkan_info_gizi(makanan, berat)
                        # Tambahkan data ke tabel
                        table_data.append(hasil_gizi.split('|'))
                    except Exception as e:
                        st.error(f"Gagal menganalisis {makanan}")
                        st.error(f"Detail error: {str(e)}")
            
            # Tampilkan tabel
            if table_data:
                df = pd.DataFrame(table_data, columns=columns)
                st.dataframe(df, use_container_width=True)

# Footer
st.markdown("---")
st.caption("Diberdayakan oleh Llama 🦙")

# Sidebar dengan informasi tambahan
with st.sidebar:
    st.header("Panduan Penggunaan")
    st.markdown("""
    1. **Pilih Sumber Gambar**
       - Unggah gambar dari perangkat
       - Atau ambil foto langsung dengan kamera
    
    2. **Deteksi Makanan**
       - Klik tombol 'Deteksi Makanan'
       - Tunggu hasil analisis AI
    
    3. **Koreksi Jika Perlu**
       - Periksa hasil deteksi untuk setiap makanan
       - Koreksi nama makanan jika diperlukan
    
    4. **Masukkan Berat**
       - Tentukan berat untuk setiap makanan dalam gram
    
    5. **Analisis Gizi**
       - Klik 'Analisis Kandungan Gizi'
       - Lihat hasil analisis mikronutrien untuk setiap makanan
    """)
    
    st.markdown("---")
    st.markdown("""
    ### Catatan
    - Pastikan gambar jelas dan fokus
    - Berat dalam gram harus akurat untuk setiap makanan
    - Hasil analisis akan ditampilkan untuk setiap makanan secara terpisah
    """)

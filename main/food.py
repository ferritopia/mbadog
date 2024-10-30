import streamlit as st
from groq import Groq
import os
from PIL import Image
import io
import base64
import pandas as pd

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

def analisis_gambar(image_base64):
    """Analisis makanan dalam gambar menggunakan model vision Groq"""
    completion = client.chat.completions.create(
        model="llama-3.2-90b-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text", 
                        "text": "Identifikasi makanan dalam gambar ini dan berikan daftar dalam format:\nmakanan 1: [nama makanan]\nmakanan 2: [nama makanan]"
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
    
    response = completion.choices[0].message.content
    
    # Debug: Print raw response
    print("Raw response:", response)
    
    # Parsing hasil deteksi ke dalam list
    makanan_list = []
    for line in response.split('\n'):
        if ':' in line:
            makanan = line.split(':')[1].strip()
            if makanan:  # Hanya tambahkan jika ada makanan
                makanan_list.append(makanan)
    
    # Debug: Print parsed list
    print("Parsed list:", makanan_list)
    return makanan_list

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
                
                # Dapatkan hasil deteksi makanan
                makanan_terdeteksi = analisis_gambar(img_str)
                st.session_state['makanan_terdeteksi'] = makanan_terdeteksi
            except Exception as e:
                st.error("Terjadi kesalahan saat menganalisis gambar.")
                st.error(f"Detail error: {str(e)}")

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

import streamlit as st
from groq import Groq
import os
from PIL import Image
import io
import base64

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
                    {"type": "text", "text": "Apa saja makanan yang ada dalam gambar ini? Berikan daftar makanan dalam format yang terpisah dengan koma."},
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
        temperature=0.5,
        max_tokens=1024,
        top_p=1,
        stream=False,
    )
    # Memisahkan hasil deteksi menjadi list makanan
    makanan_list = [item.strip() for item in completion.choices[0].message.content.split(',')]
    return makanan_list

def dapatkan_info_gizi(nama_makanan, gram):
    """Dapatkan informasi gizi menggunakan model teks Groq"""
    prompt = f"""Analisis mikronutrien dalam {gram}g {nama_makanan}. 
    Berikan juga informasi kalori, lemak, protein, karbohidrat nya dalam bentuk tabel jika memungkinkan.
    Jawaban HARUS dalam Bahasa Indonesia."""

    info_gizi = ""
    stream = client.chat.completions.create(
        model="llama-3.2-90b-text-preview",
        messages=[
            {
                "role": "system",
                "content": "Anda adalah ahli gizi yang mengkhususkan diri dalam analisis mikronutrien. Berikan informasi ilmiah yang akurat tentang mikronutrien makanan."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=1024,
        top_p=1,
        stream=True,
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content:
            info_gizi += chunk.choices[0].delta.content
    
    return info_gizi

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
                st.error(f"Terjadi kesalahan saat menganalisis gambar: {str(e)}")
                st.error("Detail error untuk debugging:", e)

if 'makanan_terdeteksi' in st.session_state:
    st.subheader("Makanan yang Terdeteksi")
    
    # Dictionary untuk menyimpan makanan dan gramasinya
    if 'makanan_data' not in st.session_state:
        st.session_state['makanan_data'] = {}
    
    # Form untuk setiap makanan yang terdeteksi
    with st.form(key='makanan_form'):
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
            
            st.session_state['makanan_data'][makanan_terkoreksi] = berat_gram
        
        submit_button = st.form_submit_button("Analisis Kandungan Gizi")
        
        if submit_button:
            for makanan, berat in st.session_state['makanan_data'].items():
                with st.spinner(f"Menganalisis kandungan gizi {makanan}..."):
                    try:
                        hasil_gizi = dapatkan_info_gizi(makanan, berat)
                        st.subheader(f"Analisis Mikronutrien untuk {berat}g {makanan}")
                        st.markdown(hasil_gizi)
                        st.markdown("---")
                    except Exception as e:
                        st.error(f"Terjadi kesalahan saat menganalisis kandungan gizi {makanan}: {str(e)}")

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

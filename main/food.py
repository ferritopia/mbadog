import streamlit as st
from groq import Groq
import os
from PIL import Image
import io
import base64

# Page configuration
st.set_page_config(
    page_title="Mbadog: Food Nutrition Analyzer",
    page_icon="🥗",
    layout="centered"
)

# Initialize Groq client
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

os.environ["GROQ_API_KEY"] = GROQ_API_KEY
client = Groq()

def analyze_image(image_base64):
    """Analyze food in image using Groq's vision model"""
    completion = client.chat.completions.create(
        model="llama-3.2-90b-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Makanan apa yang Anda lihat pada gambar ini? Berikan jawaban yang sederhana dan jelas, cukup dengan menyebutkan nama makanannya.."
                    },
                    {
                        "type": "image",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
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
    return completion.choices[0].message.content

def get_nutrition_info(food_name, grams):
    """Get nutrition information using Groq's text model"""
    prompt = f"""Analisa mikronutrisi dari {grams}g {food_name}. 
    Sediakan juga informasi berapa kalori, lemak, protein, karbohidrat nya dalam bentuk tabel jika memungkinkan"""

    nutrition_info = ""
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
            nutrition_info += chunk.choices[0].delta.content
    
    return nutrition_info

# Main app
st.title("🥗 Mbadog: Cek mikronutrisi sebelum makan!")
st.write("Unggah gambar makanan atau ambil foto untuk menganalisis")

# Image input section
image_source = st.radio("Pilih Sumber Gambar:", ("Upload Gambar", "Ambil Foto"))

if image_source == "Upload Gambar":
    uploaded_file = st.file_uploader("Pilih gambar...", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Gambar terunggah", use_column_width=True)
else:
    camera_photo = st.camera_input("Ambil foto")
    if camera_photo is not None:
        image = Image.open(camera_photo)
        st.image(image, caption="Ambil foto", use_column_width=True)

# Analysis section
if 'image' in locals():
    if st.button("Deteksi"):
        with st.spinner("Menganasila gambar..."):
            # Convert image to base64
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # Get food detection
            detection_result = analyze_image(img_str)
            st.session_state['detected_food'] = detection_result

if 'detected_food' in st.session_state:
    st.subheader("Deteksi Makanan")
    st.write(st.session_state['detected_food'])
    
    # Allow food name correction
    corrected_food = st.text_input("Correct food name if needed:", 
                                  value=st.session_state['detected_food'])
    
    # Weight input
    weight_grams = st.number_input("Enter weight (grams):", 
                                  min_value=1, max_value=1000, value=100)
    
    # Nutrition analysis button
    if st.button("Analisa"):
        with st.spinner("Mengecek makanan..."):
            nutrition_result = get_nutrition_info(corrected_food, weight_grams)
            st.subheader(f"Informasi untuk {weight_grams}g of {corrected_food}")
            st.markdown(nutrition_result)

# Footer
st.markdown("---")
st.caption("Powered by Llama 🦙")

import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import fitz

# --- 1. SETUP ---
api_key = "AIzaSyDllN5WrWDChev9gw0r65xu0eZqv3gGazQ"

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. HELPER FUNCTIONS ---

def pdf_to_image(uploaded_file):
    """Converts the first page of a PDF to an image."""
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def generate_question(topic, difficulty):
    """Asks AI to create a question based on a topic."""
    prompt = f"""
    Create a strictly 'CBSE-style' descriptive question for EMRS PGT Computer Science.
    Topic: {topic}
    Difficulty: {difficulty}
    Marks: 4
    
    Output ONLY the question text. Do not provide the answer.
    """
    response = model.generate_content(prompt)
    return response.text

def get_evaluation(image, question, max_marks, rubric_hints):
    """Evaluates the answer image."""
    prompt = f"""
    You are a strict CBSE Computer Science Examiner.
    Task: Evaluate the student's handwritten answer in the image.
    
    Question: {question}
    Max Marks: {max_marks}
    Rubric/Key Points: {rubric_hints}
    
    Output specific JSON using this schema:
    {{
        "marks_awarded": float,
        "evaluation_summary": "string",
        "mistakes": ["string", "string"],
        "model_answer": "string"
    }}
    """
    try:
        response = model.generate_content(
            [prompt, image],
            generation_config={"response_mime_type": "application/json"}
        )
        return response.text
    except Exception as e:
        return json.dumps({"error": str(e)})

# --- 3. THE UI LAYOUT ---
st.set_page_config(page_title="EMRS AI Study Companion", layout="wide")
st.title("🎓 EMRS PGT AI Companion")

if 'current_question' not in st.session_state:
    st.session_state['current_question'] = ""

# --- SIDEBAR: MODE SELECTION ---
st.sidebar.header("Step 1: Get a Question")
mode = st.sidebar.radio("How do you want to start?", 
                        ["🤖 Generate a Random Question", "✍️ Write My Own Question"])

# --- MAIN AREA LOGIC ---

# PART A: HANDLING THE QUESTION
if mode == "🤖 Generate a Random Question":
    st.subheader("🤖 AI Question Generator")
    col1, col2 = st.columns(2)
    with col1:
        topic = st.selectbox("Select Topic:", 
             ["Computer Systems and Organization", "Computational Thinking and Programming with Python", "Computer Networks", 
              "Database Management System", "Society Law and Ethics", "Emerging Trends", "Artificial Intelligence"])
    with col2:
        difficulty = st.select_slider("Difficulty:", options=["Easy", "Medium", "Hard"])
    
    if st.button("Generate New Question"):
        with st.spinner("Creating a question..."):
            q_text = generate_question(topic, difficulty)
            st.session_state['current_question'] = q_text
            st.success("Question Generated! See below.")

elif mode == "✍️ Write My Own Question":
    st.subheader("✍️ Manual Question Entry")
    user_q = st.text_area("Type your question here:", height=100, 
                          placeholder="e.g. Explain the difference between DDL and DML.")
    if st.button("Use This Question"):
        if user_q.strip():
            st.session_state['current_question'] = user_q
            st.success("Question Set! Proceed to upload your answer.")
        else:
            st.error("Please type a question first.")

# Separator
st.markdown("---")

# PART B: ANSWER UPLOAD (Only shows if a question exists)
if st.session_state['current_question']:
    st.header("Step 2: Check Your Answer")
    
    # Show the active question
    st.info(f"**Current Question:** {st.session_state['current_question']}")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        uploaded_file = st.file_uploader("Upload Answer Sheet (Image/PDF)", type=["jpg", "png", "pdf"])
    
    with col2:
        max_marks = st.number_input("Max Marks:", value=4)
        rubric = st.text_input("Rubric (Optional hints):", value="Standard CBSE marking scheme")

    if uploaded_file and st.button("Evaluate Answer"):
        if uploaded_file.type == "application/pdf":
            with st.spinner("Processing PDF..."):
                image = pdf_to_image(uploaded_file)
        else:
            image = Image.open(uploaded_file)
        
        st.image(image, caption="Your Answer Sheet", width=400)
        
        with st.spinner("👨‍🏫 Examiner is checking your copy..."):
            raw_response = get_evaluation(image, st.session_state['current_question'], max_marks, rubric)
            
            try:
                data = json.loads(raw_response)
                
                if "error" in data:
                    st.error(f"Error: {data['error']}")
                else:
                    # Score Card
                    c1, c2 = st.columns([1, 2])
                    with c1:
                        st.metric("Marks Awarded", f"{data['marks_awarded']} / {max_marks}")
                        st.progress(float(data['marks_awarded']) / max_marks)
                    
                    with c2:
                        st.subheader("Examiner's Remarks")
                        st.write(data['evaluation_summary'])
                        
                        if data.get('mistakes'):
                            st.write("**❌ Mistakes:**")
                            for m in data['mistakes']: st.write(f"- {m}")
                    
                    st.divider()
                    st.subheader("✅ Model Answer")
                    st.info(data['model_answer'])

            except json.JSONDecodeError:
                st.error("Error reading AI response.")
                st.code(raw_response)

else:
    st.info("👈 Please Select a Mode in the Sidebar to start!")
from flask import Flask, request, jsonify, render_template, send_file
from werkzeug.utils import secure_filename
import os
from PyPDF2 import PdfReader
from gtts import gTTS
import nltk
import re
from fpdf import FPDF

nltk.download('punkt')
nltk.download('stopwords')

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def simplify_text(text):
    from nltk.tokenize import sent_tokenize, word_tokenize

    # Predefined simpler synonyms for complex words
    simple_synonyms = {
        "complicated": "hard",
        "difficult": "hard",
        "complex": "simple",
        "elaborate": "explain",
        "demonstrate": "show",
        "understanding": "idea",
        "utilize": "use",
        "assist": "help",
        "facilitate": "help",
        "objective": "goal",
        "significant": "important",
        "process": "steps",
        "concept": "idea",
    }

    # Step 1: Split text into sentences
    sentences = sent_tokenize(text)
    simplified_sentences = []

    for sentence in sentences:
        # Step 2: Tokenize each sentence into words
        words = word_tokenize(sentence)

        # Step 3: Replace complex words with simpler synonyms
        simplified_words = [
            simple_synonyms.get(word.lower(), word) for word in words
        ]

        # Step 4: Reorganize into short chunks of 8 words max
        chunks = []
        chunk_size = 8
        for i in range(0, len(simplified_words), chunk_size):
            chunk = ' '.join(simplified_words[i:i + chunk_size])
            chunks.append(chunk)

        # Join chunks with newlines for better readability
        simplified_sentences.append('\n'.join(chunks))

    # Step 5: Combine all simplified sentences with extra spacing
    return '\n\n'.join(simplified_sentences)


def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ''
        for page in reader.pages:
            text += page.extract_text() + '\n'
        return text
    except Exception as e:
        raise ValueError(f"Error reading PDF: {str(e)}")

@app.route('/')
def index():
    return render_template('code.html')

@app.route('/simplify', methods=['POST'])
def simplify():
    data = request.json
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    simplified_text = simplify_text(text)
    return jsonify({'simplified_text': simplified_text})

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['pdf']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        extracted_text = extract_text_from_pdf(filepath)
        simplified_text = simplify_text(extracted_text)

        simplified_file_path = os.path.join(PROCESSED_FOLDER, 'simplified.txt')
        with open(simplified_file_path, 'w', encoding='utf-8') as f:
            f.write(simplified_text)

        return jsonify({'message': 'PDF processed successfully', 'simplified_text': simplified_text})
    except ValueError as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save_simplified', methods=['POST'])
def save_simplified():
    data = request.json
    text = data.get('text', '')
    filename = data.get('filename', 'simplified_output.txt')

    if not text:
        return jsonify({'error': 'No text provided'}), 400

    if not filename.endswith('.txt'):
        filename += '.txt'

    file_path = os.path.join(PROCESSED_FOLDER, secure_filename(filename))
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)

    return jsonify({'message': 'Simplified text saved successfully', 'file_path': file_path})

@app.route('/text_to_speech', methods=['POST'])
def text_to_speech():
    data = request.json
    text = data.get('text', '')
    if not text:
        return jsonify({'error': 'No text provided'}), 400

    tts = gTTS(text)
    audio_path = os.path.join(PROCESSED_FOLDER, 'speech.mp3')
    tts.save(audio_path)

    return send_file(audio_path, as_attachment=True)

@app.route('/download_pdf', methods=['GET'])
def download_pdf():
    simplified_file_path = os.path.join(PROCESSED_FOLDER, 'simplified.txt')
    if not os.path.exists(simplified_file_path):
        return jsonify({'error': 'No simplified text available for download'}), 404

    pdf_path = os.path.join(PROCESSED_FOLDER, 'simplified.pdf')
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', size=12)
    
    with open(simplified_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            pdf.multi_cell(0, 10, line)
    
    pdf.output(pdf_path)

    return send_file(pdf_path, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)


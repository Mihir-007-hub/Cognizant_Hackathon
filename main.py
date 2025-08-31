import os
import io
import docx
import pytesseract
from PIL import Image
from fastapi import FastAPI, UploadFile, File
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="Loan Document Processor API")

# Initialize the LLM
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0)

# The prompt remains the same
prompt_template = """
You are an expert AI assistant for a loan processing bank.
Your task is to analyze the provided text from a financial document and perform two things:
1. Extract the following key information in a structured JSON format:
   - Applicant Name
   - Address
   - Gross Income (specify if monthly or annual)
   - Taxes Paid
2. Analyze the document for any semantic inconsistencies or red flags a loan officer should know about.

Here is the document text:
---
{document_text}
---

Provide your response as a single, clean JSON object with two keys: "extracted_data" and "analysis". Do not add any extra text or markdown formatting like ```json.
"""
prompt = ChatPromptTemplate.from_template(prompt_template)
chain = prompt | llm | StrOutputParser()

# --- Text Extraction Functions (remain the same) ---
def extract_text_from_docx(file_stream):
    doc = docx.Document(file_stream)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_image(file_stream):
    image = Image.open(file_stream)
    return pytesseract.image_to_string(image)

def extract_text_from_pdf(file_stream):
    reader = PdfReader(file_stream)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

@app.post("/process-document/")
async def process_document(file: UploadFile = File(...)):
    try:
        file_content = await file.read()
        file_stream = io.BytesIO(file_content)
        document_text = ""
        filename = file.filename.lower() # Get filename and convert to lowercase

        # --- NEW, MORE ROBUST LOGIC ---
        # Check the filename extension instead of content_type
        if filename.endswith('.pdf'):
            document_text = extract_text_from_pdf(file_stream)
        elif filename.endswith('.docx'):
            document_text = extract_text_from_docx(file_stream)
        elif filename.endswith(('.png', '.jpg', '.jpeg')):
            document_text = extract_text_from_image(file_stream)
        else:
            return {"error": f"Unsupported file type: {filename}"}
        
        # --- IMPORTANT DEBUGGING STEP ---
        # This will print the first 500 characters of the extracted text to your backend terminal
        print("--- Extracted Text ---")
        print(f"{document_text[:500]}...")
        print("----------------------")

        if not document_text.strip():
            # Now we return a clear error if no text was found
            return {"error": "Could not extract any text from the document. The document might be empty or unreadable."}
        
        # Process the extracted text using the LangChain
        response = chain.invoke({"document_text": document_text})
        
        return {"filename": file.filename, "results": response}
    except Exception as e:
        # This will now catch errors from Tesseract if it's not configured correctly
        return {"error": f"An error occurred during processing: {str(e)}"}
import os
import io
import json
import base64
import re
import uuid
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Dict, Any, List
from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv
from pdf2image import convert_from_bytes
# --- NEW: MongoDB Dependencies ---
import motor.motor_asyncio
from bson import ObjectId

load_dotenv()
app = FastAPI(title="Intelligent Document Processor API")

# --- NEW: MongoDB Connection ---
MONGO_DETAILS = os.getenv("MONGO_DETAILS")
if not MONGO_DETAILS:
    raise ValueError("MONGO_DETAILS environment variable not set!")

# --- FIX: Added tls=True for robust SSL connection to MongoDB Atlas ---
# Ensure your IP is whitelisted in MongoDB Atlas under Network Access.
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS, tls=True, tlsAllowInvalidCertificates=True)

db = client.loan_processing
verified_collection = db.get_collection("verified_documents")

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0)

# --- Prompts are preserved ---
unified_prompt = """
You are an expert AI assistant for a loan processing bank. Your task is to analyze the provided document image and perform two steps:
1.  **Classify the document.** Your first response in the JSON should be the 'document_type'. Choose from: 'Payslip', 'Tax Form', 'PAN Card', 'Identity Card', or 'Other'.
2.  **Extract key information based on the type you identified.** For each field, provide the 'value' and a 'confidence' score.
    - If it is a 'Payslip', extract: "Applicant Name", "Gross Income", "Net Pay", "Total Taxes", "Pay Period End Date".
    - If it is a 'Tax Form', extract: "Applicant Name", "Total Income", "Taxes Paid", "Assessment Year".
    - If it is a 'PAN Card', extract: "Name", "Father's Name", "Date of Birth", "PAN Number".
    - If it is an 'Identity Card', extract: "Name", "Date of Birth", "Address".
    - If 'Other', extract any PII and key financial figures.
3.  **Provide an analysis.** This MUST be a JSON object with two keys: "red_flags" (a list of strings) and "inconsistencies" (a list of strings). If there are none, return empty lists.
Follow these strict rules:
- Return numbers as floats, with NO currency symbols or commas.
- Provide your response as a single, valid JSON object with three top-level keys: "document_type", "extracted_data", and "analysis".
- The final output must be ONLY the JSON object, with no extra text or markdown.
"""

# --- RESTORED: Cross-Validation Prompt ---
cross_validation_prompt = """
You are a senior loan underwriter AI. You have been provided with extracted data from multiple documents for a single loan application.
Your task is to perform a final cross-validation check. Analyze all the data and identify any critical inconsistencies between the documents.
Specifically check for mismatches in "Applicant Name" and "Date of Birth".
Here is the data from all documents:
---
{summarized_data}
---
Provide a summary of your findings as a single, valid JSON object with two keys: "overall_summary" (a string) and "validation_passed" (a boolean).
The final output must be ONLY the JSON object, with no extra text or markdown.
"""

final_summary_prompt = """
You are the lead AI underwriter. You have been given the complete data extracted from a loan application package, including individual document analyses and an initial cross-validation report.
Your task is to generate a final, comprehensive summary report for the human loan officer.
Based on all the information provided below, generate a report that includes:
1.  **Overall Summary:** A brief, two-sentence summary of the applicant's financial profile.
2.  **Key Financial Metrics:** This MUST be a list of strings, with each string formatted as "Metric Name: Value".
3.  **Consolidated Red Flags:** Combine all red flags and inconsistencies from all documents into a single, clear list of strings.
4.  **Final Recommendation:** Provide a final recommendation from these options: 'Approve', 'Deny', or 'Manual Review Required'.
Here is all the data:
---
{complete_data}
---
Provide your response as a single, valid JSON object with four keys: "overall_summary", "key_financial_metrics", "consolidated_red_flags", and "final_recommendation".
The final output must be ONLY the JSON object.
"""


def pil_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"

async def process_single_file(file_content: bytes, filename: str) -> dict:
    images_to_process = []
    if filename.endswith('.pdf'):
        images_to_process = convert_from_bytes(file_content)
    elif filename.endswith(('.png', '.jpg', '.jpeg')):
        images_to_process.append(Image.open(io.BytesIO(file_content)))
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {filename}")

    if not images_to_process:
         raise HTTPException(status_code=400, detail="Could not convert document to image.")

    content_parts = [{"type": "text", "text": unified_prompt}]
    for img in images_to_process:
        content_parts.append({"type": "image_url", "image_url": pil_to_base64(img)})
    
    message = HumanMessage(content=content_parts)
    response_json_string = llm.invoke([message]).content
    
    try:
        clean_response = response_json_string.replace("```json", "").replace("```", "").strip()
        final_result = json.loads(clean_response)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"AI returned a non-JSON response: {response_json_string}")

    final_result['filename'] = filename
    return final_result

@app.post("/process-application/")
async def process_application(files: List[UploadFile] = File(...)):
    try:
        application_id = str(uuid.uuid4()) # Generate a unique ID for this application batch
        application_results = []
        for file in files:
            file_content = await file.read()
            single_result = await process_single_file(file_content, file.filename.lower())
            application_results.append(single_result)
        
        summarized_data_for_ai = [{"filename": res.get('filename'), "document_type": res.get('document_type'), "data": res.get('extracted_data')} for res in application_results]
        
        # --- RESTORED: Cross-Validation Step ---
        cross_val_message = HumanMessage(content=cross_validation_prompt.format(summarized_data=json.dumps(summarized_data_for_ai, indent=2)))
        cross_val_response_str = llm.invoke([cross_val_message]).content
        
        try:
            json_match = re.search(r'\{.*\}', cross_val_response_str, re.DOTALL)
            cross_val_json = json.loads(json_match.group(0)) if json_match else {}
        except json.JSONDecodeError:
            cross_val_json = {"overall_summary": "AI cross-validation returned an invalid format.", "validation_passed": False}

        # --- RESTORED: Final Summary Report Step ---
        complete_data_for_summary = { 
            "individual_documents": application_results,
            "initial_cross_validation": cross_val_json
        }
        summary_message = HumanMessage(content=final_summary_prompt.format(complete_data=json.dumps(complete_data_for_summary, indent=2)))
        summary_response_str = llm.invoke([summary_message]).content

        try:
            json_match = re.search(r'\{.*\}', summary_response_str, re.DOTALL)
            summary_json = json.loads(json_match.group(0)) if json_match else {}
        except json.JSONDecodeError:
            summary_json = {"final_recommendation": "Error", "overall_summary": "AI failed to generate a final summary report."}

        return {
            "application_id": application_id,
            "individual_document_results": application_results,
            "cross_validation_report": cross_val_json,
            "final_summary_report": summary_json
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during application processing: {str(e)}")


class VerificationPayload(BaseModel):
    application_id: str
    filename: str
    original_ai_data: Dict[str, Any]
    verified_data: Dict[str, str]

@app.post("/save-verified-document/")
async def save_verified_document(payload: VerificationPayload):
    try:
        await verified_collection.update_many(
            {"application_id": payload.application_id, "filename": payload.filename, "is_active": True},
            {"$set": {"is_active": False, "end_date": datetime.now(timezone.utc)}}
        )
        
        new_document_record = {
            "application_id": payload.application_id,
            "filename": payload.filename,
            "ai_data": payload.original_ai_data.get("extracted_data", {}),
            "verified_data": payload.verified_data,
            "start_date": datetime.now(timezone.utc),
            "end_date": None,
            "is_active": True
        }
        
        result = await verified_collection.insert_one(new_document_record)
        return {"status": "success", "message": f"Verified data for {payload.filename} saved with ID {result.inserted_id}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save data to MongoDB: {str(e)}")

@app.get("/get-report-data/")
async def get_report_data():
    try:
        # --- CHANGE: Fetch all documents to show history, not just active ones ---
        cursor = verified_collection.find({})
        documents = await cursor.to_list(length=None)
        for doc in documents:
            doc["_id"] = str(doc["_id"])
        return documents
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch report data: {str(e)}")

@app.delete("/delete-all-data/")
async def delete_all_data():
    try:
        await verified_collection.delete_many({})
        return {"status": "success", "message": "All verified data has been deleted from the database."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete data: {str(e)}")


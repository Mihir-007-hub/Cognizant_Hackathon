import streamlit as st
import requests
import json
import pandas as pd
import re
import os
import numpy as np

# --- Page Configuration ---
st.set_page_config(
    page_title="Intelligent Document Processor 🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Styling ---
st.markdown(
    """
    <style>
    .big-font {
        font-size:30px !important;
        font-weight: bold;
    }
    .medium-font {
        font-size:22px !important;
        font-weight: bold;
        color: #1E88E5; /* A professional blue */
    }
    .st-emotion-cache-1r6dm7m { /* Targets the main block for the uploader */
        padding: 1rem;
        border-radius: 10px;
        border: 1px dashed #1E88E5;
    }
    /* Style for metric labels */
    .st-emotion-cache-1g6goon {
        font-size: 16px;
        color: #4A4A4A;
    }
    .report-box {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        background-color: #fafafa;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# --- Sidebar for Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to", 
    ["Loan Application Processor", "Reporting Dashboard"], 
    key="nav_radio"
)
st.sidebar.markdown("---")
st.sidebar.info("This project leverages Generative AI to automate loan document processing, including a human-in-the-loop verification workflow.")

def display_verification_form(doc_data, unique_key):
    extracted_data = doc_data.get("extracted_data", {})
    filename = doc_data.get("filename", "unknown_file")
    
    if not extracted_data:
        st.warning("No structured data was extracted to verify.")
        return

    with st.form(key=f"verification_form_{unique_key}"):
        corrected_data = {}
        for field, details in extracted_data.items():
            value = details.get('value', '') if isinstance(details, dict) else details
            confidence = details.get('confidence', 0.0) * 100 if isinstance(details, dict) else 0.0
            
            help_text = f"Confidence: {confidence:.1f}%"
            if confidence < 75:
                help_text = f"⚠️ Low Confidence ({confidence:.1f}%) - Please verify carefully."

            corrected_data[field] = st.text_input(
                label=f"{field}",
                value=value,
                key=f"{unique_key}_{field.lower().replace(' ', '_')}",
                help=help_text
            )

        submitted = st.form_submit_button("Approve & Save This Document's Data")

        if submitted:
            with st.spinner("Saving verified data..."):
                payload = {
                    "filename": filename,
                    "original_ai_data": doc_data,
                    "verified_data": corrected_data
                }
                try:
                    save_response = requests.post("http://127.0.0.1:8000/save-data/", json=payload)
                    if save_response.status_code == 200:
                        st.success(f"✅ Verified data for `{filename}` saved successfully!")
                    else:
                        st.error(f"Failed to save data for `{filename}`.")
                except requests.exceptions.ConnectionError:
                    st.error("🚫 Connection Error: Could not connect to the backend to save data.")


# --- Page 1: Loan Application Processor ---
if page == "Loan Application Processor":
    st.title("🏦 Intelligent Loan Application Processor")
    st.markdown("---")
    st.markdown(
        """
        Upload all documents for a single loan application (e.g., Payslip, Tax Form, ID card). 
        The AI will process each file, then generate a final underwriting report.
        """
    )
    st.markdown("---")

    st.subheader("📁 Upload Loan Application Package")
    uploaded_files = st.file_uploader(
        "Drag & Drop all documents here or Click to Browse",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        help="You can select multiple files at once."
    )

    if uploaded_files:
        if st.button("Process Full Application", type="primary"):
            st.info(f"✨ Processing {len(uploaded_files)} documents...")
            with st.spinner('AI is analyzing the application... This may take some time.'):
                multipart_files = [('files', (file.name, file.getvalue(), file.type)) for file in uploaded_files]
                try:
                    response = requests.post("http://127.0.0.1:8000/process-application/", files=multipart_files)
                    if response.status_code == 200:
                        st.success('✅ Application processed successfully!')
                        st.session_state.application_results = response.json()
                    else:
                        try:
                            error_detail = response.json().get('detail', response.text)
                        except json.JSONDecodeError:
                            error_detail = response.text
                        st.error(f"❌ Error from server ({response.status_code}): {error_detail}")
                        st.session_state.application_results = None
                except requests.exceptions.ConnectionError:
                    st.error("🚫 Connection Error: Could not connect to the backend.")
                    st.session_state.application_results = None

    if "application_results" in st.session_state and st.session_state.application_results:
        results = st.session_state.application_results
        
        st.markdown("---")
        st.header("🏁 Final Underwriting Summary Report")

        report = results.get('final_summary_report', {})
        recommendation = report.get('final_recommendation', 'Error')
        summary = report.get('overall_summary', "No summary provided.")
        metrics = report.get('key_financial_metrics', [])
        red_flags = report.get('consolidated_red_flags', [])

        if recommendation == 'Approve':
            st.success(f"**Recommendation: {recommendation}**")
        elif recommendation == 'Manual Review Required':
            st.warning(f"**Recommendation: {recommendation}**")
        else:
            st.error(f"**Recommendation: {recommendation}**")

        st.markdown(f"**AI Summary:** *{summary}*")
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### Key Financial Metrics")
            if metrics:
                for metric_str in metrics:
                    st.write(f"- {metric_str}")
            else:
                st.write("None identified.")
        
        with col2:
            st.markdown("##### Consolidated Red Flags")
            if red_flags:
                for flag in red_flags:
                    st.write(f"- 🚩 {flag}")
            else:
                st.write("None identified.")
        
        st.markdown("---")
        st.subheader("📄 Individual Document Verification")
        st.info("Review each document below. You can correct the data and save it individually.")

        for i, doc_result in enumerate(results.get('individual_document_results', [])):
            doc_type = doc_result.get('document_type', 'Unknown')
            filename = doc_result.get('filename', 'N/A')
            
            with st.expander(f"**{doc_type}**: `{filename}`"):
                col1_doc, col2_doc = st.columns(2)
                with col1_doc:
                    display_verification_form(doc_result, unique_key=f"doc_{i}")
                with col2_doc:
                    st.markdown("##### AI Analysis")
                    analysis = doc_result.get('analysis', {})
                    if analysis:
                        st.json(analysis)
                    else:
                        st.write("No analysis provided.")

                # --- THE FIX: Add an expander for the full raw data of THIS document ---
                with st.expander("View Full Raw Data (for debugging)"):
                    st.json(doc_result) # Display the whole dictionary for the document


# --- Page 2: Reporting Dashboard ---
elif page == "Reporting Dashboard":
    st.title("📊 Reporting Dashboard")
    st.markdown("---")
    data_file_path = "verified_data.csv"

    if os.path.exists(data_file_path):
        try:
            df = pd.read_csv(data_file_path)
            st.subheader("Key Performance Indicators")
            total_fields, matching_fields = 0, 0
            fields_to_check = [col.replace('verified_', '') for col in df.columns if col.startswith('verified_')]
            for field in fields_to_check:
                ai_col, verified_col = f"ai_{field}", f"verified_{field}"
                if ai_col in df.columns and verified_col in df.columns:
                    df[ai_col] = df[ai_col].fillna('N/A').astype(str).str.strip()
                    df[verified_col] = df[verified_col].fillna('N/A').astype(str).str.strip()
                    comparison = df[ai_col] == df[verified_col]
                    matching_fields += comparison.sum()
                    total_fields += len(df)
            ai_accuracy = (matching_fields / total_fields) * 100 if total_fields > 0 else 0
            total_docs = len(df)
            avg_income = pd.to_numeric(df.get('verified_gross_income'), errors='coerce').mean()
            avg_taxes = pd.to_numeric(df.get('verified_total_taxes'), errors='coerce').mean()
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Docs Processed", f"{total_docs}")
            col2.metric("Avg. Gross Income", f"₹{avg_income:,.2f}" if not pd.isna(avg_income) else "N/A")
            col3.metric("Avg. Total Taxes", f"₹{avg_taxes:,.2f}" if not pd.isna(avg_taxes) else "N/A")
            col4.metric("AI Accuracy", f"{ai_accuracy:.2f}%")
            st.markdown("---")
            st.subheader("Verified Data Overview (AI vs. Human)")
            st.dataframe(df)

            st.markdown("---")
            st.subheader("Manage Data")
            if st.checkbox("I want to permanently delete all verified data."):
                if st.button("Delete All Data", type="primary", help="This action cannot be undone."):
                    try:
                        delete_response = requests.delete("http://127.0.0.1:8000/delete-data/")
                        if delete_response.status_code == 200:
                            st.success("All verified data has been deleted successfully.")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete data: {delete_response.text}")
                    except requests.exceptions.ConnectionError:
                        st.error("🚫 Connection Error: Could not connect to the backend.")
        except pd.errors.ParserError:
            st.error("Error reading the data file. It may be corrupted. Please use the 'Delete All Data' button to reset it.")
        except Exception as e:
            st.error(f"An unexpected error occurred while loading the dashboard: {e}")

    else:
        st.warning("No verified data found. Process and approve a document first.")


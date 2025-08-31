import streamlit as st
import requests
import json
import pandas as pd

# --- Page Configuration ---
st.set_page_config(
    page_title="Intelligent Loan Document Processor 🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Header Section ---
st.markdown(
    """
    <style>
    .big-font {
        font-size:30px !important;
        font-weight: bold;
    }
    .medium-font {
        font-size:20px !important;
        font-weight: bold;
        color: #4CAF50; /* A nice green for subheaders */
    }
    .st-emotion-cache-1r6dm7m { /* Targets the main block for the uploader */
        padding: 1rem;
        border-radius: 10px;
        border: 1px dashed #4CAF50;
    }
    .st-emotion-cache-13awx5x p { /* Targets text within components */
        font-size: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🏦 Intelligent Loan Document Processor powered by Gen AI")
st.markdown("---")

st.markdown(
    """
    Upload financial documents like **pay stubs** or **tax returns**. 
    Our AI will automatically:
    - ⚡ Extract key financial information.
    - 🔍 Perform semantic analysis to identify discrepancies or red flags.
    """
)
st.markdown("---")

# --- File Uploader Section ---
st.subheader("📁 Upload Your Document")
uploaded_file = st.file_uploader(
    "Drag & Drop your Document here or Click to Browse", 
    type=["pdf", "docx", "png", "jpg", "jpeg"],
    help="Supported file types: PDF, DOCX, PNG, JPG. Max size: 200MB."
)

# --- Processing Logic ---
if uploaded_file is not None:
    st.info(f"✨ Processing '{uploaded_file.name}'...")
    
    with st.spinner('AI is analyzing the document for key details and inconsistencies...'):
        files = {'file': (uploaded_file.name, uploaded_file.getvalue(), 'application/pdf')}
        
        try:
            response = requests.post("http://127.0.0.1:8000/process-document/", files=files)
            
            if response.status_code == 200:
                st.success('Document processed successfully! Results below. 🎉')
                
                results = response.json()
                
                try:
                    data_string = results.get("results", "{}")
                    if not data_string: # Handle case where results might be empty
                        st.warning("AI returned an empty response.")
                        data = {}
                    else:
                        data = json.loads(data_string)

                    st.markdown("---")
                    st.subheader("📊 Analysis Results")
                    
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("<p class='medium-font'>Extracted Key Information</p>", unsafe_allow_html=True)
                        extracted_data = data.get("extracted_data", {})
                        
                        if extracted_data:
                            display_data = {}
                            for k, v in extracted_data.items():
                                if isinstance(v, dict) and 'amount' in v:
                                    display_data[k] = f"{v.get('amount')} ({v.get('period', '')})".strip()
                                else:
                                    display_data[k] = v

                            df_extracted = pd.DataFrame(list(display_data.items()), columns=['Field', 'Value'])
                            st.table(df_extracted)
                        else:
                            st.info("No structured data extracted.")

                    with col2:
                        st.markdown("<p class='medium-font'>AI Semantic Analysis & Red Flags</p>", unsafe_allow_html=True)
                        analysis_content = data.get("analysis")

                        # --- NEW ROBUST LOGIC TO HANDLE VARYING AI OUTPUT ---
                        if isinstance(analysis_content, dict):
                            # This is the expected case (like for DOCX)
                            red_flags = analysis_content.get("red_flags", [])
                            inconsistencies = analysis_content.get("inconsistencies", [])
                            
                            st.error("🚨 Potential Red Flags:")
                            if red_flags:
                                for flag in red_flags: st.write(f"- {flag}")
                            else:
                                st.write("None identified.")

                            st.warning("⚠️ Noted Inconsistencies:")
                            if inconsistencies:
                                for item in inconsistencies: st.write(f"- {item}")
                            else:
                                st.write("None identified.")

                        elif isinstance(analysis_content, list):
                            # This handles the case from your screenshot
                            st.warning("⚠️ General Analysis Notes:")
                            if analysis_content:
                                for item in analysis_content:
                                    st.write(f"- {item}")
                            else:
                                st.write("None provided.")
                        
                        elif isinstance(analysis_content, str):
                             # Handles case where AI just returns a single string
                            st.warning("⚠️ General Analysis Notes:")
                            st.write(analysis_content)

                        elif analysis_content is None:
                            st.info("No analysis provided by the AI.")
                        
                        else:
                            st.info(f"Analysis content has an unexpected format: {type(analysis_content)}")


                    st.markdown("---")
                    with st.expander("🔍 View Raw AI Response (for debugging)"):
                        st.json(data)

                except json.JSONDecodeError:
                    st.error("❌ Error: Failed to decode the AI's response.")
                    st.code(results.get("results", "No raw results available."), language="text")
                
            else:
                st.error(f"❌ Error from server ({response.status_code}): {response.text}")

        except requests.exceptions.ConnectionError:
            st.error("🚫 Connection Error: Could not connect to the backend.")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

# --- Footer ---
st.sidebar.markdown("### About")
st.sidebar.info("This project leverages Generative AI (Google Gemini) and LangChain to automate loan document processing.")
st.sidebar.markdown("---")
st.sidebar.markdown("Built for a Hackathon 🚀")
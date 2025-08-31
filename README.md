# 🏦 Intelligent Loan Document Processor

An AI-powered application that automatically processes and analyzes financial documents for loan applications using Google Gemini AI and LangChain.

## ✨ Features

- **Multi-format Support**: Process PDF, DOCX, PNG, JPG, and JPEG files
- **AI-Powered Analysis**: Uses Google Gemini AI to extract key financial information
- **Smart Document Processing**: Automatically identifies applicant details, income, taxes, and addresses
- **Red Flag Detection**: AI analyzes documents for inconsistencies and potential issues
- **Modern Web Interface**: Clean Streamlit frontend with intuitive file upload
- **FastAPI Backend**: Robust API for document processing

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API key
- Tesseract OCR (for image processing)

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd loan_processor
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   GOOGLE_API_KEY=your_gemini_api_key_here
   ```

5. **Install Tesseract OCR**
   - **Windows**: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
   - **macOS**: `brew install tesseract`
   - **Linux**: `sudo apt-get install tesseract-ocr`

### Running the Application

1. **Start the FastAPI backend**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Start the Streamlit frontend** (in a new terminal)
   ```bash
   streamlit run app.py
   ```

3. **Open your browser** and navigate to `http://localhost:8501`

## 📁 Project Structure

```
loan_processor/
├── main.py              # FastAPI backend with document processing logic
├── app.py               # Streamlit frontend interface
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── .env                # Environment variables (create this)
├── dummy_payslip.pdf   # Sample document for testing
└── dummy_tax_return.pdf # Sample document for testing
```

## 🔧 API Endpoints

- `POST /process-document/` - Process uploaded financial documents

## 📊 Supported Document Types

- **PDF**: Tax returns, bank statements, pay stubs
- **DOCX**: Word documents with financial information
- **Images**: PNG, JPG, JPEG files (requires OCR)

## 🤖 AI Capabilities

The system extracts and analyzes:
- Applicant name and address
- Gross income (monthly/annual)
- Taxes paid
- Document inconsistencies
- Potential red flags for loan officers

## 🛠️ Technologies Used

- **Backend**: FastAPI, Python
- **Frontend**: Streamlit
- **AI**: Google Gemini, LangChain
- **Document Processing**: PyPDF, python-docx, Tesseract OCR
- **Data Handling**: Pandas, JSON

## 📝 Usage

1. Upload a financial document through the web interface
2. The AI automatically processes and extracts key information
3. View structured results and AI analysis
4. Identify potential issues or red flags

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter any issues:
1. Check the console for error messages
2. Ensure all dependencies are installed
3. Verify your Google API key is correct
4. Make sure Tesseract OCR is properly installed

## 🎯 Future Enhancements

- [ ] Batch document processing
- [ ] Document validation rules
- [ ] Export to various formats
- [ ] Integration with loan management systems
- [ ] Advanced fraud detection

# DPR Insight AI

> AI-powered platform for automated analysis, risk assessment, explainable predictions, and conversational question answering over Detailed Project Reports (DPRs).

DPR Insight AI is an end-to-end document intelligence application that combines **PDF processing, OCR, machine learning, explainable AI, vector search, and generative AI** to simplify the analysis of Detailed Project Reports.

The system allows users to upload a DPR, automatically extract and organize its contents, generate a project risk assessment, understand the factors contributing to the score, and ask natural-language questions about the uploaded document.

---

## 🚀 Key Features

### 📄 Intelligent PDF Processing
- Upload DPR documents through the web interface.
- Extract text and document structure using PyMuPDF.
- Detect pages with insufficient native text.
- Automatically use Tesseract OCR for scanned/image-based pages.
- Preserve page-level information for traceable answers.

### 📊 Risk Prediction
- Extract structured features from DPR documents.
- Predict project risk using a **Random Forest classifier**.
- Generate a risk score and risk-level distribution.
- Display the factors contributing to the prediction.

### 🔍 Explainable AI
- Uses **SHAP** to explain the Random Forest prediction.
- Shows which document characteristics contribute to increasing or decreasing the risk score.
- Helps users understand the model output instead of treating it as a black-box prediction.

### 🤖 RAG-Based Document Assistant
Users can ask questions directly about an uploaded DPR.

Example questions:

- What are the financial parameters mentioned in this DPR?
- What is the proposed project?
- What is the project timeline?
- What are the major risks mentioned?
- What is the total project cost?
- What are the sources of finance?
- Summarize the project objectives.

The RAG pipeline:

```text
User Question
      ↓
Question Embedding
      ↓
FAISS Similarity Search
      ↓
Relevant DPR Chunks
      ↓
Context Construction
      ↓
Gemini LLM
      ↓
Grounded Answer + Sources
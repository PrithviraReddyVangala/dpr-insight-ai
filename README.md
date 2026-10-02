# DPR Insight AI

### AI-Powered Detailed Project Report Analysis & Risk Intelligence

DPR Insight AI is an end-to-end AI application that analyzes Detailed Project Reports (DPRs), extracts structured project information, predicts project risk, explains model decisions using SHAP, and provides a Retrieval-Augmented Generation (RAG) assistant for document-grounded question answering.

---

## 🚀 Overview

Detailed Project Reports contain large amounts of financial, technical, timeline, and project-scope information.

DPR Insight AI automates the analysis process by combining:

- Document processing
- OCR
- Machine Learning
- Risk prediction
- SHAP explainability
- Semantic search
- Vector databases
- Retrieval-Augmented Generation
- Large Language Models

The goal is to transform unstructured DPR documents into actionable project insights.

---

## ✨ Key Features

### 📄 Intelligent Document Processing

- PDF document ingestion
- Structured section extraction
- OCR fallback for scanned documents
- Financial, timeline, scope and technical information extraction

### 📊 ML-Based Risk Prediction

- Feature extraction from DPR documents
- Random Forest risk model
- Project risk scoring
- SHAP-based explainability
- Feature-level contribution analysis

### 🤖 RAG-Based AI Assistant

- Document chunking
- Semantic embeddings
- FAISS vector search
- Context retrieval
- Gemini-powered question answering
- Document-grounded responses

### 📈 Interactive Dashboard

- Project overview
- Risk indicators
- Extracted information
- AI-generated insights
- Interactive charts

### ⚡ FastAPI Backend

- REST APIs
- Document upload
- Risk prediction
- RAG chat
- Asynchronous processing

---

# 🏗️ System Architecture

                    ┌───────────────────────────┐
                    │       DPR PDF Upload      │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │    Document Ingestion     │
                    │      PDF + OCR Fallback   │
                    └─────────────┬─────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
                    ▼                           ▼
        ┌─────────────────────┐     ┌─────────────────────┐
        │     Risk Model      │     │      RAG Engine     │
        ├─────────────────────┤     ├─────────────────────┤
        │ Feature Extraction  │     │ Text Chunking       │
        │ Random Forest       │     │ Embeddings          │
        │ SHAP Explainability │     │ FAISS Vector Store  │
        └──────────┬──────────┘     └──────────┬──────────┘
                   │                           │
                   ▼                           ▼
        ┌─────────────────────┐     ┌─────────────────────┐
        │   Risk Prediction   │     │    Gemini LLM       │
        │ + SHAP Explanation  │     │ Context-Aware RAG   │
        └──────────┬──────────┘     └──────────┬──────────┘
                   │                           │
                   └─────────────┬─────────────┘
                                 ▼
                    ┌───────────────────────────┐
                    │       FastAPI Backend      │
                    │  Upload │ Risk │ Chat API │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │    React + Tailwind UI    │
                    │ Dashboard │ Risk │ Chat   │
                    └───────────────────────────┘
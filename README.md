# 🧬 MediMatch - AI-Powered Drug Discovery Platform

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MediMatch is a comprehensive AI-powered drug discovery and analysis platform that combines molecular visualization,
knowledge graph exploration, target prediction, prescription OCR, and an intelligent AI copilot to assist researchers
and healthcare professionals.

![MediMatch Banner](https://via.placeholder.com/1200x400/009688/ffffff?text=MediMatch+AI+Drug+Discovery+Platform)

---

## ✨ Features

### 🔍 **Drug Search & Visualization**

- Search drugs from local database or automatically fetch from ChEMBL, PubChem, and DrugCentral
- Interactive 3D molecular structure visualization using RDKit and 3Dmol.js
- Comprehensive drug property display (LogP, PSA, IC50, targets, mechanisms)
- Side-by-side drug comparison with AI-generated insights

### 🕸️ **Knowledge Graph Visualization**

- Interactive drug-protein-disease relationship graphs
- Powered by PharmaSage knowledge base
- Dynamic visualization with customizable node counts
- Export and explore biomedical relationships

### 🎯 **Target Prediction**

- Molecular similarity-based target prediction using Tanimoto coefficients
- Find similar drugs and predict biological targets
- Mechanism of action inference from structural similarity
- Confidence scoring for predictions

### 📸 **Prescription OCR**

- AI-powered prescription text extraction
- Hosted API integration with local Gemini Vision fallback
- Medical entity recognition (drugs, dosages, frequencies)
- Drug interaction checking

### 🤖 **AI Drug Copilot**

- Conversational AI assistant powered by Groq Llama 3.3
- Knowledge graph-augmented responses
- Retrieval-Augmented Generation (RAG) for external insights
- PubMed and arXiv integration for latest research

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager
- API keys (see setup instructions)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/medimatch.git
cd medimatch
```

2. **Create virtual environment (recommended)**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Install spaCy medical model**

```bash
pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.3/en_core_sci_sm-0.5.3.tar.gz
```

5. **Set up environment variables**

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API keys
# You'll need:
# - GROQ_API_KEY (from https://console.groq.com/)
# - SERPER_API_KEY (from https://serper.dev/)
# - GEMINI_API_KEY (from https://makersuite.google.com/app/apikey)
```

6. **Prepare data files**

```bash
# Download the required dataset (not included in repo due to size)
# Place cleaned_clinical_drugs_dataset.csv in data/ folder
# Or the app will fallback to external APIs
```

7. **Run the application**

```bash
python app.py
```

8. **Open in browser**

```
http://localhost:5000
```

---

## 📁 Project Structure

```
medimatch/
│
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
│
├── prescription_ocr/          # OCR module
│   ├── gemini_vision.py       # Gemini Vision OCR
│   ├── medical_ner.py         # Medical entity recognition
│   ├── pipeline.py            # OCR pipeline
│   └── ...
│
├── templates/                 # HTML templates
│   ├── index.html            # Main drug search page
│   ├── drug_copilot.html     # AI Copilot interface
│   ├── prescription_ocr.html  # OCR interface
│   ├── target_prediction.html # Target prediction
│   └── visualize_kg.html     # Knowledge graph viewer
│
├── static/                    # Static assets
│   ├── js/                   # JavaScript files
│   │   └── viewer.js         # 3D viewer logic
│   ├── uploads/              # Uploaded files (gitignored)
│   └── processed/            # Processed files (gitignored)
│
├── data/                      # Data files (gitignored)
│   ├── cleaned_clinical_drugs_dataset.csv
│   ├── kg_triples_cleaned.csv
│   └── ...
│
├── chembl_service.py          # ChEMBL API integration
├── drug_lookup_service.py     # Multi-source drug lookup
├── prescription_routes.py     # Prescription OCR routes
└── rag_engine.py             # RAG engine for AI insights
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Required API Keys
GROQ_API_KEY=your_groq_api_key          # For AI chatbot
SERPER_API_KEY=your_serper_api_key      # For web search
GEMINI_API_KEY=your_gemini_api_key      # For OCR

# Optional Configuration
FLASK_ENV=development
DEBUG=True
USE_TMP_FOR_KG=false
```

### API Key Setup

#### 1. Groq API (Free Tier Available)

- Visit https://console.groq.com/
- Create account and generate API key
- Used for: AI Copilot responses

#### 2. Serper API (Free: 2,500 searches/month)

- Visit https://serper.dev/
- Sign up with Google
- Used for: External research retrieval (RAG)

#### 3. Google Gemini API (Free Tier Available)

- Visit https://makersuite.google.com/app/apikey
- Generate API key
- Used for: Prescription OCR, Vision tasks

---

## 🎯 Usage Examples

### 1. Search and Visualize a Drug

```python
# Via Web Interface
1. Go to http://localhost:5000
2. Select "Drug Visualizer" tab
3. Search for "Aspirin" or enter SMILES
4. View 3D structure and properties
```

### 2. Compare Two Drugs

```python
# Via Web Interface
1. Go to http://localhost:5000
2. Select "Drug Comparator" tab
3. Enter two drug names (e.g., "Aspirin" vs "Ibuprofen")
4. Click "Compare Drugs"
5. View side-by-side comparison with AI insights
```

### 3. OCR Prescription

```python
# Via Web Interface
1. Go to http://localhost:5000/prescription-ocr
2. Upload prescription image
3. View extracted medications and interactions
```

### 4. Chat with AI Copilot

```python
# Via Web Interface
1. Go to http://localhost:5000/drug-copilot
2. Ask questions like:
   - "What are the side effects of metformin?"
   - "Explain how statins work"
   - "Compare ACE inhibitors and ARBs"
```

---

## 🔌 API Endpoints

### Drug Search

```bash
GET /api/search_drug?query=aspirin
```

### Drug Information

```bash
GET /api/drug/aspirin
```

### Compare Drugs

```bash
GET /api/compare_drugs?drug1=aspirin&drug2=ibuprofen
```

### Target Prediction

```bash
POST /api/predict_target
Content-Type: application/json

{
  "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O"
}
```

### AI Copilot

```bash
POST /api/drug_copilot
Content-Type: application/json

{
  "query": "What are the mechanisms of aspirin?",
  "humanize": true
}
```

### Prescription OCR

```bash
POST /api/prescription/upload
Content-Type: multipart/form-data

prescription_image: [file]
```

---

## 🧪 Testing

```bash
# Test drug lookup
curl http://localhost:5000/api/search_drug?query=aspirin

# Test comparison
curl http://localhost:5000/api/compare_drugs?drug1=aspirin&drug2=ibuprofen

# Test AI Copilot
curl -X POST http://localhost:5000/api/drug_copilot \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain ACE inhibitors"}'
```

---

## 📊 Data Sources

MediMatch integrates multiple authoritative drug databases:

- **Local Database**: Curated clinical drugs dataset (~2,000 drugs)
- **ChEMBL**: Bioactivity database (~2M compounds)
- **PubChem**: Chemical database (110M+ compounds)
- **DrugCentral**: FDA-approved drugs with mechanisms
- **RxNorm**: Drug name normalization (NLM)

---

## 🛠️ Technology Stack

### Backend

- **Flask 3.0**: Web framework
- **RDKit**: Cheminformatics and molecular operations
- **Pandas**: Data manipulation
- **NetworkX + PyVis**: Graph visualization

### AI/ML

- **Groq Llama 3.3**: Large language model
- **Google Gemini**: Vision and OCR
- **Sentence Transformers**: Embeddings
- **FAISS**: Vector similarity search

### Frontend

- **Bootstrap 5**: UI framework
- **3Dmol.js**: 3D molecular visualization
- **JavaScript**: Interactive features

### APIs

- **ChEMBL REST API**: Drug bioactivity
- **PubChem REST API**: Chemical structures
- **DrugCentral API**: Drug mechanisms
- **RxNorm API**: Drug name normalization
- **Serper API**: Web search for RAG

---

## ⚠️ Known Limitations

1. **Dataset Size**: Local database contains ~2,000 drugs. Falls back to external APIs for missing drugs.
2. **Rate Limits**: External APIs have rate limits (especially free tiers).
3. **OCR Accuracy**: Prescription OCR works best with clear, high-quality images.
4. **Model Dependencies**: Some models are large and require good internet for first-time downloads.

---

## 🚧 Future Enhancements

- [ ] Expand local drug database to 10,000+ compounds
- [ ] Add drug-drug interaction database
- [ ] Implement ADMET prediction models
- [ ] Add batch processing for multiple molecules
- [ ] Integrate more knowledge graphs (DrugBank, KEGG)
- [ ] Add user authentication and saved searches
- [ ] Deploy to cloud (AWS/GCP/Azure)
- [ ] Mobile-responsive redesign

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add docstrings to all functions
- Write unit tests for new features
- Update documentation

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors

- **Your Name** - *Initial work* - [YourGitHub](https://github.com/yourusername)

---

## 🙏 Acknowledgments

- ChEMBL team for bioactivity data
- PubChem for chemical structures
- RDKit developers for cheminformatics tools
- Groq for fast LLM inference
- Google for Gemini API
- All contributors and users!

---

## 📧 Contact

For questions, issues, or collaboration:

- **Email**: your.email@example.com
- **GitHub Issues**: https://github.com/yourusername/medimatch/issues
- **Twitter**: @yourhandle

---

## 📚 Citation

If you use MediMatch in your research, please cite:

```bibtex
@software{medimatch2025,
  author = {Your Name},
  title = {MediMatch: AI-Powered Drug Discovery Platform},
  year = {2025},
  url = {https://github.com/yourusername/medimatch}
}
```

---

<div align="center">
  <strong>Made with ❤️ for drug discovery and healthcare</strong>
  <br>
  <sub>Star ⭐ this repo if you find it useful!</sub>
</div>

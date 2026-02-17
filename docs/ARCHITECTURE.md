# MediMatch AI+ Architecture

## Visual Architecture Diagram
![MediMatch Architecture](architecture_diagram.png)

## Mermaid Architecture Code

```mermaid
flowchart TB
    subgraph Frontend["🖥️ Frontend Layer"]
        Browser["Web Browser"]
        Templates["HTML/Jinja2 Templates"]
        CSS["Bootstrap 5 CSS"]
        JS["JavaScript (viewer.js)"]
        ThreeDmol["3Dmol.js<br/>3D Molecules"]
        ChartJS["Chart.js<br/>Analytics"]
    end

    subgraph Flask["⚙️ Application Layer (Flask)"]
        App["Flask Application<br/>(app.py)"]
        
        subgraph Routes["API Routes"]
            R1["/ - Dashboard"]
            R2["/drug-copilot - AI Chat"]
            R3["/api/drugs - Drug List"]
            R4["/api/compare - Compare"]
            R5["/prescription-ocr - OCR"]
        end

        subgraph Services["Backend Services"]
            RAG["RAG Engine<br/>(rag_engine.py)"]
            Lookup["Drug Lookup<br/>(drug_lookup_service.py)"]
            ChEMBL["ChEMBL Service<br/>(chembl_service.py)"]
            OCR["Prescription OCR<br/>(prescription_routes.py)"]
            Models["SQLAlchemy Models<br/>(models.py)"]
        end
    end

    subgraph Data["🗄️ Data Layer"]
        SQLite[("SQLite Database<br/>Users, Prescriptions,<br/>SavedDrugs")]
        FAISS[("FAISS Vector Index<br/>Semantic Search")]
        KG[("Knowledge Graph<br/>Drug Relationships")]
    end

    subgraph External["☁️ External APIs"]
        Groq["Groq (Llama 3.3)<br/>LLM Generation"]
        Gemini["Google Gemini<br/>Vision OCR"]
        ChEMBLAPI["ChEMBL API<br/>Drug Data"]
        PubChem["PubChem API<br/>Chemical Data"]
        Serper["Serper API<br/>Web Search"]
    end

    %% Frontend connections
    Browser --> Templates
    Templates --> CSS
    Templates --> JS
    JS --> ThreeDmol
    JS --> ChartJS

    %% Frontend to Backend
    Browser -->|HTTP Requests| App
    App --> Routes

    %% Backend services connections
    Routes --> RAG
    Routes --> Lookup
    Routes --> ChEMBL
    Routes --> OCR
    Routes --> Models

    %% Data layer connections
    Models -->|ORM| SQLite
    RAG -->|Vector Search| FAISS
    RAG -->|Triple Retrieval| KG

    %% External API connections
    RAG -->|LLM Queries| Groq
    OCR -->|Image Analysis| Gemini
    ChEMBL -->|Drug Lookup| ChEMBLAPI
    Lookup -->|Chemical Data| PubChem
    RAG -->|Web RAG| Serper

    %% Styling
    classDef frontend fill:#4CAF50,stroke:#2E7D32,color:white
    classDef backend fill:#009688,stroke:#00695C,color:white
    classDef data fill:#FF9800,stroke:#E65100,color:white
    classDef external fill:#9C27B0,stroke:#6A1B9A,color:white

    class Browser,Templates,CSS,JS,ThreeDmol,ChartJS frontend
    class App,R1,R2,R3,R4,R5,RAG,Lookup,ChEMBL,OCR,Models backend
    class SQLite,FAISS,KG data
    class Groq,Gemini,ChEMBLAPI,PubChem,Serper external
```

## Component Descriptions

| Component | File | Purpose |
|-----------|------|---------|
| **Flask App** | `app.py` | Main application with 25+ routes |
| **RAG Engine** | `rag_engine.py` | Web search + LLM synthesis for drug insights |
| **Drug Lookup** | `drug_lookup_service.py` | Multi-source drug data aggregation |
| **ChEMBL Service** | `chembl_service.py` | ChEMBL API integration for drug properties |
| **OCR Routes** | `prescription_routes.py` | Prescription digitization with Gemini Vision |
| **Models** | `models.py` | SQLAlchemy ORM for User, Drug, Prescription |

## Data Flow

1. **User Request** → Browser sends HTTP request to Flask
2. **Route Handler** → Flask routes to appropriate service
3. **Service Logic** → Service queries data layer or external APIs
4. **RAG Pipeline** → For AI queries: FAISS retrieval → LLM generation
5. **Response** → JSON/HTML returned to frontend
6. **Rendering** → JavaScript updates DOM with 3D molecules, charts

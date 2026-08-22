# 🚀 AI Resume Analyzer & Interview Simulator

> An AI-powered Resume Analysis and Intelligent Interview Simulation platform developed as a Final Year B.Tech Project.

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-black)
![React](https://img.shields.io/badge/React-19-blue)
![MySQL](https://img.shields.io/badge/MySQL-8-orange)
![Transformers](https://img.shields.io/badge/HuggingFace-Transformers-yellow)
![License](https://img.shields.io/badge/License-MIT-green)

---

# 📖 Overview

The AI Resume Analyzer & Interview Simulator is an intelligent recruitment assistance platform that analyzes resumes using Natural Language Processing (NLP), maps candidates to suitable job roles, generates personalized interview questions, evaluates candidate responses using semantic similarity, and provides actionable feedback for skill improvement.

The system leverages modern NLP techniques including Sentence Transformers, spaCy, and a fine-tuned FLAN-T5 model to deliver an end-to-end AI-driven interview experience.

---

# ✨ Key Features

## Resume Analysis

- Upload Resume (PDF/DOCX)
- Automatic Resume Parsing
- Skill Extraction
- Education Detection
- Experience Extraction
- Project Identification
- Resume Summary Generation

---

## AI Job Role Mapping

- Semantic Resume Matching
- Intelligent Role Recommendation
- Skill Gap Detection
- Candidate Profile Analysis

---

## AI Interview Simulator

- Dynamic Interview Sessions
- AI-generated Technical Questions
- Adaptive Question Generation
- Domain-specific Interviews
- Multiple Job Roles

---

## AI Answer Evaluation

- Semantic Similarity Evaluation
- Answer Quality Scoring
- Keyword Coverage
- Technical Accuracy Assessment
- Personalized Feedback
- Improvement Suggestions

---

## Feedback Dashboard

- Overall Interview Score
- Per-question Evaluation
- Strength Analysis
- Weakness Detection
- Recommended Learning Areas

---

# 🧠 AI Technologies Used

| Component | Technology |
|------------|------------|
| Resume Parsing | spaCy |
| Semantic Similarity | Sentence Transformers (MiniLM) |
| Question Generation | Fine-tuned FLAN-T5 |
| NLP | HuggingFace Transformers |
| LoRA Fine-Tuning | PEFT |
| Embeddings | SentenceTransformer |
| Text Processing | pdfplumber, python-docx |

---

# 🏗️ System Architecture

```
                    Resume Upload
                          │
                          ▼
                Resume Parsing Module
                          │
                          ▼
               Skill Extraction (spaCy)
                          │
                          ▼
              Job Role Recommendation
                          │
                          ▼
          AI Interview Question Generator
                (Fine-tuned FLAN-T5)
                          │
                          ▼
             Candidate Answers Submission
                          │
                          ▼
         Semantic Evaluation (MiniLM)
                          │
                          ▼
              AI Feedback Generation
                          │
                          ▼
                 Final Performance Report
```

---

# 🛠️ Tech Stack

## Frontend

- React 19
- Vite
- Axios
- CSS

## Backend

- Flask
- Flask SQLAlchemy
- Flask Migrate
- Flask CORS

## Database

- MySQL

## AI / NLP

- spaCy
- Transformers
- Sentence Transformers
- PEFT (LoRA)
- FLAN-T5

## File Processing

- pdfplumber
- python-docx

---

# 📂 Project Structure

```
AI-Resume-Analyzer/
│
├── backend/
│   ├── app/
│   │   ├── controllers/
│   │   ├── models/
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   └── config.py
│   │
│   ├── migrations/
│   ├── tests/
│   ├── uploads/
│   ├── run.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

---

# ⚙️ Installation

## Clone Repository

```bash
git clone https://github.com/yourusername/AI-Resume-Analyzer.git

cd AI-Resume-Analyzer
```

---

## Backend Setup

```bash
cd backend

python -m venv venv

source venv/bin/activate

# Windows

venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file.

Example:

```env
FLASK_ENV=development

SECRET_KEY=your_secret_key

DATABASE_URL=mysql+pymysql://username:password@localhost/database_name
```

Run database migrations

```bash
flask db upgrade
```

Start Backend

```bash
python run.py
```

---

## Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

---

# 🔄 Workflow

1. Upload Resume
2. Resume Parsing
3. Skill Extraction
4. Role Recommendation
5. AI Interview Generation
6. Candidate Answers
7. Semantic Evaluation
8. Personalized Feedback
9. Final Report

---

# 🧪 Testing

Run backend tests

```bash
pytest
```

---

# 📈 Future Enhancements

- Voice-based Interview
- Video Interview Analysis
- ATS Score Prediction
- Resume Ranking
- Company-specific Interview Sets
- AI Career Roadmap
- Emotion Detection
- Multilingual Interview Support
- Recruiter Dashboard
- Cloud Deployment (AWS/Azure)

---

# 🎯 Learning Outcomes

This project demonstrates practical implementation of:

- Full Stack Development
- REST API Design
- NLP
- Generative AI
- Semantic Search
- Transformer Models
- Fine-tuning using LoRA
- Database Design
- Model Integration
- Software Architecture

---

# 👨‍💻 Author

**Siddharth Srivastava**

Bachelor of Technology (B.Tech)

Artificial Intelligence | Machine Learning | Full Stack Development | NLP

---
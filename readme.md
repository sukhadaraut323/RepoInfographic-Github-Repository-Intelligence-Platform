# RepoInfographic – AI-Powered GitHub Repository Intelligence Platform

RepoInfographic is an AI-powered GitHub repository analysis platform that transforms repository data into meaningful engineering insights, interactive visualizations, and downloadable PDF reports.

It analyzes repository structure, engineering metrics, Git history, dependencies, architecture, and workflows. It also uses **Ollama** to generate detailed, repository-specific AI insights.

---

## Features

### 1. GitHub Repository Analysis
- Analyze public GitHub repositories using their repository URLs.
- Retrieve repository metadata, including stars, forks, open issues, language, license, and visibility.
- Clone repositories for deeper analysis.
- Inspect repository structure and directory organization.

### 2. Engineering Metrics
- Repository health score.
- Documentation analysis.
- Codebase analysis.
- Development activity analysis.
- Community health analysis.
- Maintainability assessment.
- Best-practices evaluation.

### 3. Git History Analysis
- Commit history analysis.
- Contributor activity.
- Development activity trends.
- Commit timeline visualization.
- Repository evolution insights.

### 4. Advanced Visualizations
- Dynamic architecture diagrams.
- Dependency graph visualization.
- Repository workflow diagrams.
- Technology and language distribution.
- Interactive engineering visualizations.

### 5. AI-Powered Insights

RepoInfographic integrates Ollama to generate repository-specific engineering insights.

The AI Insights module includes eight sections:

1. **Repository Summary** – Detailed explanation of the repository's purpose, structure, and technologies.
2. **Architecture Explanation** – Analysis of architecture and relationships between components.
3. **Contribution Guide** – Guidance for developers who want to contribute.
4. **Project Evolution** – Suggested development stages and future project direction.
5. **Learning Roadmap** – A structured roadmap for understanding and improving the project's technologies.
6. **Suggested Commits** – Potential meaningful improvements that can be implemented.
7. **Improvement Suggestions** – Prioritized recommendations for improving the repository.
8. **README Review** – Evaluation of existing project documentation and suggested improvements.

AI-generated insights use repository evidence and the locally configured Ollama model.

### 6. PDF Report Generation
Generate and download a compact PDF report containing:

- Engineering metrics.
- Advanced visualizations.
- AI engineering insights.

The report is designed to present the most useful engineering information without unnecessarily including lengthy commit-history inventories.

---

## Technology Stack

|       Component        |                     Technologies                    |
|------------------------|-----------------------------------------------------|
|          Frontend      |             React, Vite, Tailwind CSS               |
|          Backend       |                     Python, FastAPI                 |
|    AI Integration      |                         Ollama                      |
|    Default AI Model    |                      Qwen 2.5 7B                    |
| Repository Integration |               GitHub REST API, GitPython            |
|     Visualization      | Recharts, custom architecture and workflow diagrams |
|    PDF Generation      |                        ReportLab                    |
|        Testing         |                     Pytest, Vitest                  |

---

## Project Structure

```text
RepoInfographic/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   ├── core/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── tests/
│   │   └── main.py
│   │
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── __tests__/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

---

## Prerequisites

Install the following before running the application:

- Python 3.10 or later.
- Node.js and npm.
- Git.
- Ollama.
- A GitHub Personal Access Token.

---

## Installation and Setup

### Step 1: Clone the repository

```bash
git clone YOUR_REPOSITORY_URL
cd RepoInfographic
```

Alternatively, extract the downloaded project ZIP and open its root directory.

### Step 2: Set up the backend

Navigate to the backend directory:

```powershell
cd backend
```

Create a Python virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

### Step 3: Configure environment variables

Create a `.env` file inside the `backend` directory by copying `.env.example`.

```powershell
Copy-Item .env.example .env
```

Open `backend/.env` and configure:

```env
# GitHub Configuration
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_API_BASE_URL=https://api.github.com

# Application Configuration
LOG_LEVEL=INFO
WORKSPACE_DIRECTORY=./workspace

# AI Configuration
AI_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT_SECONDS=300
OLLAMA_TOTAL_TIMEOUT_SECONDS=900
OLLAMA_NUM_CTX=8192
OLLAMA_NUM_PREDICT=6000
OLLAMA_TEMPERATURE=0.2
```

**Important:**
- Replace the GitHub token placeholder with your actual token.
- Make sure the configured Ollama model is installed.
- Never upload your actual `.env` file or GitHub token to GitHub.

### Step 4: Install and configure Ollama

Download Ollama:

https://ollama.com/download

Pull the default model:

```powershell
ollama pull qwen2.5:7b
```

Check installed models:

```powershell
ollama list
```

Verify Ollama is responding:

```powershell
ollama run qwen2.5:7b
```

Ollama should be running locally before repository analysis begins.

### Step 5: Start the backend

From the `backend` directory, with the virtual environment activated:

```powershell
python -m uvicorn app.main:app --reload
```

Backend address:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
http://127.0.0.1:8000/health
```

### Step 6: Start the frontend

Open another terminal and navigate to the frontend directory:

```powershell
cd frontend
```

Install frontend dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

Open the application:

```text
http://localhost:5173
```

---

## How to Use RepoInfographic

1. Open the application in your browser.
2. Enter a valid public GitHub repository URL.
3. Click **Analyze Repository**.
4. Wait for repository cloning and analysis to finish.
5. Explore the dashboard.

The dashboard provides the following sections:

- Overview
- Engineering Metrics
- Git History
- Analytics
- Advanced Visualizations
- AI Insights

To generate a PDF, click **Download Repository Report (PDF)**.

---

## AI Insights Configuration

RepoInfographic uses Ollama for local AI generation.

Default configuration:

| Setting | Default |
|---|---|
| AI Enabled | true |
| Ollama URL | http://localhost:11434 |
| Model | qwen2.5:7b |
| Context Window | 8192 |
| Maximum Generated Tokens | 6000 |
| Temperature | 0.2 |
| Request Timeout | 300 seconds |
| Total Generation Timeout | 900 seconds |

The AI system uses repository analysis evidence to generate engineering explanations and recommendations.

If AI Insights are unavailable:

1. Check whether Ollama is running.
2. Run `ollama list` to verify the model is installed.
3. Verify `OLLAMA_MODEL` in `backend/.env`.
4. Check that `AI_ENABLED=true`.
5. Verify that `OLLAMA_NUM_PREDICT` is sufficiently high.
6. Restart the backend after changing environment variables.
7. Analyze the repository again.

---

## API Endpoints

The backend exposes its API under `/api/v1`.

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Backend health check |
| `/api/v1/dashboard/analyze` | POST | Analyze a GitHub repository |
| `/api/v1/dashboard/report` | POST | Generate a PDF report |

For the complete API documentation, visit:

`http://127.0.0.1:8000/docs`

---

## Running Tests

### Backend tests

From the backend directory:

```powershell
python -m pytest app/tests -v
```

Run a specific report-generation test:

```powershell
python -m pytest app/tests/test_report_generation_service.py -v
```

### Frontend tests

From the frontend directory:

```powershell
npm test
```

### Frontend production build

```powershell
npm run build
```

---

## Troubleshooting

### 1. GitHub Authentication Error

**Possible cause:** Missing or invalid GitHub token.

**Solution:** Check `GITHUB_TOKEN` in `backend/.env`.

### 2. Ollama Connection Error

**Possible cause:** Ollama is not running.

**Solution:**

```powershell
ollama list
```

Ensure Ollama is running and the configured model is installed.

### 3. AI Insights Unavailable

**Possible cause:** Invalid model response, insufficient generation tokens, or an Ollama timeout.

**Solution:**
- Verify the model configuration.
- Increase `OLLAMA_NUM_PREDICT` if responses are truncated.
- Check backend logs.
- Restart Ollama and the backend.
- Run repository analysis again.

### 4. Missing Python Dependencies

Install backend dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

### 5. Frontend Cannot Reach Backend

Ensure the backend is running on port `8000`.

The Vite development server proxies `/api` requests to:

```text
http://127.0.0.1:8000
```

---

## Security

- Keep GitHub tokens in environment variables.
- Do not commit `.env` files.
- Do not expose private credentials in frontend code.
- Use appropriate GitHub token permissions.
- Keep local repository workspace files out of version control.

---

## Future Scope

Potential future enhancements include:

- Deeper semantic code analysis.
- More detailed architecture recommendations.
- Additional programming-language support.
- Improved repository comparison.
- Historical engineering-health tracking.
- More advanced AI-generated development roadmaps.

---

## Project Goal

RepoInfographic aims to make GitHub repository analysis more understandable, visual, and actionable.

By combining repository analytics, engineering metrics, advanced visualizations, and locally generated AI insights, it helps developers understand codebases, identify improvement opportunities, and make better engineering decisions.

---

**RepoInfographic – Understand Your Repository. Visualize Its Architecture. Improve Its Engineering Quality.**
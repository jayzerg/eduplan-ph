# EduPlan PH

**AI-Enhanced Lesson Plan Generator for Philippine K-12 Educators**

![Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit)
![LangChain](https://img.shields.io/badge/AI-LangChain-4CAF50)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python)
![License](https://img.shields.io/badge/License-MIT-green)

## Overview

EduPlan PH is a web application that generates DepEd-aligned lesson plans and quizzes in seconds. Built for Philippine K-12 educators who spend too much time on administrative paperwork and not enough time on what matters — teaching.

### The Problem
- Teachers spend 5-8 hours per week creating lesson plans manually.
- Existing tools are not localized to the Philippine curriculum.
- DepEd's DLP format has specific structural requirements that generic AI tools don't follow.

### The Solution
EduPlan PH uses AI to generate complete, submission-ready lesson plans that:
- Follow the exact DepEd Detailed Lesson Plan (DLP) format.
- Support English, Filipino, and Taglish output.
- Include objectives, procedures, assessments, and quizzes with answer keys.
- Export to Word (.docx) and PDF formats.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend/UI | Streamlit |
| AI Engine | LangChain + OpenRouter |
| Document Export | python-docx, FPDF2 |
| Data Handling | Pandas |
| Deployment | Streamlit Cloud |

## Installation

### Option 1: Docker (Recommended)

#### Prerequisites
- Docker and Docker Compose installed on your system
- An OpenRouter API key (free at [openrouter.ai/keys](https://openrouter.ai/keys))

#### Quick Start with Docker

```bash
# Clone the repository
git clone https://github.com/yourusername/eduplan-ph.git
cd eduplan-ph

# Copy environment template and configure API key
cp .env.template .env
# Edit .env and add your OPENROUTER_API_KEY

# Build and run with Docker Compose
docker compose up --build -d

# View logs
docker compose logs -f

# Access the application at http://localhost:8501
```

#### Docker Commands Reference

```bash
# Start the application
docker compose up -d

# Stop the application
docker compose down

# Rebuild after code changes
docker compose up --build -d

# View logs
docker compose logs -f

# Access container shell for debugging
docker compose exec eduplan-ph /bin/bash

# Clean up volumes (removes cached data)
docker compose down -v
```

**Data Persistence:** The SQLite cache is stored in a Docker volume (`eduplan_cache_data`) to persist across container restarts. To reset the cache, run `docker compose down -v`.

For detailed Docker setup instructions, see [docs/DOCKER_SETUP.md](docs/DOCKER_SETUP.md).

---

### Option 2: Manual Installation

#### Prerequisites
- Python 3.8 or higher
- An OpenRouter API key (free at [openrouter.ai/keys](https://openrouter.ai/keys))

#### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/eduplan-ph.git
cd eduplan-ph

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.template .env
# Edit .env and add your OPENROUTER_API_KEY

# Run the application
streamlit run app.py
```

## Usage

1. Open the application in your browser (default: http://localhost:8501).
2. Select your **Grade Level**, **Subject**, and **Output Language** from the sidebar.
3. Enter the **Topic** you want to create a lesson plan for.
4. Click **Generate Lesson Plan**.
5. Review the generated content, then download as Word or PDF.

## Project Structure

```
eduplan-ph/
├── app.py                  # Main Streamlit application
├── src/
│   ├── generator.py        # AI chain and LLM logic
│   ├── prompts.py          # Prompt templates
│   ├── config.py           # Application constants
│   ├── utils.py            # Export functions
│   └── validators.py       # Input validation
├── assets/                 # Images and static resources
├── tests/                  # Unit tests
├── docs/                   # Documentation
│   └── DOCKER_SETUP.md     # Detailed Docker setup guide
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker container configuration
├── docker-compose.yml      # Docker Compose orchestration
├── .dockerignore           # Files to exclude from Docker build
├── .env.template           # Environment variables template
└── README.md               # This file
```

## Contributing

Contributions are welcome! Please see the Issues tab for current feature requests and bug reports.

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Department of Education (DepEd)** — For the DLP format guidelines that shaped this tool's output structure.
- **OpenRouter** — For providing access to multiple free AI models.
- **Streamlit** — For making Python-based web apps accessible to all developers.
- **Philippine Educators** — The inspiration and primary beneficiaries of this project.
# LinkedIn Profile Optimizer

A Multi-Agent System powered by AI that optimizes LinkedIn profiles and generates content ideas based on uploaded profile PDFs.

## 🚀 Quick Start

1. **Setup Backend**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   python main.py
   ```

2. **Setup Frontend** (in a new terminal):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Use the Application**:
   - Open `http://localhost:3000`
   - Upload your LinkedIn profile PDF
   - Get optimization recommendations and content ideas!

## 🚀 Features

- **PDF Profile Analysis**: Extract and analyze LinkedIn profile data from exported PDFs
- **AI-Powered Optimization**: Get personalized recommendations for profile improvement
- **Content Generation**: Receive tailored LinkedIn post ideas and content strategy
- **Multi-Agent Architecture**: Three specialized AI agents working together:
  - **Profile Collector Agent**: Extracts structured data from PDF files
  - **Profile Analyzer Agent**: Analyzes profiles and identifies optimization opportunities
  - **Content Generator Agent**: Creates engaging LinkedIn content ideas and posts

## 🏗 Architecture

### Tech Stack

- **Backend**: Python with FastAPI
- **Frontend**: Next.js with TypeScript and Tailwind CSS
- **AI Framework**: LangGraph for multi-agent orchestration
- **LLM**: OpenAI GPT-4 (configurable)
- **PDF Processing**: PyMuPDF for text extraction
- **State Management**: LangGraph with MemorySaver

### Project Structure

```
linkedin-profile-optimizer/
├── backend/
│   ├── agents/
│   │   ├── profile_collector.py    # PDF parsing and data extraction
│   │   ├── profile_analyzer.py     # Profile analysis and recommendations
│   │   └── content_generator.py    # Content ideas and post generation
│   ├── workflows/
│   │   └── linkedin_optimizer_workflow.py  # LangGraph orchestration
│   ├── utils/
│   │   ├── pdf_parser.py          # PDF processing utilities
│   │   └── prompt_loader.py       # YAML prompt management
│   ├── config.py                  # Configuration management
│   ├── prompts.yaml               # All agent prompts
│   ├── main.py                    # FastAPI application
│   ├── requirements.txt           # Python dependencies
│   └── .env.example               # Environment variables template
├── frontend/
│   ├── src/
│   │   ├── app/                   # Next.js app directory
│   │   ├── components/            # React components
│   │   ├── lib/                   # Utility functions
│   │   └── types/                 # TypeScript types
│   ├── package.json               # Node.js dependencies
│   └── next.config.js             # Next.js configuration
└── README.md
```

## 🛠 Detailed Setup

### Prerequisites

- Python 3.10
- Node.js 18+
- OpenAI API key

### Backend Setup

The backend runs on FastAPI and provides the AI-powered optimization API.

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your OpenAI API key
python main.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup

The frontend is a Next.js application that provides the user interface.

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000`

## 📝 Usage

### How to Export Your LinkedIn Profile as PDF

1. Go to your LinkedIn profile page
2. Click the "More" button (three dots)
3. Select "Save to PDF"
4. Download the PDF file

### Using the Application

1. Open `http://localhost:3000` in your browser
2. Upload your LinkedIn profile PDF
3. (Optional) Specify a target role/industry for personalized recommendations
4. Click "Optimize My LinkedIn Profile"
5. Review the results in the comprehensive dashboard

## 🤖 Agent Details

### Profile Collector Agent (`profile_collector.py`)

**Purpose**: Extracts structured information from LinkedIn profile PDFs

**Capabilities**:
- PDF text extraction using PyMuPDF
- Structured data parsing with LLM
- Validation and data cleaning

**Output**: Structured JSON with profile sections:
- Personal information
- Professional summary
- Work experience
- Education
- Skills and endorsements
- Recommendations
- Languages and volunteer work

### Profile Analyzer Agent (`profile_analyzer.py`)

**Purpose**: Analyzes profile data and provides optimization recommendations

**Capabilities**:
- Profile completeness assessment
- Industry-specific keyword analysis
- ATS optimization suggestions
- Professional branding recommendations

**Output**:
- Overall profile score (0-100)
- Strengths and improvement areas
- Specific recommendations for headline, summary, and experience
- Skills and certification suggestions
- Next steps for optimization

### Content Generator Agent (`content_generator.py`)

**Purpose**: Creates engaging LinkedIn content based on profile analysis

**Capabilities**:
- Content strategy development
- Post ideas generation
- Sample post creation
- Weekly content calendar

**Output**:
- Content strategy with posting frequency and optimal times
- Multiple content ideas with different formats (posts, articles, polls)
- Sample posts ready to publish
- Weekly content calendar

## 📊 API Endpoints

### Main Endpoints

- `POST /optimize-profile` - Complete profile optimization workflow
- `POST /analyze-profile` - Profile analysis only
- `POST /generate-content` - Content generation only
- `GET /health` - Health check

## ⚙️ Configuration

### Prompts Configuration

All agent prompts are stored in `backend/prompts.yaml` for easy modification:

```yaml
profile_collector:
  system_prompt: |
    You are a LinkedIn Profile Collector Agent...
  user_prompt: |
    Please extract all relevant LinkedIn profile information...

profile_analyzer:
  system_prompt: |
    You are a LinkedIn Profile Analyzer Agent...
  user_prompt: |
    Please analyze the following LinkedIn profile data...

content_generator:
  system_prompt: |
    You are a LinkedIn Content Generator Agent...
  user_prompt: |
    Based on the following profile analysis...
```

### Environment Variables

Backend (`.env`):
```
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional (with defaults)
OPENAI_MODEL=gpt-4o
HOST=0.0.0.0
PORT=8000
DEBUG=false
MAX_FILE_SIZE=10485760
DEFAULT_TEMPERATURE=0.3
MAX_TOKENS=4000
ALLOWED_ORIGINS=http://localhost:3000
```

Frontend:
```
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

## 🧪 Testing

### Backend Testing

```bash
cd backend
python -m pytest tests/ -v
```

### Frontend Testing

```bash
cd frontend
npm test
```

### Integration Testing

1. Start both backend and frontend servers
2. Upload a sample LinkedIn profile PDF
3. Verify complete workflow execution
4. Check all agent outputs and UI components

## ⚙️ Configuration

The application uses environment variables for configuration. All settings can be customized by editing the `.env` file in the backend directory.

### Configuration Options

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | - | ✅ Yes |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o` | No |
| `HOST` | Server host address | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |
| `DEBUG` | Enable debug mode | `false` | No |
| `MAX_FILE_SIZE` | Max upload size in bytes | `10485760` (10MB) | No |
| `DEFAULT_TEMPERATURE` | LLM temperature | `0.3` | No |
| `MAX_TOKENS` | Max tokens per request | `4000` | No |
| `ALLOWED_ORIGINS` | CORS allowed origins | `http://localhost:3000` | No |

### Model-Specific Temperatures

The system automatically adjusts temperature for different agents:
- **Profile Collector**: Uses `DEFAULT_TEMPERATURE` (precise extraction)
- **Profile Analyzer**: Uses `DEFAULT_TEMPERATURE + 0.1` (balanced analysis)
- **Content Generator**: Uses `DEFAULT_TEMPERATURE + 0.4` (creative content)

### Configuration Validation

The application validates configuration on startup and will show helpful error messages if required settings are missing or invalid.

## 🔧 Development

### Adding New Agent Capabilities

1. Extend agent classes in the respective files
2. Update prompts in `prompts.yaml`
3. Modify workflow if needed in `linkedin_optimizer_workflow.py`
4. Update frontend types and components as necessary

### Customizing Prompts

Edit `backend/prompts.yaml` to customize:
- Agent personalities and expertise
- Output formats and requirements
- Industry-specific knowledge
- Analysis criteria and scoring

## 🚀 Deployment

### Backend Deployment

```bash
# Using Docker
docker build -t linkedin-optimizer-backend .
docker run -p 8000:8000 linkedin-optimizer-backend

# Using Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Frontend Deployment

```bash
npm run build
npm start
```

## 📈 Performance

- **Processing Time**: 30-60 seconds per profile optimization
- **File Size Limit**: 10MB for PDF uploads
- **Concurrent Requests**: Supports multiple simultaneous optimizations
- **Rate Limiting**: Configurable based on OpenAI API limits

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License. 
See `LICENSE` file for details. 

## 🆘 Support

For issues and questions:
1. Check the existing GitHub issues
2. Create a new issue with detailed description
3. Include error logs and steps to reproduce


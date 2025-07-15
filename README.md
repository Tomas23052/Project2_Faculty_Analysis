# IPT Faculty Performance Assessment System

An automated data collection and analysis system for IPT (Instituto Politécnico de Tomar) faculty performance assessment. This system integrates multiple data sources including HR documents, web scraping, and research metrics to provide comprehensive faculty analytics through an interactive Streamlit dashboard.

## 🎯 Overview

This system provides:
- **Automated Web Scraping**: Extracts faculty profiles from IPT's "Quem é Quem" website
- **PDF Data Extraction**: Parses HR documents to extract basic faculty information  
- **Research Metrics Integration**: Collects data from ORCID, Google Scholar, and other academic sources
- **Interactive Dashboard**: Streamlit-based analytics dashboard with visualizations and insights
- **Data Integration**: Unified dataset combining multiple sources for comprehensive analysis

## 📁 Project Structure

```
p2-bigdata/
├── src/                           # Source code
│   ├── collect_all_data.py       # Main data collection pipeline
│   ├── extract_basic_info.py     # Web scraper for IPT profiles
│   ├── parse_hr_pdfs.py          # PDF parser for HR documents
│   ├── collect_research_data.py  # Research metrics collector
│   ├── advanced_dashboard.py     # Streamlit dashboard
│   └── advanced_pdf_parser.py    # Advanced PDF processing
├── data/                          # Data files
│   ├── raw/                       # Original source files (PDFs)
│   ├── faculty_enhanced_complete.csv    # Main integrated dataset
│   ├── faculty_research_metrics.csv     # Research metrics
│   ├── faculty_basic.csv               # Basic faculty info
│   └── [other data files]
├── notebooks/                     # Jupyter notebooks for analysis
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd p2-bigdata

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation (optional)
python verify_system.py
```

### 2. Prepare Data Sources

Place HR PDF files in the `data/raw/` directory:
```bash
mkdir -p data/raw
# Copy your HR PDF files to data/raw/
```

### 3. Run Data Collection Pipeline

Execute the complete data collection process:

```bash
# Run the full pipeline
python src/collect_all_data.py
```

This will:
1. Parse HR PDF files for basic faculty information
2. Scrape IPT "Quem é Quem" website for detailed profiles  
3. Collect research metrics from academic databases
4. Generate integrated datasets in the `data/` directory

### 4. Launch Dashboard

Start the interactive Streamlit dashboard:

```bash
# Launch dashboard
streamlit run src/advanced_dashboard.py
```

The dashboard will be available at `http://localhost:8501`

## 📊 Dashboard Features

The Streamlit dashboard provides:

- **Faculty Overview**: Complete faculty listing with key metrics
- **Research Analytics**: Publication counts, citations, H-index tracking
- **Department Analysis**: Cross-departmental comparisons
- **Performance Trends**: Historical analysis and trends
- **Export Capabilities**: Download filtered data and reports
- **Search & Filter**: Advanced filtering by department, position, metrics

## 🔧 Individual Components

### Web Scraping
```bash
# Scrape IPT profiles only
python src/extract_basic_info.py
```

### PDF Processing
```bash
# Parse HR PDFs only
python src/parse_hr_pdfs.py
```

### Research Data Collection
```bash
# Collect research metrics only
python src/collect_research_data.py
```

### Advanced PDF Analysis
```bash
# Advanced PDF processing with OCR
python src/advanced_pdf_parser.py --input data/raw/ --output data/
```

## 📝 Generated Data Files

The system generates several data files:

| File | Description |
|------|-------------|
| `faculty_enhanced_complete.csv` | Main integrated dataset with all sources |
| `faculty_research_metrics.csv` | Research metrics (publications, citations) |
| `faculty_basic.csv` | Basic information from HR documents |
| `faculty_advanced_parsed.csv` | Advanced parsing results |
| `faculty_profiles_robust.csv` | Web-scraped profile data |
| `faculty_clusters.csv` | Faculty clustering analysis |
| `faculty_network_metrics.csv` | Network analysis metrics |
| `faculty_scopus_metrics.csv` | Scopus-specific metrics |
| `faculty_alerts.csv` | Data quality alerts and issues |

## 🛠️ Dependencies

Key Python packages required:
- **Data Processing**: pandas, numpy
- **Web Scraping**: requests, beautifulsoup4, selenium
- **PDF Processing**: PyPDF2, pdfplumber, pytesseract
- **Dashboard**: streamlit, plotly
- **Research APIs**: scholarly (Google Scholar)
- **Analysis**: scikit-learn, networkx, statsmodels

See `requirements.txt` for complete list.

## ⚙️ Configuration

### Web Scraping Settings
- Default delay between requests: 2 seconds
- Maximum pages to scrape: configurable in scripts
- User agent rotation for anti-detection

### PDF Processing
- OCR enabled for scanned documents
- Multiple PDF libraries for robust extraction
- Error handling for corrupted files

### Research Data
- ORCID API integration
- Google Scholar automated queries
- Rate limiting to respect API limits

## 🔍 Troubleshooting

### Common Issues

**No data extracted from PDFs**
- Ensure PDF files are in `data/raw/` directory
- Check if PDFs are readable (not password protected)
- Try the advanced PDF parser for scanned documents

**Web scraping failures**
- Check internet connection
- Verify IPT website is accessible
- Adjust delay settings for rate limiting

**Dashboard errors**
- Ensure data files exist in `data/` directory
- Run data collection pipeline first
- Check Streamlit logs for specific errors

**Missing dependencies**
- Run `pip install -r requirements.txt` again
- Check Python version compatibility (3.8+)
- Install system dependencies for PDF/OCR processing

### System Requirements

- Python 3.8 or higher
- 4GB+ RAM for large datasets
- Internet connection for web scraping
- Optional: Tesseract OCR for scanned PDFs

## 📈 Performance

The system processes:
- ~300+ faculty profiles in 10-15 minutes
- HR PDF files in seconds to minutes
- Research metrics collection: varies by API response
- Dashboard loads datasets in <10 seconds

## 🤝 Contributing

1. Ensure all dependencies are installed
2. Run the full pipeline to test functionality
3. Validate dashboard loads correctly
4. Test with sample data before production use

## 📄 License

This project is for academic and institutional use at IPT.

---

For questions or support, please refer to the documentation in `WEB_SCRAPING_IMPROVEMENTS_FINAL.md` or contact the development team.

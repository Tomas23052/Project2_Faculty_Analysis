import PyPDF2
import pandas as pd
import re
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IPTHRParser:
    """
    Parser for IPT HR Division PDF files containing faculty information.
    """
    
    def __init__(self, data_dir="data/raw"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_pdf_text(self, pdf_path):
        """Extract text from PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            logger.error(f"Error reading PDF {pdf_path}: {e}")
            return ""
    
    def parse_faculty_data(self, text):
        """
        Parse faculty information from extracted text.
        This is a template that needs adjustment based on actual PDF structure.
        """
        faculty_list = []
        
        lines = text.split('\n')
        current_faculty = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Pattern for names (adjust based on actual PDF format)
            name_pattern = r'^([A-ZÁÊÇÃO][a-záêção]+\s+[A-ZÁÊÇÃO][a-záêção]+(?:\s+[A-ZÁÊÇÃO][a-záêção]+)*)'
            name_match = re.match(name_pattern, line)
            
            if name_match:
                if current_faculty:
                    faculty_list.append(current_faculty)
                current_faculty = {'name': name_match.group(1)}
            
            # Look for ORCID patterns
            orcid_match = re.search(r'(\d{4}-\d{4}-\d{4}-\d{4})', line)
            if orcid_match and current_faculty:
                current_faculty['orcid'] = orcid_match.group(1)
            
            # Look for categories (Professor, Assistant, etc.)
            category_patterns = [
                r'Professor\s+Adjunto',
                r'Professor\s+Coordenador',
                r'Assistente',
                r'Equiparado\s+a\s+Assistente'
            ]
            
            for pattern in category_patterns:
                if re.search(pattern, line, re.IGNORECASE) and current_faculty:
                    current_faculty['category'] = re.search(pattern, line, re.IGNORECASE).group(0)
                    break
            
            # Look for departments/schools
            dept_patterns = [
                r'Escola\s+Superior\s+de\s+[A-Z][a-z]+',
                r'Departamento\s+de\s+[A-Z][a-z]+',
                r'ESTT|ESGT|ESTA'
            ]
            
            for pattern in dept_patterns:
                dept_match = re.search(pattern, line, re.IGNORECASE)
                if dept_match and current_faculty:
                    current_faculty['department'] = dept_match.group(0)
                    break
        
        # Don't forget the last faculty member
        if current_faculty:
            faculty_list.append(current_faculty)
            
        return faculty_list
    
    def process_hr_files(self):
        """Process all HR PDF files in the data directory"""
        pdf_files = list(self.data_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {self.data_dir}")
            logger.info("Please download HR PDF files to data/raw/ directory")
            return pd.DataFrame()
        
        all_faculty = []
        
        for pdf_file in pdf_files:
            logger.info(f"Processing {pdf_file.name}...")
            text = self.extract_pdf_text(pdf_file)
            
            if text:
                faculty_data = self.parse_faculty_data(text)
                all_faculty.extend(faculty_data)
                logger.info(f"Extracted {len(faculty_data)} faculty members from {pdf_file.name}")
            else:
                logger.warning(f"No text extracted from {pdf_file.name}")
        
        if all_faculty:
            # Create DataFrame and save
            df = pd.DataFrame(all_faculty)
            
            # Clean up data
            df = self.clean_faculty_data(df)
            
            output_path = self.data_dir.parent / "faculty_basic.csv"
            df.to_csv(output_path, index=False, encoding='utf-8')
            
            logger.info(f"Successfully extracted {len(all_faculty)} faculty members")
            logger.info(f"Saved to {output_path}")
            
            return df
        else:
            logger.warning("No faculty data extracted")
            return pd.DataFrame()
    
    def clean_faculty_data(self, df):
        """Clean and standardize faculty data"""
        if df.empty:
            return df
        
        # Remove duplicates based on name
        df = df.drop_duplicates(subset=['name'], keep='first')
        
        # Clean names (remove extra spaces, etc.)
        if 'name' in df.columns:
            df['name'] = df['name'].str.strip()
            df['name'] = df['name'].str.replace(r'\s+', ' ', regex=True)
        
        # Standardize ORCID format
        if 'orcid' in df.columns:
            df['orcid'] = df['orcid'].str.replace(r'[^\d-]', '', regex=True)
            df.loc[df['orcid'].str.len() != 19, 'orcid'] = None
        
        # Fill missing values
        df = df.fillna('')
        
        return df

def main():
    """Main function for testing"""
    parser = IPTHRParser()
    
    # Check if PDF files exist
    pdf_files = list(parser.data_dir.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found in data/raw/")
        print("Please download IPT HR PDF files to data/raw/ directory first")
        print("URL: https://portal2.ipt.pt/pt/ipt/estrutura_organica/instituto_politecnico_de_tomar/unidades_funcionais/unidades_de_apoio/servicos_centrais/divisao_de_recursos_humanos/")
        return
    
    faculty_df = parser.process_hr_files()
    
    if not faculty_df.empty:
        print(f"\nExtracted {len(faculty_df)} faculty members:")
        print(faculty_df.head())
        print(f"\nColumns: {list(faculty_df.columns)}")
        
        # Show some statistics
        if 'orcid' in faculty_df.columns:
            orcid_count = faculty_df['orcid'].notna().sum()
            print(f"Faculty with ORCID: {orcid_count}/{len(faculty_df)} ({orcid_count/len(faculty_df)*100:.1f}%)")
        
        if 'category' in faculty_df.columns:
            print("\nFaculty categories:")
            print(faculty_df['category'].value_counts())

if __name__ == "__main__":
    main()

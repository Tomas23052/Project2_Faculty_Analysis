#!/usr/bin/env python3
"""
Advanced PDF Parser for IPT Faculty Data
Handles complex PDF layouts, tables, and multi-column text extraction
"""

import PyPDF2
import pdfplumber
import tabula
import pandas as pd
import numpy as np
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import fitz  # PyMuPDF
import camelot
from PIL import Image
import pytesseract
import cv2
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdvancedPDFParser:
    """Advanced PDF parser with multiple extraction methods and AI-enhanced processing"""
    
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialize the advanced PDF parser
        
        Args:
            tesseract_path: Path to tesseract executable (for OCR)
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        self.extraction_methods = [
            'pdfplumber',
            'pymupdf', 
            'tabula',
            'camelot',
            'ocr'
        ]
        
        # Faculty data patterns (Portuguese and English)
        self.name_patterns = [
            r'([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+(?:\s+[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][a-záàâãéêíóôõúç]+)+)',
            r'Dr\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            r'Prof\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        ]
        
        self.category_patterns = {
            'Professor Coordenador': [r'Prof\.?\s*Coord\.?', r'Professor\s+Coordenador'],
            'Professor Adjunto': [r'Prof\.?\s*Adj\.?', r'Professor\s+Adjunto'],
            'Assistente': [r'Assistente', r'Assist\.'],
            'Equiparado': [r'Equiparado'],
            'Convidado': [r'Convidado', r'Convid\.']
        }
        
        self.department_patterns = [
            r'Departamento\s+de\s+([^,\n]+)',
            r'Depart\.?\s+([^,\n]+)',
            r'Área\s+de\s+([^,\n]+)',
            r'Escola\s+de\s+([^,\n]+)'
        ]
        
    def extract_with_multiple_methods(self, pdf_path: str) -> Dict:
        """
        Extract data using multiple methods and combine results
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        results = {
            'metadata': self._extract_metadata(pdf_path),
            'text_data': {},
            'table_data': {},
            'faculty_data': [],
            'extraction_quality': {}
        }
        
        logger.info(f"Starting advanced extraction from: {pdf_path}")
        
        # Method 1: PDFPlumber (best for text and simple tables)
        try:
            results['text_data']['pdfplumber'] = self._extract_with_pdfplumber(pdf_path)
            results['extraction_quality']['pdfplumber'] = 'success'
        except Exception as e:
            logger.error(f"PDFPlumber extraction failed: {e}")
            results['extraction_quality']['pdfplumber'] = f'failed: {str(e)}'
        
        # Method 2: PyMuPDF (best for layout preservation)
        try:
            results['text_data']['pymupdf'] = self._extract_with_pymupdf(pdf_path)
            results['extraction_quality']['pymupdf'] = 'success'
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            results['extraction_quality']['pymupdf'] = f'failed: {str(e)}'
        
        # Method 3: Tabula (best for complex tables)
        try:
            results['table_data']['tabula'] = self._extract_tables_tabula(pdf_path)
            results['extraction_quality']['tabula'] = 'success'
        except Exception as e:
            logger.error(f"Tabula extraction failed: {e}")
            results['extraction_quality']['tabula'] = f'failed: {str(e)}'
        
        # Method 4: Camelot (alternative table extraction)
        try:
            results['table_data']['camelot'] = self._extract_tables_camelot(pdf_path)
            results['extraction_quality']['camelot'] = 'success'
        except Exception as e:
            logger.error(f"Camelot extraction failed: {e}")
            results['extraction_quality']['camelot'] = f'failed: {str(e)}'
        
        # Method 5: OCR (fallback for scanned PDFs)
        try:
            results['text_data']['ocr'] = self._extract_with_ocr(pdf_path)
            results['extraction_quality']['ocr'] = 'success'
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            results['extraction_quality']['ocr'] = f'failed: {str(e)}'
        
        # Combine and process results
        results['faculty_data'] = self._process_and_combine_results(results)
        
        return results
    
    def _extract_metadata(self, pdf_path: Path) -> Dict:
        """Extract PDF metadata"""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                metadata = {
                    'num_pages': len(reader.pages),
                    'title': reader.metadata.title if reader.metadata else None,
                    'author': reader.metadata.author if reader.metadata else None,
                    'creator': reader.metadata.creator if reader.metadata else None,
                    'creation_date': str(reader.metadata.creation_date) if reader.metadata else None,
                    'file_size': pdf_path.stat().st_size,
                    'extraction_date': datetime.now().isoformat()
                }
                return metadata
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            return {'error': str(e)}
    
    def _extract_with_pdfplumber(self, pdf_path: Path) -> Dict:
        """Extract text and tables using pdfplumber"""
        data = {'pages': [], 'tables': []}
        
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_data = {
                    'page_num': i + 1,
                    'text': page.extract_text(),
                    'tables': [],
                    'bbox': page.bbox
                }
                
                # Extract tables from this page
                tables = page.extract_tables()
                for j, table in enumerate(tables):
                    if table:
                        page_data['tables'].append({
                            'table_id': j,
                            'data': table,
                            'rows': len(table),
                            'cols': len(table[0]) if table else 0
                        })
                
                data['pages'].append(page_data)
                data['tables'].extend(page_data['tables'])
        
        return data
    
    def _extract_with_pymupdf(self, pdf_path: Path) -> Dict:
        """Extract text with layout information using PyMuPDF"""
        data = {'pages': [], 'blocks': []}
        
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Extract text with layout information
            text_dict = page.get_text("dict")
            
            page_data = {
                'page_num': page_num + 1,
                'text': page.get_text(),
                'blocks': text_dict.get('blocks', []),
                'width': page.rect.width,
                'height': page.rect.height
            }
            
            data['pages'].append(page_data)
            data['blocks'].extend(page_data['blocks'])
        
        doc.close()
        return data
    
    def _extract_tables_tabula(self, pdf_path: Path) -> List[pd.DataFrame]:
        """Extract tables using tabula-py"""
        try:
            # Extract tables with tabula-py
            all_tables = []
            
            try:
                # Try lattice method
                tables = tabula.read_pdf(
                    str(pdf_path),
                    pages='all',
                    lattice=True,
                    multiple_tables=True,
                    pandas_options={'header': None}
                )
                
                if tables:
                    for i, table in enumerate(tables):
                        if not table.empty:
                            table_info = {
                                'method': 'lattice',
                                'table_id': len(all_tables),
                                'dataframe': table,
                                'shape': table.shape,
                                'columns': list(table.columns)
                            }
                            all_tables.append(table_info)
            
            except Exception as e:
                logger.warning(f"Tabula lattice method failed: {e}")
                
            # Try stream method if lattice failed
            if not all_tables:
                try:
                    tables = tabula.read_pdf(
                        str(pdf_path),
                        pages='all',
                        stream=True,
                        multiple_tables=True,
                        pandas_options={'header': None}
                    )
                    
                    if tables:
                        for i, table in enumerate(tables):
                            if not table.empty:
                                table_info = {
                                    'method': 'stream',
                                    'table_id': len(all_tables),
                                    'dataframe': table,
                                    'shape': table.shape,
                                    'columns': list(table.columns)
                                }
                                all_tables.append(table_info)
                
                except Exception as e:
                    logger.warning(f"Tabula stream method failed: {e}")
            
            return all_tables
            
        except Exception as e:
            logger.error(f"Tabula extraction failed: {e}")
            return []
    
    def _extract_tables_camelot(self, pdf_path: Path) -> List[Dict]:
        """Extract tables using camelot"""
        try:
            tables = camelot.read_pdf(str(pdf_path), pages='all', flavor='lattice')
            
            camelot_tables = []
            for i, table in enumerate(tables):
                table_info = {
                    'table_id': i,
                    'dataframe': table.df,
                    'shape': table.shape,
                    'accuracy': table.accuracy,
                    'whitespace': table.whitespace,
                    'page': table.page
                }
                camelot_tables.append(table_info)
            
            return camelot_tables
            
        except Exception as e:
            logger.error(f"Camelot extraction failed: {e}")
            return []
    
    def _extract_with_ocr(self, pdf_path: Path) -> Dict:
        """Extract text using OCR for scanned PDFs"""
        data = {'pages': []}
        
        try:
            doc = fitz.open(pdf_path)
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Convert page to image
                pix = page.get_pixmap()
                img_data = pix.tobytes("ppm")
                
                # Convert to PIL Image
                from io import BytesIO
                img = Image.open(BytesIO(img_data))
                
                # Preprocessing for better OCR
                img_array = np.array(img)
                
                # Convert to grayscale
                if len(img_array.shape) == 3:
                    img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                else:
                    img_gray = img_array
                
                # Apply image enhancement
                img_enhanced = self._enhance_image_for_ocr(img_gray)
                
                # Perform OCR
                ocr_text = pytesseract.image_to_string(
                    img_enhanced, 
                    lang='por+eng',  # Portuguese and English
                    config='--psm 6'  # Uniform block of text
                )
                
                page_data = {
                    'page_num': page_num + 1,
                    'text': ocr_text,
                    'image_size': img.size
                }
                
                data['pages'].append(page_data)
            
            doc.close()
            return data
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {'error': str(e)}
    
    def _enhance_image_for_ocr(self, img_gray: np.ndarray) -> np.ndarray:
        """Apply image enhancement techniques for better OCR"""
        # Noise reduction
        img_denoised = cv2.medianBlur(img_gray, 3)
        
        # Contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        img_enhanced = clahe.apply(img_denoised)
        
        # Binarization
        _, img_binary = cv2.threshold(img_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return img_binary
    
    def _process_and_combine_results(self, results: Dict) -> List[Dict]:
        """Process and combine results from all extraction methods"""
        faculty_data = []
        
        # Combine text from all successful methods
        all_text = ""
        for method, text_data in results['text_data'].items():
            if isinstance(text_data, dict) and 'pages' in text_data:
                for page in text_data['pages']:
                    if page.get('text'):
                        all_text += page['text'] + "\n"
        
        # Extract faculty information using patterns
        faculty_data.extend(self._extract_faculty_from_text(all_text))
        
        # Process tables if available
        table_faculty = self._extract_faculty_from_tables(results['table_data'])
        faculty_data.extend(table_faculty)
        
        # Remove duplicates and clean data
        faculty_data = self._clean_and_deduplicate(faculty_data)
        
        return faculty_data
    
    def _extract_faculty_from_text(self, text: str) -> List[Dict]:
        """Extract faculty information from text using regex patterns"""
        faculty_data = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Try to match faculty names
            for pattern in self.name_patterns:
                matches = re.findall(pattern, line)
                for match in matches:
                    faculty_info = {
                        'name': match.strip(),
                        'category': self._extract_category(line),
                        'department': self._extract_department(line),
                        'line_number': i + 1,
                        'source_line': line,
                        'extraction_method': 'text_pattern'
                    }
                    
                    # Look for additional info in surrounding lines
                    context_lines = lines[max(0, i-2):min(len(lines), i+3)]
                    faculty_info.update(self._extract_additional_info(context_lines))
                    
                    faculty_data.append(faculty_info)
        
        return faculty_data
    
    def _extract_category(self, text: str) -> Optional[str]:
        """Extract faculty category from text"""
        text_lower = text.lower()
        
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return category
        
        return None
    
    def _extract_department(self, text: str) -> Optional[str]:
        """Extract department from text"""
        for pattern in self.department_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_additional_info(self, context_lines: List[str]) -> Dict:
        """Extract additional information from context lines"""
        additional_info = {}
        
        context_text = ' '.join(context_lines).lower()
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_matches = re.findall(email_pattern, context_text, re.IGNORECASE)
        if email_matches:
            additional_info['email'] = email_matches[0]
        
        # Phone pattern
        phone_pattern = r'(\+351\s?)?[0-9]{3}\s?[0-9]{3}\s?[0-9]{3}'
        phone_matches = re.findall(phone_pattern, context_text)
        if phone_matches:
            additional_info['phone'] = phone_matches[0]
        
        # ORCID pattern
        orcid_pattern = r'0000-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]'
        orcid_matches = re.findall(orcid_pattern, context_text)
        if orcid_matches:
            additional_info['orcid'] = orcid_matches[0]
        
        return additional_info
    
    def _extract_faculty_from_tables(self, table_data: Dict) -> List[Dict]:
        """Extract faculty information from tables"""
        faculty_data = []
        
        for method, tables in table_data.items():
            if not tables:
                continue
                
            for table_info in tables:
                if 'dataframe' in table_info:
                    df = table_info['dataframe']
                    table_faculty = self._process_table_dataframe(df, method)
                    faculty_data.extend(table_faculty)
        
        return faculty_data
    
    def _process_table_dataframe(self, df: pd.DataFrame, method: str) -> List[Dict]:
        """Process a table DataFrame to extract faculty information"""
        faculty_data = []
        
        if df.empty:
            return faculty_data
        
        # Try to identify columns
        name_col = self._identify_name_column(df)
        category_col = self._identify_category_column(df)
        dept_col = self._identify_department_column(df)
        
        for idx, row in df.iterrows():
            faculty_info = {
                'extraction_method': f'table_{method}',
                'table_row': idx
            }
            
            if name_col is not None:
                name = str(row.iloc[name_col]).strip()
                if name and name != 'nan' and len(name) > 3:
                    faculty_info['name'] = name
            
            if category_col is not None:
                category = str(row.iloc[category_col]).strip()
                if category and category != 'nan':
                    faculty_info['category'] = category
            
            if dept_col is not None:
                department = str(row.iloc[dept_col]).strip()
                if department and department != 'nan':
                    faculty_info['department'] = department
            
            # Only add if we found at least a name
            if 'name' in faculty_info:
                faculty_data.append(faculty_info)
        
        return faculty_data
    
    def _identify_name_column(self, df: pd.DataFrame) -> Optional[int]:
        """Identify the column most likely to contain names"""
        name_indicators = ['nome', 'name', 'docente', 'professor', 'faculty']
        
        # Check column headers first
        for i, col in enumerate(df.columns):
            col_str = str(col).lower()
            if any(indicator in col_str for indicator in name_indicators):
                return i
        
        # Check first few rows for name-like patterns
        for i in range(min(len(df.columns), 5)):
            sample_values = df.iloc[:5, i].astype(str)
            name_score = 0
            
            for value in sample_values:
                if self._looks_like_name(value):
                    name_score += 1
            
            if name_score >= 2:  # At least 2 name-like values
                return i
        
        return None
    
    def _identify_category_column(self, df: pd.DataFrame) -> Optional[int]:
        """Identify the column most likely to contain categories"""
        category_indicators = ['categoria', 'category', 'cargo', 'position', 'grau']
        
        for i, col in enumerate(df.columns):
            col_str = str(col).lower()
            if any(indicator in col_str for indicator in category_indicators):
                return i
        
        return None
    
    def _identify_department_column(self, df: pd.DataFrame) -> Optional[int]:
        """Identify the column most likely to contain departments"""
        dept_indicators = ['departamento', 'department', 'área', 'area', 'escola', 'school']
        
        for i, col in enumerate(df.columns):
            col_str = str(col).lower()
            if any(indicator in col_str for indicator in dept_indicators):
                return i
        
        return None
    
    def _looks_like_name(self, value: str) -> bool:
        """Check if a value looks like a person's name"""
        if not value or len(value) < 3:
            return False
        
        value = value.strip()
        
        # Check if it matches name patterns
        for pattern in self.name_patterns:
            if re.match(pattern, value):
                return True
        
        # Simple heuristic: multiple words with capital letters
        words = value.split()
        if len(words) >= 2:
            capital_words = sum(1 for word in words if word and word[0].isupper())
            return capital_words >= 2
        
        return False
    
    def _clean_and_deduplicate(self, faculty_data: List[Dict]) -> List[Dict]:
        """Clean and remove duplicate faculty entries"""
        if not faculty_data:
            return []
        
        # Convert to DataFrame for easier processing
        df = pd.DataFrame(faculty_data)
        
        # Clean names
        if 'name' in df.columns:
            df['name'] = df['name'].str.strip()
            df['name'] = df['name'].str.replace(r'\s+', ' ', regex=True)
            
            # Remove entries with invalid names
            df = df[df['name'].str.len() > 3]
            df = df[~df['name'].str.contains(r'^\d+$', regex=True)]  # Remove pure numbers
        
        # Remove duplicates based on name similarity
        df = self._remove_similar_names(df)
        
        return df.to_dict('records')
    
    def _remove_similar_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove entries with very similar names"""
        if 'name' not in df.columns or df.empty:
            return df
        
        from difflib import SequenceMatcher
        
        to_remove = set()
        names = df['name'].tolist()
        
        for i, name1 in enumerate(names):
            if i in to_remove:
                continue
                
            for j, name2 in enumerate(names[i+1:], i+1):
                if j in to_remove:
                    continue
                
                similarity = SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
                if similarity > 0.85:  # Very similar names
                    # Keep the one with more information
                    row1 = df.iloc[i]
                    row2 = df.iloc[j]
                    
                    info_count1 = sum(1 for v in row1.values if pd.notna(v) and str(v).strip())
                    info_count2 = sum(1 for v in row2.values if pd.notna(v) and str(v).strip())
                    
                    if info_count1 >= info_count2:
                        to_remove.add(j)
                    else:
                        to_remove.add(i)
        
        return df.drop(df.index[list(to_remove)])
    
    def save_results(self, results: Dict, output_path: str) -> None:
        """Save extraction results to files"""
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save faculty data as CSV
        if results['faculty_data']:
            faculty_df = pd.DataFrame(results['faculty_data'])
            faculty_df.to_csv(output_path / 'faculty_advanced_parsed.csv', index=False)
            logger.info(f"Saved {len(faculty_df)} faculty records to CSV")
        
        # Save full results as JSON
        results_copy = results.copy()
        # Remove DataFrames from results for JSON serialization
        for method_data in results_copy.get('table_data', {}).values():
            for table in method_data:
                if 'dataframe' in table:
                    table['dataframe'] = table['dataframe'].to_dict() if hasattr(table['dataframe'], 'to_dict') else str(table['dataframe'])
        
        with open(output_path / 'extraction_results.json', 'w', encoding='utf-8') as f:
            json.dump(results_copy, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Results saved to {output_path}")

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced PDF Parser for IPT Faculty Data')
    parser.add_argument('pdf_path', help='Path to the PDF file')
    parser.add_argument('--output', '-o', default='data', help='Output directory')
    parser.add_argument('--tesseract-path', help='Path to tesseract executable')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize parser
    parser = AdvancedPDFParser(tesseract_path=args.tesseract_path)
    
    # Extract data
    logger.info(f"Processing PDF: {args.pdf_path}")
    results = parser.extract_with_multiple_methods(args.pdf_path)
    
    # Save results
    parser.save_results(results, args.output)
    
    # Print summary
    faculty_count = len(results['faculty_data'])
    successful_methods = [method for method, status in results['extraction_quality'].items() if status == 'success']
    
    print(f"\n=== EXTRACTION SUMMARY ===")
    print(f"Faculty members found: {faculty_count}")
    print(f"Successful methods: {', '.join(successful_methods)}")
    print(f"Results saved to: {args.output}")

if __name__ == "__main__":
    main()

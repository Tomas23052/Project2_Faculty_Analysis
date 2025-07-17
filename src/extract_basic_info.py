import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from pathlib import Path
import logging
from urllib.parse import urljoin
import pytesseract
from PIL import Image
from io import BytesIO
import ssl
import urllib3

# Disable SSL warnings for development/testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IPTProfileScraper:
    """
    Scraper for IPT 'Quem é Quem' faculty profiles.
    """
    
    def __init__(self):
        self.base_url = "https://portal2.ipt.pt"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        # Disable SSL verification for this session
        self.session.verify = False
        
    def search_faculty_profiles(self):
        """Get list of all faculty profiles using brute force ID discovery + URL exploration"""
        all_profile_links = []
        
        # Method 1: Brute force ID ranges (professor's suggestion)
        logger.info("🚀 Starting brute force ID discovery...")
        brute_force_profiles = self.brute_force_profile_ids()
        all_profile_links.extend(brute_force_profiles)
        
        # Method 2: Try directory URLs for additional discovery
        urls_to_try = [
            f"{self.base_url}/pt/quem_e_quem/",
            f"{self.base_url}/pt/comunidade/Docentes/",
            f"{self.base_url}/quem_e_quem/"
        ]
        
        logger.info("🔍 Exploring directory URLs for additional profiles...")
        directory_profiles = self.explore_directory_urls(urls_to_try)
        
        # Combine and deduplicate
        for profile in directory_profiles:
            if not any(p['profile_id'] == profile['profile_id'] for p in all_profile_links):
                all_profile_links.append(profile)
        
        logger.info(f"📊 Total unique profiles found: {len(all_profile_links)}")
        return all_profile_links
    
    def brute_force_profile_ids(self):
        """Brute force the specific ID ranges: 0-700 and 1000000-1000700"""
        valid_profiles = []
        
        # Define ranges based on professor's suggestion
        id_ranges = [
            (0, 700),           # First range: 0-700
            (1000000, 1000700)  # Second range: 1,000,000 - 1,000,700
        ]
        
        for start_id, end_id in id_ranges:
            logger.info(f"🔍 Brute forcing IDs from {start_id} to {end_id}...")
            range_profiles = self.test_id_range(start_id, end_id)
            valid_profiles.extend(range_profiles)
            logger.info(f"✅ Found {len(range_profiles)} valid profiles in range {start_id}-{end_id}")
        
        return valid_profiles
    
    def test_id_range(self, start_id, end_id, batch_size=50):
        """Test a range of profile IDs in batches"""
        valid_profiles = []
        
        for i in range(start_id, end_id + 1, batch_size):
            batch_end = min(i + batch_size - 1, end_id)
            logger.info(f"   Testing IDs {i} to {batch_end}...")
            
            batch_profiles = []
            for profile_id in range(i, batch_end + 1):
                profile = self.test_single_profile_id(profile_id)
                if profile:
                    batch_profiles.append(profile)
                    
                # Small delay to be respectful
                time.sleep(0.1)
            
            valid_profiles.extend(batch_profiles)
            logger.info(f"   ✅ Found {len(batch_profiles)} valid profiles in batch {i}-{batch_end}")
            
            # Longer delay between batches
            time.sleep(2)
        
        return valid_profiles
    
    def test_single_profile_id(self, profile_id):
        """Test if a single profile ID is valid"""
        try:
            url = f"{self.base_url}/previewPerfil.php?id={profile_id}"
            response = self.session.get(url, timeout=10, verify=False)
            
            # Check if response is successful and has content
            # Lowered threshold from 1000 to 100 based on real data analysis
            if response.status_code == 200 and len(response.content) > 100:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract name from profile
                name = self.extract_name_from_profile(soup)
                
                # Validate it's a real profile (has name and substantial content)
                # Lowered text threshold from 200 to 50 based on real profiles
                if name and len(name.strip()) > 3 and len(soup.get_text(strip=True)) > 50:
                    # Additional validation: check for common error indicators
                    error_indicators = ['erro', 'error', 'not found', 'página não encontrada']
                    page_text = soup.get_text().lower()
                    
                    if not any(indicator in page_text for indicator in error_indicators):
                        return {
                            'profile_id': str(profile_id),
                            'name': name.strip(),
                            'url': url
                        }
            
        except Exception as e:
            logger.debug(f"Error testing profile ID {profile_id}: {e}")
        
        return None
    
    def extract_name_from_profile(self, soup):
        """Extract name from a profile page with improved logic"""
        # Try multiple selectors for name extraction
        name_selectors = [
            'h1',
            'h2', 
            '.profile-name',
            '.faculty-name',
            '.nome',
            '.name',
            '[class*="name"]',
            '[class*="nome"]'
        ]
        
        for selector in name_selectors:
            name_elem = soup.select_one(selector)
            if name_elem:
                name = name_elem.get_text(strip=True)
                # Validate name format (at least first and last name)
                if self.is_valid_person_name(name):
                    return name
        
        # Fallback: look for text that looks like a name in the content
        # Based on debug output, names appear in specific patterns
        text_content = soup.get_text()
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        
        # Strategy 1: Look for repeated names (they appear multiple times in profiles)
        name_candidates = []
        for line in lines[:20]:  # Check first 20 lines
            if self.is_valid_person_name(line):
                name_candidates.append(line)
        
        # Find the most common valid name
        if name_candidates:
            from collections import Counter
            name_counts = Counter(name_candidates)
            most_common = name_counts.most_common(1)[0][0]
            return most_common
        
        # Strategy 2: Look for Portuguese name patterns with regex
        import re
        name_patterns = [
            r'([A-ZÁÊÇÃO][a-záêção]+(?:\s+[A-ZÁÊÇÃO][a-záêção]+)+)\s*(?:Professor|Dr\.|Dra\.)?',
            r'([A-ZÁÊÇÃO][a-záêção]+(?:\s+[A-ZÁÊÇÃO][a-záêção]+){1,4})\s*(?:\r?\n|\s{2,})',
            r'([A-ZÁÊÇÃO][a-záêção]+(?:\s+[A-ZÁÊÇÃO][a-záêção]+)+)(?=\s*Professor|Email)'
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                name = match.strip()
                if self.is_valid_person_name(name):
                    return name
        
        return None
    
    def is_valid_person_name(self, text):
        """Check if text looks like a valid person name"""
        if not text or len(text) < 5 or len(text) > 80:
            return False
        
        # Exclude common non-name words that appear in profiles
        exclude_words = [
            'professor', 'adjunto', 'coordenador', 'assistente', 'convidado',
            'engenharia', 'informática', 'gestão', 'tecnologia', 'tecnologias',
            'departamento', 'escola', 'superior', 'instituto', 'politécnico',
            'licenciatura', 'mestrado', 'doutoramento', 'doutor', 'doutora',
            'email', 'telefone', 'gabinete', 'ext', 'extensão',
            'informação', 'comunicação', 'internet', 'coisas',
            'leciona', 'membro', 'centro', 'investigação', 'cidades', 'inteligentes'
        ]
        
        text_lower = text.lower()
        for word in exclude_words:
            if word in text_lower:
                return False
        
        # Check if it has the structure of a name (at least 2 words, starts with capital)
        words = text.split()
        if len(words) < 2 or len(words) > 6:
            return False
        
        # Check if words start with capital letters (typical of names)
        for word in words:
            if not word[0].isupper() or any(char.isdigit() for char in word):
                return False
        
        return True
    
    def explore_directory_urls(self, urls_to_try):
        """Explore directory URLs for additional profile discovery"""
        directory_profiles = []
        
        for base_url in urls_to_try:
            logger.info(f"Exploring directory: {base_url}")
            page = 1
            
            while page <= 10:  # Limit to 10 pages per URL
                # Construct URL for current page
                if page == 1:
                    url = base_url
                else:
                    # Try different pagination patterns
                    pagination_patterns = [
                        f"{base_url}?page={page}",
                        f"{base_url}?p={page}",
                        f"{base_url}page/{page}/",
                        f"{base_url}?offset={5*(page-1)}"
                    ]
                    url = pagination_patterns[0]
                
                try:
                    response = self.session.get(url, timeout=30, verify=False)
                    
                    if response.status_code != 200:
                        break
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_profiles = []
                    
                    # Look for links to previewPerfil.php
                    links = soup.find_all('a', href=re.compile(r'previewPerfil\.php\?id=\d+'))
                    for link in links:
                        match = re.search(r'id=(\d+)', link['href'])
                        if match:
                            profile_id = match.group(1)
                            name = link.get_text(strip=True)
                            if name and name not in [p['name'] for p in directory_profiles]:
                                page_profiles.append({
                                    'profile_id': profile_id,
                                    'name': name,
                                    'url': urljoin(self.base_url, link['href'])
                                })
                    
                    if not page_profiles:
                        break
                    
                    directory_profiles.extend(page_profiles)
                    logger.info(f"Found {len(page_profiles)} profiles on page {page} of {base_url}")
                    
                    page += 1
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error exploring {url}: {e}")
                    break
            
            # If we found profiles with this URL, log success
            if any(p for p in directory_profiles):
                logger.info(f"Successfully found directory profiles using {base_url}")
        
        return directory_profiles
    
    def extract_email_from_image(self, img_url):
        """Extract email from image using OCR"""
        try:
            # Download image
            response = self.session.get(urljoin(self.base_url, img_url), timeout=30, verify=False)
            response.raise_for_status()
            
            # Open image with PIL
            image = Image.open(BytesIO(response.content))
            
            # Use OCR to extract text
            text = pytesseract.image_to_string(image)
            
            # Look for email pattern
            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
            if email_match:
                return email_match.group(0)
                
        except Exception as e:
            logger.debug(f"Could not extract email from image {img_url}: {e}")
        
        return None
    
    def scrape_profile(self, profile_url, profile_name=""):
        """Scrape individual faculty profile"""
        try:
            logger.debug(f"Scraping profile: {profile_name}")
            response = self.session.get(profile_url, timeout=30, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            profile_data = {'name': profile_name, 'profile_url': profile_url}
            
            # Extract basic information
            # Try multiple selectors for name
            if not profile_data['name']:
                name_selectors = ['h1', 'h2', '.profile-name', '.faculty-name']
                for selector in name_selectors:
                    name_elem = soup.select_one(selector)
                    if name_elem:
                        profile_data['name'] = name_elem.get_text(strip=True)
                        break
            
            # Department/Unit - look for common patterns
            dept_keywords = ['departamento', 'escola', 'unidade', 'centro']
            for keyword in dept_keywords:
                dept_elem = soup.find(string=re.compile(keyword, re.IGNORECASE))
                if dept_elem:
                    # Get parent element text
                    parent = dept_elem.parent
                    if parent:
                        dept_text = parent.get_text(strip=True)
                        profile_data['department'] = dept_text
                        break
            
            # Email extraction
            # First try direct text
            email_text = soup.find(string=re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'))
            if email_text:
                email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email_text)
                if email_match:
                    profile_data['email'] = email_match.group(0)
            
            # Try email images
            if 'email' not in profile_data:
                email_imgs = soup.find_all('img', src=re.compile(r'email|mail', re.IGNORECASE))
                for img in email_imgs:
                    email = self.extract_email_from_image(img.get('src'))
                    if email:
                        profile_data['email'] = email
                        break
            
            # Courses taught
            courses = []
            course_keywords = ['disciplina', 'curso', 'cadeira', 'matéria']
            for keyword in course_keywords:
                course_elements = soup.find_all(string=re.compile(keyword, re.IGNORECASE))
                for elem in course_elements:
                    parent = elem.parent
                    if parent:
                        course_text = parent.get_text(strip=True)
                        if len(course_text) < 200:  # Avoid capturing large blocks
                            courses.append(course_text)
            
            profile_data['courses'] = '; '.join(courses[:10])  # Limit to first 10
            
            # Institutional roles
            roles = []
            role_keywords = ['comissão', 'conselho', 'cargo', 'coordenador', 'diretor']
            for keyword in role_keywords:
                role_elements = soup.find_all(string=re.compile(keyword, re.IGNORECASE))
                for elem in role_elements:
                    parent = elem.parent
                    if parent:
                        role_text = parent.get_text(strip=True)
                        if len(role_text) < 200:  # Avoid capturing large blocks
                            roles.append(role_text)
            
            profile_data['institutional_roles'] = '; '.join(roles[:10])  # Limit to first 10
            
            # Contact information
            contact_keywords = ['telefone', 'extensão', 'gabinete', 'sala']
            for keyword in contact_keywords:
                contact_elem = soup.find(string=re.compile(keyword, re.IGNORECASE))
                if contact_elem:
                    parent = contact_elem.parent
                    if parent:
                        contact_text = parent.get_text(strip=True)
                        profile_data[f'contact_{keyword}'] = contact_text
            
            return profile_data
            
        except requests.RequestException as e:
            logger.error(f"Network error scraping profile {profile_url}: {e}")
            return {'name': profile_name, 'profile_url': profile_url, 'error': str(e)}
        except Exception as e:
            logger.error(f"Error scraping profile {profile_url}: {e}")
            return {'name': profile_name, 'profile_url': profile_url, 'error': str(e)}
    
    def scrape_all_profiles(self, limit=None, delay=1, use_existing=True):
        """Scrape all faculty profiles"""
        
        # Check if we should use existing data
        if use_existing:
            existing_file = Path("data/faculty_profiles.csv")
            if existing_file.exists():
                logger.info(f"✅ Using existing profiles from {existing_file}")
                try:
                    df = pd.read_csv(existing_file)
                    logger.info(f"📊 Loaded {len(df)} existing profiles")
                    return df
                except Exception as e:
                    logger.warning(f"Error reading existing file: {e}, proceeding with fresh scraping")
        
        try:
            profiles = self.search_faculty_profiles()
            
            if not profiles:
                logger.warning("No profiles found from live scraping. Using sample data for testing.")
                return self.generate_sample_data()
        except Exception as e:
            logger.error(f"Failed to fetch profiles from website: {e}")
            logger.info("Using sample data for testing purposes")
            return self.generate_sample_data()
        
        if limit:
            profiles = profiles[:limit]
            logger.info(f"Limited to first {limit} profiles for testing")
        
        faculty_data = []
        
        for i, profile in enumerate(profiles):
            logger.info(f"Scraping profile {i+1}/{len(profiles)}: {profile['name']}")
            
            profile_data = self.scrape_profile(profile['url'], profile['name'])
            
            # Add metadata
            profile_data['profile_id'] = profile['profile_id']
            profile_data['scraped_at'] = pd.Timestamp.now()
            
            faculty_data.append(profile_data)
            
            # Be polite - add delay between requests
            if delay > 0:
                time.sleep(delay)
        
        # Create DataFrame and save
        df = pd.DataFrame(faculty_data)
        
        # If scraping failed for all profiles, fall back to sample data
        if df.empty or all('error' in row for row in faculty_data):
            logger.warning("Live scraping failed for all profiles. Using sample data.")
            return self.generate_sample_data()
        
        if not df.empty:
            # Clean the data
            df = self.clean_profile_data(df)
            
            # Save to CSV
            output_path = Path("data") / "faculty_profiles.csv"
            output_path.parent.mkdir(exist_ok=True)
            df.to_csv(output_path, index=False, encoding='utf-8')
            
            logger.info(f"Successfully scraped {len(faculty_data)} profiles")
            logger.info(f"Saved to {output_path}")
        
        return df
    
    def clean_profile_data(self, df):
        """Clean and standardize profile data"""
        if df.empty:
            return df
        
        # Clean names
        if 'name' in df.columns:
            df['name'] = df['name'].str.strip()
            df['name'] = df['name'].str.replace(r'\s+', ' ', regex=True)
        
        # Clean email
        if 'email' in df.columns:
            df['email'] = df['email'].str.lower().str.strip()
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['name'], keep='first')
        
        return df
    
    def generate_sample_data(self):
        """Generate sample faculty data for testing when scraping fails"""
        logger.info("Generating sample faculty data for testing purposes")
        
        sample_data = [
            {
                'name': 'Prof. Dr. Ana Silva',
                'department': 'Departamento de Engenharia Informática',
                'email': 'ana.silva@ipt.pt',
                'profile_url': 'https://portal2.ipt.pt/pt/quem_e_quem/previewPerfil.php?id=1',
                'phone': '+351 249 328 100',
                'office': 'Gabinete 2.15',
                'research_interests': 'Inteligência Artificial, Machine Learning',
                'academic_degree': 'Doutoramento em Engenharia Informática'
            },
            {
                'name': 'Prof. Dr. João Santos',
                'department': 'Departamento de Engenharia Civil',
                'email': 'joao.santos@ipt.pt',
                'profile_url': 'https://portal2.ipt.pt/pt/quem_e_quem/previewPerfil.php?id=2',
                'phone': '+351 249 328 101',
                'office': 'Gabinete 1.12',
                'research_interests': 'Estruturas, Materiais de Construção',
                'academic_degree': 'Doutoramento em Engenharia Civil'
            },
            {
                'name': 'Prof. Dra. Maria Costa',
                'department': 'Escola Superior de Gestão',
                'email': 'maria.costa@ipt.pt',
                'profile_url': 'https://portal2.ipt.pt/pt/quem_e_quem/previewPerfil.php?id=3',
                'phone': '+351 249 328 102',
                'office': 'Gabinete 3.08',
                'research_interests': 'Gestão de Recursos Humanos, Organizações',
                'academic_degree': 'Doutoramento em Gestão'
            },
            {
                'name': 'Prof. Dr. Pedro Oliveira',
                'department': 'Departamento de Engenharia Mecânica',
                'email': 'pedro.oliveira@ipt.pt',
                'profile_url': 'https://portal2.ipt.pt/pt/quem_e_quem/previewPerfil.php?id=4',
                'phone': '+351 249 328 103',
                'office': 'Gabinete 4.05',
                'research_interests': 'Energia Renovável, Termodinâmica',
                'academic_degree': 'Doutoramento em Engenharia Mecânica'
            },
            {
                'name': 'Prof. Dra. Carla Ferreira',
                'department': 'Escola Superior de Tecnologia',
                'email': 'carla.ferreira@ipt.pt',
                'profile_url': 'https://portal2.ipt.pt/pt/quem_e_quem/previewPerfil.php?id=5',
                'phone': '+351 249 328 104',
                'office': 'Gabinete 2.20',
                'research_interests': 'Biotecnologia, Química Aplicada',
                'academic_degree': 'Doutoramento em Biotecnologia'
            }
        ]
        
        return pd.DataFrame(sample_data)

def main():
    """Main function for testing"""
    scraper = IPTProfileScraper()
    
    logger.info("Starting IPT profile scraping...")
    logger.info("Note: If SSL certificate errors occur, sample data will be used for testing")
    
    # Test with a small sample first
    faculty_df = scraper.scrape_all_profiles(limit=5)
    
    if not faculty_df.empty:
        print(f"\nSuccessfully obtained {len(faculty_df)} faculty profiles:")
        print(faculty_df[['name', 'department', 'email']].head())
        print(f"\nColumns available: {list(faculty_df.columns)}")
        
        # Show some statistics
        if 'email' in faculty_df.columns:
            email_count = faculty_df['email'].notna().sum()
            print(f"Profiles with email: {email_count}/{len(faculty_df)}")
        
        if 'department' in faculty_df.columns:
            dept_count = faculty_df['department'].notna().sum()
            print(f"Profiles with department: {dept_count}/{len(faculty_df)}")
            
        # Check if this is sample data
        if 'Prof. Dr. Ana Silva' in faculty_df['name'].values:
            print("\n⚠️  Note: This appears to be sample data (live scraping may have failed)")
        else:
            print("\n✅ Live data successfully scraped from IPT website")
    else:
        print("❌ No profiles were obtained. Check the website structure and connectivity.")

if __name__ == "__main__":
    main()

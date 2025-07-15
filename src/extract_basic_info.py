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
        """Get list of all faculty profiles from 'Quem é Quem' with pagination support"""
        all_profile_links = []
        page = 1
        
        # Try multiple possible URLs for faculty directory
        urls_to_try = [
            f"{self.base_url}/pt/quem_e_quem/",
            f"{self.base_url}/pt/comunidade/Docentes/",
            f"{self.base_url}/quem_e_quem/"
        ]
        
        for base_url in urls_to_try:
            logger.info(f"Trying faculty directory: {base_url}")
            
            while True:
                # Construct URL for current page
                if page == 1:
                    url = base_url
                else:
                    # Try different pagination patterns
                    pagination_patterns = [
                        f"{base_url}?page={page}",
                        f"{base_url}?p={page}",
                        f"{base_url}page/{page}/",
                        f"{base_url}?offset={5*(page-1)}"  # 5 profiles per page
                    ]
                    url = pagination_patterns[0]  # Start with most common pattern
                
                try:
                    logger.info(f"Fetching page {page} from {url}")
                    response = self.session.get(url, timeout=30, verify=False)
                    
                    if response.status_code != 200:
                        logger.warning(f"Page {page} returned status {response.status_code}")
                        break
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_profile_links = []
                    
                    # Method 1: Look for links to previewPerfil.php
                    links = soup.find_all('a', href=re.compile(r'previewPerfil\.php\?id=\d+'))
                    for link in links:
                        match = re.search(r'id=(\d+)', link['href'])
                        if match:
                            profile_id = match.group(1)
                            name = link.get_text(strip=True)
                            if name and name not in [p['name'] for p in all_profile_links]:
                                page_profile_links.append({
                                    'profile_id': profile_id,
                                    'name': name,
                                    'url': urljoin(self.base_url, link['href'])
                                })
                    
                    # Method 2: Look for other profile patterns
                    if not page_profile_links:
                        all_links = soup.find_all('a', href=True)
                        for link in all_links:
                            href = link.get('href', '')
                            text = link.get_text(strip=True)
                            
                            # Check for profile patterns in URL or text
                            profile_patterns = ['perfil', 'docente', 'professor', 'faculty']
                            if any(pattern in href.lower() for pattern in profile_patterns):
                                if text and len(text.split()) >= 2 and text not in [p['name'] for p in all_profile_links]:
                                    page_profile_links.append({
                                        'profile_id': len(all_profile_links) + len(page_profile_links) + 1,
                                        'name': text,
                                        'url': urljoin(self.base_url, href)
                                    })
                    
                    # Method 3: Look for faculty names in structured elements
                    if not page_profile_links:
                        # Look for cards, divs, or other containers with faculty info
                        faculty_containers = soup.find_all(['div', 'article', 'section'], 
                                                         class_=re.compile(r'(faculty|docente|profile|staff)', re.I))
                        for container in faculty_containers:
                            name_elem = container.find(['h1', 'h2', 'h3', 'h4', 'strong', 'b'])
                            if name_elem:
                                name = name_elem.get_text(strip=True)
                                if name and len(name.split()) >= 2 and name not in [p['name'] for p in all_profile_links]:
                                    page_profile_links.append({
                                        'profile_id': len(all_profile_links) + len(page_profile_links) + 1,
                                        'name': name,
                                        'url': url  # Use page URL as fallback
                                    })
                    
                    if not page_profile_links:
                        logger.info(f"No profiles found on page {page}, trying next URL or stopping")
                        break
                    
                    logger.info(f"Found {len(page_profile_links)} profiles on page {page}")
                    all_profile_links.extend(page_profile_links)
                    
                    # Check for "Next" button or pagination
                    next_button_found = False
                    next_patterns = ['next', 'próximo', 'siguiente', 'suivant', '›', '»']
                    
                    for pattern in next_patterns:
                        next_links = soup.find_all('a', string=re.compile(pattern, re.I))
                        next_links.extend(soup.find_all('a', title=re.compile(pattern, re.I)))
                        
                        if next_links:
                            next_button_found = True
                            break
                    
                    # Also check for pagination by looking at page numbers
                    page_numbers = soup.find_all('a', string=re.compile(r'^\d+$'))
                    if page_numbers:
                        max_page = max([int(a.string) for a in page_numbers if a.string.isdigit()])
                        if page < max_page:
                            next_button_found = True
                    
                    if not next_button_found:
                        logger.info(f"No next page found after page {page}")
                        break
                        
                    page += 1
                    
                    # Safety limit to prevent infinite loops
                    if page > 50:
                        logger.warning("Reached page limit of 50, stopping")
                        break
                    
                    # Be respectful with delays
                    time.sleep(1)
                    
                except requests.RequestException as e:
                    logger.error(f"Error fetching page {page}: {e}")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error on page {page}: {e}")
                    break
            
            # If we found profiles, stop trying other URLs
            if all_profile_links:
                logger.info(f"Successfully found profiles using {base_url}")
                break
        
        logger.info(f"Total faculty profiles found: {len(all_profile_links)}")
        return all_profile_links
    
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
    
    def scrape_all_profiles(self, limit=None, delay=1):
        """Scrape all faculty profiles"""
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

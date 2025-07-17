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
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from datetime import datetime

# Disable SSL warnings for development/testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedIPTProfileScraper:
    """
    Enhanced scraper for IPT 'Quem é Quem' faculty profiles with brute force ID discovery.
    Based on professor's hint: IDs range from 0-700 and 1000000-1000700
    """
    
    def __init__(self, max_workers=10):
        self.base_url = "https://portal2.ipt.pt"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        # Disable SSL verification for this session
        self.session.verify = False
        self.max_workers = max_workers
        
        # ID ranges based on professor's hint
        self.id_ranges = [
            (0, 700),           # First range: 0-700
            (1000000, 1000700)  # Second range: 1M-1M+700
        ]
        
    def check_profile_exists(self, profile_id):
        """Check if a profile ID exists and return basic info"""
        try:
            url = f"{self.base_url}/previewPerfil.php?id={profile_id}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Check if this is a valid profile (not error page)
                text_content = soup.get_text().lower()
                
                # Skip if it's an error page
                if any(error in text_content for error in ['erro', 'error', 'not found', 'página não encontrada']):
                    return None
                
                # Extract basic info to validate it's a real profile
                title = soup.find('title')
                h1_tags = soup.find_all(['h1', 'h2', 'h3'])
                
                # Look for name indicators
                name = None
                for tag in h1_tags:
                    text = tag.get_text(strip=True)
                    if text and len(text) > 3 and not any(skip in text.lower() for skip in ['ipt', 'instituto', 'tomar']):
                        name = text
                        break
                
                # If we found a name, this is likely a valid profile
                if name:
                    return {
                        'profile_id': profile_id,
                        'name': name,
                        'url': url,
                        'exists': True
                    }
                    
            return None
            
        except Exception as e:
            logger.debug(f"Error checking profile {profile_id}: {e}")
            return None
    
    def discover_all_valid_profiles(self):
        """Discover all valid profile IDs using brute force in the specified ranges"""
        logger.info("🔍 Starting brute force discovery of profile IDs...")
        logger.info(f"📊 Ranges to check: {self.id_ranges}")
        
        all_valid_profiles = []
        
        for start_id, end_id in self.id_ranges:
            logger.info(f"🎯 Checking range {start_id} to {end_id}...")
            
            # Generate all IDs in this range
            id_list = list(range(start_id, end_id + 1))
            
            # Use ThreadPoolExecutor for parallel checking
            valid_profiles_in_range = []
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_id = {executor.submit(self.check_profile_exists, profile_id): profile_id 
                               for profile_id in id_list}
                
                # Process completed tasks
                for i, future in enumerate(as_completed(future_to_id)):
                    if i % 100 == 0:
                        logger.info(f"   Checked {i}/{len(id_list)} IDs in range {start_id}-{end_id}")
                    
                    try:
                        result = future.result()
                        if result:
                            valid_profiles_in_range.append(result)
                            logger.info(f"   ✅ Found valid profile: ID {result['profile_id']} - {result['name']}")
                    except Exception as e:
                        logger.debug(f"Error processing future: {e}")
            
            logger.info(f"📈 Found {len(valid_profiles_in_range)} valid profiles in range {start_id}-{end_id}")
            all_valid_profiles.extend(valid_profiles_in_range)
            
            # Brief pause between ranges
            time.sleep(1)
        
        logger.info(f"🎉 Total valid profiles discovered: {len(all_valid_profiles)}")
        return all_valid_profiles
    
    def extract_detailed_profile(self, profile_info):
        """Extract detailed information from a profile"""
        try:
            url = profile_info['url']
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract detailed information
            profile_data = {
                'profile_id': profile_info['profile_id'],
                'name': profile_info['name'],
                'url': url,
                'scraped_at': datetime.now().isoformat()
            }
            
            # Extract department
            dept_patterns = [
                r'departamento[:\s]+([^\\n]+)',
                r'escola[:\s]+([^\\n]+)',
                r'unidade[:\s]+([^\\n]+)'
            ]
            
            page_text = soup.get_text()
            for pattern in dept_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    profile_data['department'] = match.group(1).strip()
                    break
            
            # Extract email
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, page_text)
            if emails:
                # Prefer IPT emails
                ipt_emails = [email for email in emails if 'ipt.pt' in email]
                profile_data['email'] = ipt_emails[0] if ipt_emails else emails[0]
            
            # Try OCR for email if not found
            if 'email' not in profile_data:
                profile_data['email'] = self.extract_email_ocr(soup)
            
            # Extract phone
            phone_pattern = r'(\\+351\\s?)?[0-9]{3}\\s?[0-9]{3}\\s?[0-9]{3}'
            phones = re.findall(phone_pattern, page_text)
            if phones:
                profile_data['phone'] = phones[0]
            
            # Extract courses (if available)
            courses = []
            course_indicators = ['disciplina', 'cadeira', 'unidade curricular', 'curso']
            for indicator in course_indicators:
                pattern = f'{indicator}[:\\s]+([^\\n]+)'
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                courses.extend(matches)
            
            if courses:
                profile_data['courses'] = '; '.join(set(courses[:5]))  # Limit to 5 courses
            
            # Extract institutional roles
            roles = []
            role_indicators = ['cargo', 'função', 'responsabilidade', 'comissão']
            for indicator in role_indicators:
                pattern = f'{indicator}[:\\s]+([^\\n]+)'
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                roles.extend(matches)
            
            if roles:
                profile_data['institutional_roles'] = '; '.join(set(roles[:3]))  # Limit to 3 roles
            
            # Extract academic degree
            degree_patterns = [
                r'doutor[a]?',
                r'mestre',
                r'licenciad[oa]',
                r'ph\\.?d',
                r'professor[a]?'
            ]
            
            for pattern in degree_patterns:
                if re.search(pattern, page_text, re.IGNORECASE):
                    profile_data['academic_degree'] = pattern.replace('\\', '')
                    break
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error extracting profile {profile_info['profile_id']}: {e}")
            return None
    
    def extract_email_ocr(self, soup):
        """Extract email using OCR if it's in an image"""
        try:
            # Look for images that might contain email
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src')
                if src and ('email' in src.lower() or 'mail' in src.lower()):
                    img_url = urljoin(self.base_url, src)
                    
                    # Download and process image
                    response = self.session.get(img_url, timeout=10)
                    if response.status_code == 200:
                        image = Image.open(BytesIO(response.content))
                        
                        # Use OCR to extract text
                        text = pytesseract.image_to_string(image)
                        
                        # Look for email in OCR text
                        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}'
                        emails = re.findall(email_pattern, text)
                        if emails:
                            return emails[0]
            
        except Exception as e:
            logger.debug(f"OCR email extraction failed: {e}")
        
        return None
    
    def scrape_all_profiles(self, profile_list):
        """Scrape detailed information for all discovered profiles"""
        logger.info(f"📊 Starting detailed scraping of {len(profile_list)} profiles...")
        
        detailed_profiles = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_profile = {executor.submit(self.extract_detailed_profile, profile): profile 
                               for profile in profile_list}
            
            # Process completed tasks
            for i, future in enumerate(as_completed(future_to_profile)):
                if i % 20 == 0:
                    logger.info(f"   Processed {i}/{len(profile_list)} detailed profiles")
                
                try:
                    result = future.result()
                    if result:
                        detailed_profiles.append(result)
                except Exception as e:
                    logger.error(f"Error processing detailed profile: {e}")
                
                # Rate limiting
                time.sleep(0.1)
        
        logger.info(f"✅ Successfully scraped {len(detailed_profiles)} detailed profiles")
        return detailed_profiles
    
    def save_results(self, profiles_data, filename="faculty_profiles_enhanced.csv"):
        """Save the scraped profiles to CSV"""
        if not profiles_data:
            logger.warning("No profiles to save")
            return
        
        df = pd.DataFrame(profiles_data)
        
        # Create data directory if it doesn't exist
        Path("data").mkdir(exist_ok=True)
        
        output_path = Path("data") / filename
        df.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"💾 Saved {len(df)} profiles to {output_path}")
        
        # Print summary statistics
        logger.info(f"📊 SUMMARY STATISTICS:")
        logger.info(f"   • Total profiles: {len(df)}")
        if 'email' in df.columns:
            logger.info(f"   • Profiles with email: {df['email'].notna().sum()}")
        if 'department' in df.columns:
            logger.info(f"   • Profiles with department: {df['department'].notna().sum()}")
        if 'academic_degree' in df.columns:
            logger.info(f"   • Profiles with academic degree: {df['academic_degree'].notna().sum()}")
        
        return df
    
    def run_comprehensive_scraping(self):
        """Run the complete enhanced scraping process"""
        logger.info("🚀 Starting enhanced IPT profile scraping...")
        
        # Step 1: Discover all valid profile IDs
        valid_profiles = self.discover_all_valid_profiles()
        
        if not valid_profiles:
            logger.error("No valid profiles found! Check network connection and URLs.")
            return None
        
        # Step 2: Save basic profile list
        basic_df = pd.DataFrame(valid_profiles)
        basic_df.to_csv("data/faculty_profiles_discovered.csv", index=False)
        logger.info(f"💾 Saved basic profile list to data/faculty_profiles_discovered.csv")
        
        # Step 3: Scrape detailed information
        detailed_profiles = self.scrape_all_profiles(valid_profiles)
        
        # Step 4: Save detailed results
        final_df = self.save_results(detailed_profiles, "faculty_profiles_enhanced.csv")
        
        logger.info("🎉 Enhanced scraping completed successfully!")
        return final_df

def main():
    """Main function for testing the enhanced scraper"""
    scraper = EnhancedIPTProfileScraper(max_workers=8)  # Adjust based on your system
    
    try:
        # Run comprehensive scraping
        result_df = scraper.run_comprehensive_scraping()
        
        if result_df is not None:
            print(f"\\n✅ SUCCESS: Scraped {len(result_df)} profiles")
            print(f"📊 Sample of results:")
            print(result_df.head())
            
            # Compare with previous results
            try:
                old_df = pd.read_csv("data/faculty_basic.csv")
                print(f"\\n📈 IMPROVEMENT:")
                print(f"   • Previous: {len(old_df)} profiles")
                print(f"   • New: {len(result_df)} profiles")
                print(f"   • Increase: +{len(result_df) - len(old_df)} profiles ({((len(result_df) - len(old_df)) / len(old_df) * 100):.1f}%)")
            except:
                print("\\n📊 No previous data found for comparison")
        
    except KeyboardInterrupt:
        logger.info("\\nScraping interrupted by user")
    except Exception as e:
        logger.error(f"Error during scraping: {e}")

if __name__ == "__main__":
    main()

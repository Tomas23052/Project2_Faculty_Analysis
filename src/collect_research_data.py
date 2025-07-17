import requests
import pandas as pd
import time
import logging
from pathlib import Path
import json
import re
from scholarly import scholarly
from urllib.parse import quote

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchDataCollector:
    """
    Collector for research data from ORCID, Scopus, and Google Scholar.
    """
    
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Setup session for API calls
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; IPT-Faculty-Assessment/1.0)',
            'Accept': 'application/json'
        })
    
    def get_orcid_data(self, orcid_id):
        """
        Get research data from ORCID API.
        """
        if not orcid_id or len(orcid_id) != 19:
            return {}
        
        try:
            # ORCID API endpoints
            base_url = f"https://pub.orcid.org/v3.0/{orcid_id}"
            
            # Get basic profile info
            profile_url = f"{base_url}/person"
            headers = {'Accept': 'application/json'}
            
            logger.debug(f"Fetching ORCID data for {orcid_id}")
            response = self.session.get(profile_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                profile_data = response.json()
                
                # Extract basic info
                orcid_data = {
                    'orcid': orcid_id,
                    'orcid_status': 'found'
                }
                
                # Get name
                name = profile_data.get('name', {})
                if name:
                    given_names = name.get('given-names', {}).get('value', '')
                    family_name = name.get('family-name', {}).get('value', '')
                    orcid_data['orcid_name'] = f"{given_names} {family_name}".strip()
                
                # Get works (publications)
                works_url = f"{base_url}/works"
                works_response = self.session.get(works_url, headers=headers, timeout=30)
                
                if works_response.status_code == 200:
                    works_data = works_response.json()
                    works_list = works_data.get('group', [])
                    
                    orcid_data['orcid_works_count'] = len(works_list)
                    
                    # Count recent works (last 5 years)
                    current_year = 2025
                    recent_works = 0
                    
                    for work_group in works_list[:50]:  # Limit to avoid too many API calls
                        work_summary = work_group.get('work-summary', [])
                        if work_summary:
                            pub_date = work_summary[0].get('publication-date')
                            if pub_date and pub_date.get('year'):
                                pub_year = int(pub_date['year']['value'])
                                if current_year - pub_year <= 5:
                                    recent_works += 1
                    
                    orcid_data['orcid_recent_works'] = recent_works
                
                # Get funding
                funding_url = f"{base_url}/fundings"
                funding_response = self.session.get(funding_url, headers=headers, timeout=30)
                
                if funding_response.status_code == 200:
                    funding_data = funding_response.json()
                    funding_list = funding_data.get('group', [])
                    orcid_data['orcid_funding_count'] = len(funding_list)
                
                return orcid_data
                
            elif response.status_code == 404:
                return {'orcid': orcid_id, 'orcid_status': 'not_found'}
            else:
                logger.warning(f"ORCID API error for {orcid_id}: {response.status_code}")
                return {'orcid': orcid_id, 'orcid_status': 'error'}
                
        except requests.RequestException as e:
            logger.error(f"Network error fetching ORCID data for {orcid_id}: {e}")
            return {'orcid': orcid_id, 'orcid_status': 'network_error'}
        except Exception as e:
            logger.error(f"Error processing ORCID data for {orcid_id}: {e}")
            return {'orcid': orcid_id, 'orcid_status': 'processing_error'}
    
    def search_google_scholar(self, faculty_name, affiliation="IPT"):
        """
        Search for faculty member on Google Scholar using scholarly library.
        """
        try:
            # Clean the name for search
            search_name = faculty_name.strip()
            
            logger.debug(f"Searching Google Scholar for: {search_name}")
            
            # Search for the author
            search_query = scholarly.search_author(f'{search_name} {affiliation}')
            
            # Get first result (most likely match)
            try:
                author = next(search_query)
                
                # Fill in detailed information
                author_detail = scholarly.fill(author, sections=['basics', 'indices'])
                
                scholar_data = {
                    'gs_name': author_detail.get('name', ''),
                    'gs_affiliation': author_detail.get('affiliation', ''),
                    'gs_citedby': author_detail.get('citedby', 0),
                    'gs_hindex': author_detail.get('hindex', 0),
                    'gs_i10index': author_detail.get('i10index', 0),
                    'gs_profile_id': author_detail.get('scholar_id', ''),
                    'gs_status': 'found'
                }
                
                return scholar_data
                
            except StopIteration:
                return {'gs_status': 'not_found'}
                
        except Exception as e:
            logger.warning(f"Error searching Google Scholar for {faculty_name}: {e}")
            return {'gs_status': 'error'}
    
    def load_faculty_data(self):
        """Load faculty data from previous steps"""
        faculty_files = [
            self.data_dir / "faculty_basic.csv",
            self.data_dir / "faculty_profiles.csv"
        ]
        
        dataframes = []
        
        for file_path in faculty_files:
            if file_path.exists():
                logger.info(f"Loading {file_path}")
                df = pd.read_csv(file_path)
                dataframes.append(df)
            else:
                logger.warning(f"File not found: {file_path}")
        
        if not dataframes:
            logger.error("No faculty data files found. Run basic data collection first.")
            return pd.DataFrame()
        
        # Merge dataframes on name
        faculty_df = dataframes[0]
        for df in dataframes[1:]:
            faculty_df = faculty_df.merge(df, on='name', how='outer', suffixes=('', '_dup'))
            
            # Remove duplicate columns
            faculty_df = faculty_df.loc[:, ~faculty_df.columns.str.endswith('_dup')]
        
        return faculty_df
    
    def collect_orcid_metrics(self, faculty_df, delay=1):
        """Collect ORCID metrics for all faculty members"""
        logger.info("Collecting ORCID metrics...")
        
        orcid_data = []
        
        for idx, row in faculty_df.iterrows():
            name = row.get('name', '')
            orcid = row.get('orcid', '')
            
            logger.info(f"Processing ORCID data for {name} ({idx+1}/{len(faculty_df)})")
            
            if orcid and len(str(orcid)) == 19:
                data = self.get_orcid_data(str(orcid))
                data['faculty_name'] = name
                orcid_data.append(data)
            else:
                orcid_data.append({
                    'faculty_name': name,
                    'orcid_status': 'no_orcid'
                })
            
            if delay > 0:
                time.sleep(delay)
        
        return pd.DataFrame(orcid_data)
    
    def collect_scholar_metrics(self, faculty_df, delay=2, limit=None):
        """Collect Google Scholar metrics for faculty members"""
        logger.info("Collecting Google Scholar metrics...")
        
        # Limit for testing
        if limit:
            faculty_df = faculty_df.head(limit)
            logger.info(f"Limited to first {limit} faculty members for testing")
        
        scholar_data = []
        
        for idx, row in faculty_df.iterrows():
            name = row.get('name', '')
            
            logger.info(f"Searching Google Scholar for {name} ({idx+1}/{len(faculty_df)})")
            
            try:
                data = self.search_google_scholar(name)
                data['faculty_name'] = name
                scholar_data.append(data)
                
            except Exception as e:
                logger.error(f"Error processing {name}: {e}")
                scholar_data.append({
                    'faculty_name': name,
                    'gs_status': 'error'
                })
            
            # Longer delay for Google Scholar to avoid rate limiting
            if delay > 0:
                time.sleep(delay)
        
        return pd.DataFrame(scholar_data)
    
    def collect_all_metrics(self, orcid_delay=1, scholar_delay=2, scholar_limit=None, skip_scholar=True):
        """Collect all research metrics and create integrated dataset"""
        logger.info("Starting comprehensive research data collection...")
        
        # Load faculty data
        faculty_df = self.load_faculty_data()
        
        if faculty_df.empty:
            logger.error("No faculty data available. Run basic data collection first.")
            return pd.DataFrame()
        
        logger.info(f"Loaded {len(faculty_df)} faculty members")
        
        # Collect ORCID metrics
        orcid_df = self.collect_orcid_metrics(faculty_df, delay=orcid_delay)
        
        # Collect Google Scholar metrics (skip if requested)
        if not skip_scholar:
            scholar_df = self.collect_scholar_metrics(faculty_df, delay=scholar_delay, limit=scholar_limit)
        else:
            logger.info("Skipping Google Scholar collection (skip_scholar=True)")
            scholar_df = pd.DataFrame()
        
        # Merge all data
        research_df = faculty_df.copy()
        
        if not orcid_df.empty:
            research_df = research_df.merge(
                orcid_df, 
                left_on='name', 
                right_on='faculty_name', 
                how='left'
            ).drop('faculty_name', axis=1, errors='ignore')
        
        if not scholar_df.empty:
            research_df = research_df.merge(
                scholar_df, 
                left_on='name', 
                right_on='faculty_name', 
                how='left'
            ).drop('faculty_name', axis=1, errors='ignore')
        
        # Save integrated dataset
        output_path = self.data_dir / "faculty_research_metrics.csv"
        research_df.to_csv(output_path, index=False, encoding='utf-8')
        
        logger.info(f"Research metrics collection completed!")
        logger.info(f"Integrated dataset saved to {output_path}")
        logger.info(f"Total faculty with data: {len(research_df)}")
        
        # Print summary statistics
        self.print_collection_summary(research_df)
        
        return research_df
    
    def print_collection_summary(self, df):
        """Print summary of collected research data"""
        logger.info("\n=== RESEARCH DATA COLLECTION SUMMARY ===")
        
        total_faculty = len(df)
        logger.info(f"Total faculty processed: {total_faculty}")
        
        # ORCID statistics
        if 'orcid_status' in df.columns:
            orcid_found = (df['orcid_status'] == 'found').sum()
            orcid_not_found = (df['orcid_status'] == 'not_found').sum()
            no_orcid = (df['orcid_status'] == 'no_orcid').sum()
            
            logger.info(f"\nORCID Status:")
            logger.info(f"  - Found: {orcid_found} ({orcid_found/total_faculty*100:.1f}%)")
            logger.info(f"  - Not found: {orcid_not_found}")
            logger.info(f"  - No ORCID provided: {no_orcid}")
            
            if 'orcid_works_count' in df.columns:
                avg_works = df['orcid_works_count'].mean()
                logger.info(f"  - Average publications: {avg_works:.1f}")
        
        # Google Scholar statistics
        if 'gs_status' in df.columns:
            gs_found = (df['gs_status'] == 'found').sum()
            gs_not_found = (df['gs_status'] == 'not_found').sum()
            
            logger.info(f"\nGoogle Scholar Status:")
            logger.info(f"  - Found: {gs_found} ({gs_found/len(df)*100:.1f}%)")
            logger.info(f"  - Not found: {gs_not_found}")
            
            if 'gs_citedby' in df.columns:
                avg_citations = df['gs_citedby'].mean()
                avg_hindex = df['gs_hindex'].mean()
                logger.info(f"  - Average citations: {avg_citations:.1f}")
                logger.info(f"  - Average h-index: {avg_hindex:.1f}")

def main():
    """Main function for testing"""
    collector = ResearchDataCollector()
    
    # Collect research metrics (limited for testing)
    research_df = collector.collect_all_metrics(
        orcid_delay=1,
        scholar_delay=3,  # Longer delay for Google Scholar
        scholar_limit=5   # Test with only 5 faculty members
    )
    
    if not research_df.empty:
        print(f"\nSample of collected research data:")
        print(research_df[['name', 'orcid_status', 'orcid_works_count', 'gs_status', 'gs_citedby']].head())

if __name__ == "__main__":
    main()

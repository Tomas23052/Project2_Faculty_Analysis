#!/usr/bin/env python3
"""
Main script to collect all IPT faculty data.
Run this script to execute the complete data collection pipeline.
"""

import logging
import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent))

from parse_hr_pdfs import IPTHRParser
from extract_basic_info import IPTProfileScraper
from collect_research_data import ResearchDataCollector

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main data collection pipeline"""
    logger.info("=" * 60)
    logger.info("IPT FACULTY PERFORMANCE DATA COLLECTION PIPELINE")
    logger.info("=" * 60)
    
    try:
        # Step 1: Parse HR PDFs
        logger.info("\n🔍 STEP 1: Parsing HR PDF files...")
        hr_parser = IPTHRParser()
        faculty_basic = hr_parser.process_hr_files()
        
        if faculty_basic.empty:
            logger.warning("No basic faculty data extracted from PDFs.")
            logger.info("Please ensure HR PDF files are placed in data/raw/ directory")
            logger.info("Continuing with profile scraping...")
        else:
            logger.info(f"✅ Successfully extracted {len(faculty_basic)} faculty records from HR PDFs")
        
        # Step 2: Scrape IPT profiles
        logger.info("\n🕷️  STEP 2: Scraping IPT 'Quem é Quem' profiles...")
        profile_scraper = IPTProfileScraper()
        
        # Start with a limited number for testing
        faculty_profiles = profile_scraper.scrape_all_profiles(limit=10, delay=2)
        
        if faculty_profiles.empty:
            logger.warning("No faculty profiles scraped from IPT website")
        else:
            logger.info(f"✅ Successfully scraped {len(faculty_profiles)} faculty profiles")
        
        # Step 3: Collect research metrics
        logger.info("\n📚 STEP 3: Collecting research metrics...")
        research_collector = ResearchDataCollector()
        
        # Collect with conservative limits for testing
        research_metrics = research_collector.collect_all_metrics(
            orcid_delay=2,      # 2 second delay for ORCID API
            scholar_delay=5,    # 5 second delay for Google Scholar
            scholar_limit=5     # Only test with 5 faculty members
        )
        
        if research_metrics.empty:
            logger.warning("No research metrics collected")
        else:
            logger.info(f"✅ Successfully collected research metrics for {len(research_metrics)} faculty")
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("DATA COLLECTION SUMMARY")
        logger.info("=" * 60)
        
        if not faculty_basic.empty:
            logger.info(f"📄 HR Data: {len(faculty_basic)} records")
        
        if not faculty_profiles.empty:
            logger.info(f"🌐 Profile Data: {len(faculty_profiles)} records")
            
        if not research_metrics.empty:
            logger.info(f"📊 Research Metrics: {len(research_metrics)} records")
            
            # Show research stats
            if 'orcid_status' in research_metrics.columns:
                orcid_found = (research_metrics['orcid_status'] == 'found').sum()
                logger.info(f"   - ORCID profiles found: {orcid_found}")
            
            if 'gs_status' in research_metrics.columns:
                gs_found = (research_metrics['gs_status'] == 'found').sum()
                logger.info(f"   - Google Scholar profiles found: {gs_found}")
        
        logger.info("\n🚀 Data collection completed!")
        logger.info("Run the dashboard with: streamlit run src/dashboard.py")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  Data collection interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Error during data collection: {e}")
        raise

if __name__ == "__main__":
    main()

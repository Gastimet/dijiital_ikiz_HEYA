from zenml import pipeline, step
import logging
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import crawlers
from Crawlers.Ocr_to_text import PDFTextExtractor
from Crawlers.Wikipedia_Crawler import WikiCrawler

@step
def ocr_extraction_step(pdf_path: str) -> Optional[str]:
    """
    Step to extract text from PDF using OCR.
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        Optional[str]: Extracted text from the PDF
    """
    try:
        extractor = PDFTextExtractor()
        # Assuming your PDFTextExtractor has a method to extract text
        extracted_text = extractor.extract_text(pdf_path)
        logger.info("Successfully completed OCR extraction")
        return extracted_text
    except Exception as e:
        logger.error(f"Error in OCR extraction: {str(e)}")
        return None

@step
def wikipedia_crawl_step(search_query: str) -> List[str]:
    """
    Step to crawl Wikipedia articles.
    
    Args:
        search_query: Search term for Wikipedia
    
    Returns:
        List[str]: List of paragraphs from Wikipedia
    """
    try:
        crawler = WikiCrawler()
        paragraphs = crawler.main(search_query)  # Assuming main() accepts a search query
        logger.info(f"Successfully crawled Wikipedia for: {search_query}")
        return paragraphs
    except Exception as e:
        logger.error(f"Error in Wikipedia crawling: {str(e)}")
        return []

@step
def data_processing_step(ocr_text: Optional[str], wiki_paragraphs: List[str]) -> dict:
    """
    Step to process and combine data from different sources.
    
    Args:
        ocr_text: Text extracted from PDF
        wiki_paragraphs: Paragraphs from Wikipedia
    
    Returns:
        dict: Processed data
    """
    processed_data = {
        "ocr_content": ocr_text if ocr_text else "",
        "wiki_content": wiki_paragraphs,
        "total_wiki_paragraphs": len(wiki_paragraphs),
        "has_ocr_data": ocr_text is not None
    }
    logger.info("Data processing completed")
    return processed_data

@pipeline
def digital_twin_pipeline(pdf_path: str = "./data/sample.pdf", 
                         wiki_search_query: str = "digital twin"):
    """
    Main pipeline that orchestrates the digital twin data collection process.
    
    Args:
        pdf_path: Path to the PDF file for OCR
        wiki_search_query: Search query for Wikipedia crawling
    """
    # Execute steps
    ocr_result = ocr_extraction_step(pdf_path)
    wiki_result = wikipedia_crawl_step(wiki_search_query)
    final_result = data_processing_step(ocr_result, wiki_result)
    return final_result

if __name__ == "__main__":
    # Run the pipeline
    try:
        logger.info("Starting digital twin pipeline")
        pipeline_instance = digital_twin_pipeline()
        results = pipeline_instance()
        logger.info("Pipeline completed successfully")
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
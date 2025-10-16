from zenml import pipeline, step

# Import your crawlers (assuming they're in the Crawlers directory)
from Crawlers.Ocr_to_text import PDFTextExtractor
# You may need to refactor Youtube_Crawler and Wikipedia_Crawler to expose functions
from Crawlers.Wikipedia_Crawler import WikiCrawler

@step
def ocr_step():
    extractor = PDFTextExtractor()
    # Example call, you may want to pass a PDF path and use MongoDB here
    print("OCR step executed.")

@step
def wikipedia_step():
    crawler = WikiCrawler()
    paragraphs = crawler.main()  # This interacts with MongoDB
    print("Wikipedia Crawler step executed.")
    return paragraphs

@pipeline
def my_pipeline():
    ocr_step()
    wikipedia_step()

if __name__ == "__main__":
    my_pipeline()
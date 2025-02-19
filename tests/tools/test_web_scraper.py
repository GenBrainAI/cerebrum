import pytest
from src.server.tools.web_scraper_tool import WebScraperTool

@pytest.mark.asyncio
async def test_scrape_page():
    """Test scraping a single page."""
    scraper = WebScraperTool()
    url = "https://example.com"
    
    result = await scraper.scrape_page(url)
    
    assert result is not None
    assert 'url' in result
    assert 'path' in result
    assert 'content' in result
    assert 'metadata' in result
    assert result['url'] == url
    assert result['path'] == url
    assert isinstance(result['content'], str)
    assert len(result['content']) > 0

@pytest.mark.asyncio
async def test_scrape_page_with_invalid_url():
    """Test scraping with invalid URL."""
    scraper = WebScraperTool()
    
    with pytest.raises(Exception):
        await scraper.scrape_page("invalid-url")

@pytest.mark.asyncio
async def test_metadata_format():
    """Test that metadata values are properly formatted."""
    scraper = WebScraperTool()
    url = "https://example.com"
    
    result = await scraper.scrape_page(url)
    
    # Verify metadata structure
    assert 'metadata' in result
    metadata = result['metadata']
    
    # Check metadata types
    assert isinstance(metadata['title'], str)
    assert isinstance(metadata['description'], str)
    
    # Verify no lists in metadata values
    for key, value in metadata.items():
        assert isinstance(value, (str, int, float, bool)), f"Metadata {key} has invalid type: {type(value)}" 
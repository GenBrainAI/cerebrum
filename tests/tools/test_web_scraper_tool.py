import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from bs4 import BeautifulSoup
from src.server.tools.web_scraper_tool import WebScraperTool
from src.server.controllers.task_observability import TaskObservabilityManager, ObservabilityLevel
import time

@pytest.fixture
def mock_page_content():
    """Provide mock HTML content for testing."""
    return """
    <html>
        <head>
            <title>Main Title</title>
        </head>
        <body>
            <header>Header Content</header>
            <nav>Navigation</nav>
            <main>
                <h1>Main Title</h1>
                <p>Main Content</p>
                <pre class="language-python">print("Hello World")</pre>
            </main>
            <footer>Footer Content</footer>
        </body>
    </html>
    """

@pytest.fixture
def mock_playwright():
    mock_instance = AsyncMock()
    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    
    # Set up the mock chain
    mock_instance.chromium.launch.return_value = mock_browser
    mock_browser.new_page.return_value = mock_page
    mock_page.goto = AsyncMock()
    
    # Set up context manager
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock()
    
    return mock_instance

@pytest.fixture
def mock_observability():
    return MagicMock(spec=TaskObservabilityManager)

@pytest.fixture
def mock_page():
    mock = AsyncMock()
    mock.goto = AsyncMock()
    mock.content = AsyncMock()
    mock.title = AsyncMock()
    return mock

@pytest.fixture
def mock_browser(mock_page):
    mock = AsyncMock()
    mock.new_page = AsyncMock(return_value=mock_page)
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock()
    mock.close = AsyncMock()
    return mock

@pytest.mark.asyncio
async def test_domain_restriction(mock_playwright, mock_observability):
    scraper = WebScraperTool(allowed_domains=["example.com"], observability=mock_observability)
    with pytest.raises(ValueError, match="Domain not allowed"):
        await scraper.scrape_page("https://not-allowed.com")

@pytest.mark.asyncio
@patch('src.server.tools.web_scraper_tool.async_playwright')
async def test_content_filtering(mock_async_playwright, mock_playwright):
    mock_async_playwright.return_value = mock_playwright
    
    # Set up the mock page
    mock_page = mock_playwright.chromium.launch.return_value.new_page.return_value
    mock_content = """
        <html>
            <head>
                <title>Main Title</title>
                <meta name="description" content="Test description">
            </head>
            <body>
                <header>Header Content</header>
                <main>
                    <h1>Main Title</h1>
                    <p>Main Content</p>
                    <pre class="language-python">print("Hello World")</pre>
                </main>
                <footer>Footer Content</footer>
            </body>
        </html>
    """
    mock_page.content.return_value = mock_content
    mock_page.title.return_value = "Main Title"
    
    scraper = WebScraperTool()
    result = await scraper.scrape_page("https://example.com")
    
    # Check content filtering
    assert 'Main Title' in result['content']
    assert 'Main Content' in result['content']
    assert 'Header Content' not in result['content']
    assert 'Footer Content' not in result['content']
    
    # Check code blocks
    assert len(result['code_blocks']) == 1
    assert result['code_blocks'][0]['language'] == 'python'
    assert result['code_blocks'][0]['content'] == 'print("Hello World")'
    
    # Check metadata
    assert result['metadata']['title'] == 'Main Title'
    assert result['metadata']['description'] == 'Test description'

@pytest.mark.asyncio
async def test_rate_limiting(mock_playwright, mock_observability):
    scraper = WebScraperTool(observability=mock_observability)
    start_time = time.time()
    await scraper.scrape_page("https://example.com")
    await scraper.scrape_page("https://example.com")
    end_time = time.time()
    assert end_time - start_time >= 1  # At least 1 second delay between requests

@pytest.mark.asyncio
@patch('src.server.tools.web_scraper_tool.async_playwright')
async def test_scrape_langchain_tools(mock_async_playwright, mock_playwright):
    mock_async_playwright.return_value = mock_playwright
    
    # Set up the mock page
    mock_page = mock_playwright.chromium.launch.return_value.new_page.return_value
    mock_content = """
        <html>
            <head>
                <title>🦜️🔗 LangChain</title>
            </head>
            <body>
                <main>
                    <h1>🦜️🔗 LangChain</h1>
                    <p>Tools are utilities designed to be used within LangChain.</p>
                </main>
            </body>
        </html>
    """
    mock_page.content.return_value = mock_content
    mock_page.title.return_value = "🦜️🔗 LangChain"
    
    scraper = WebScraperTool()
    result = await scraper.scrape_page("https://python.langchain.com/docs/integrations/tools/")
    
    assert '🦜️🔗 LangChain' in result['content']
    assert 'Tools are utilities' in result['content']
    assert result['url'] == "https://python.langchain.com/docs/integrations/tools/"

@pytest.mark.asyncio
@patch('src.server.tools.web_scraper_tool.async_playwright')
async def test_scrape_langchain_tool_details(mock_async_playwright, mock_playwright):
    # Set up the mock page
    mock_page = AsyncMock()
    mock_content = """
        <html>
            <head>
                <title>Python REPL | 🦜️🔗 LangChain</title>
                <meta name="description" content="Documentation for Python REPL Tool">
            </head>
            <body>
                <main>
                    <h1>Python REPL Tool</h1>
                    <p>The Python REPL tool allows you to execute Python code.</p>
                </main>
            </body>
        </html>
    """
    
    # Set up the mock returns for async methods
    mock_page.content.return_value = mock_content
    mock_page.title.return_value = "Python REPL | 🦜️🔗 LangChain"
    mock_page.goto = AsyncMock()

    # Create a proper mock for observability
    mock_observability = MagicMock()
    mock_observability.add_entry = MagicMock()

    # Set up the mock browser to be used as a context manager
    mock_browser = AsyncMock()
    mock_browser.new_page.return_value = mock_page
    mock_browser.close = AsyncMock()
    mock_playwright.chromium.launch.return_value = mock_browser

    # Set up the async context manager
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_playwright
    mock_context.__aexit__.return_value = None
    mock_async_playwright.return_value = mock_context

    scraper = WebScraperTool(observability=mock_observability)
    result = await scraper.scrape_page("https://python.langchain.com/docs/integrations/tools/python")

    assert result['metadata']['title'] == "Python REPL | 🦜️🔗 LangChain"
    assert mock_observability.add_entry.called

@pytest.mark.asyncio
@patch('src.server.tools.web_scraper_tool.async_playwright')
async def test_extract_tool_metadata(mock_async_playwright, mock_playwright):
    mock_async_playwright.return_value = mock_playwright
    
    # Set up the mock page
    mock_page = mock_playwright.chromium.launch.return_value.new_page.return_value
    mock_content = """
        <html>
            <head>
                <title>Python REPL Tool</title>
                <meta name="description" content="Tool for executing Python commands">
            </head>
            <body>
                <main>
                    <h1>Python REPL Tool</h1>
                    <p>A tool for executing Python commands and capturing their output.</p>
                </main>
            </body>
        </html>
    """
    mock_page.content.return_value = mock_content
    mock_page.title.return_value = "Python REPL Tool"
    
    scraper = WebScraperTool()
    result = await scraper.scrape_page("https://python.langchain.com/docs/integrations/tools/python_repl")
    
    assert result['metadata']['title'] == "Python REPL Tool"
    assert result['metadata']['description'] == "Tool for executing Python commands"

if __name__ == '__main__':
    asyncio.run(test_scrape_langchain_tools(mock_playwright()))
    asyncio.run(test_scrape_langchain_tool_details(mock_playwright(), mock_observability()))
    asyncio.run(test_extract_tool_metadata(mock_playwright())) 
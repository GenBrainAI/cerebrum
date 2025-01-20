"""URL tools for web scraping and content fetching."""

import asyncio
from typing import Optional, Dict, Any, List, Callable
import logging
from urllib.parse import urlparse
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import aiohttp
import re
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter implementation."""
    
    def __init__(self, calls: int, period: float):
        """
        Initialize rate limiter.
        
        Args:
            calls: Number of calls allowed
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period
        self.timestamps = []
        
    async def acquire(self):
        """Acquire a rate limit slot."""
        now = datetime.now()
        
        # Remove timestamps older than our period
        self.timestamps = [ts for ts in self.timestamps 
                         if now - ts < timedelta(seconds=self.period)]
        
        if len(self.timestamps) >= self.calls:
            # We need to wait
            wait_time = self.period - (now - self.timestamps[0]).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                # After waiting, get new timestamp
                now = datetime.now()
                
        self.timestamps.append(now)

def rate_limit(calls: int, period: float):
    """Rate limiting decorator for async functions."""
    limiter = RateLimiter(calls, period)
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await limiter.acquire()
            return await func(*args, **kwargs)
        return wrapper
    return decorator

class URLTools:
    """Tools for URL operations and web scraping."""
    
    def __init__(self, 
                 rate_limit: int = 10,  # requests per minute
                 respect_robots: bool = True,
                 allowed_domains: Optional[List[str]] = None):
        """
        Initialize URL tools.
        
        Args:
            rate_limit: Maximum requests per minute
            respect_robots: Whether to respect robots.txt
            allowed_domains: List of allowed domains (None for all)
        """
        self.rate_limit = rate_limit
        self.respect_robots = respect_robots
        self.allowed_domains = allowed_domains or []
        
    def _is_allowed_domain(self, url: str) -> bool:
        """Check if URL domain is allowed."""
        if not self.allowed_domains:
            return True
        domain = urlparse(url).netloc
        return any(domain.endswith(d) for d in self.allowed_domains)
    
    @rate_limit(calls=10, period=60)
    async def get_data_from_url(self, url: str, 
                               use_js: bool = False,
                               selectors: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Fetch data from a URL with optional JavaScript rendering.
        
        Args:
            url: URL to fetch
            use_js: Whether to use JavaScript rendering
            selectors: Optional CSS selectors to extract specific content
            
        Returns:
            Dictionary containing content and metadata
        """
        if not self._is_allowed_domain(url):
            raise ValueError(f"Domain not allowed: {urlparse(url).netloc}")
            
        try:
            if use_js:
                return await self._fetch_with_playwright(url, selectors)
            else:
                return await self._fetch_with_requests(url, selectors)
                
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            raise
            
    async def _fetch_with_playwright(self, url: str,
                                   selectors: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Fetch URL content using Playwright for JavaScript rendering."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            try:
                # Navigate and wait for network idle
                await page.goto(url, wait_until='networkidle')
                await page.wait_for_load_state('networkidle')
                
                # Get rendered content
                content = await page.content()
                title = await page.title()
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract metadata
                meta_tags = soup.find_all('meta')
                metadata = {
                    'title': title,
                    'url': url,
                    'description': next((tag.get('content', '') for tag in meta_tags 
                                      if tag.get('name', '').lower() == 'description'), ''),
                    'keywords': next((tag.get('content', '') for tag in meta_tags 
                                   if tag.get('name', '').lower() == 'keywords'), '')
                }
                
                # Extract selected content if specified
                selected_content = {}
                if selectors:
                    for key, selector in selectors.items():
                        elements = await page.query_selector_all(selector)
                        selected_content[key] = [
                            await elem.inner_text() for elem in elements
                        ]
                
                # Get main content
                main_content = soup.find('main') or soup.find('article') or soup.body
                content_text = main_content.get_text(strip=True) if main_content else ''
                
                return {
                    'content': content_text,
                    'html': content,
                    'metadata': metadata,
                    'selected_content': selected_content
                }
                
            finally:
                await browser.close()
                
    async def _fetch_with_requests(self, url: str,
                                 selectors: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Fetch URL content using aiohttp for basic requests."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                content = await response.text()
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                
                # Extract metadata
                title = soup.title.string if soup.title else ''
                meta_tags = soup.find_all('meta')
                metadata = {
                    'title': title,
                    'url': url,
                    'description': next((tag.get('content', '') for tag in meta_tags 
                                      if tag.get('name', '').lower() == 'description'), ''),
                    'keywords': next((tag.get('content', '') for tag in meta_tags 
                                   if tag.get('name', '').lower() == 'keywords'), '')
                }
                
                # Extract selected content if specified
                selected_content = {}
                if selectors:
                    for key, selector in selectors.items():
                        elements = soup.select(selector)
                        selected_content[key] = [elem.get_text(strip=True) for elem in elements]
                
                # Get main content
                main_content = soup.find('main') or soup.find('article') or soup.body
                content_text = main_content.get_text(strip=True) if main_content else ''
                
                return {
                    'content': content_text,
                    'html': content,
                    'metadata': metadata,
                    'selected_content': selected_content
                }
                
    async def extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """Extract code blocks from HTML or Markdown content."""
        # Find Markdown code blocks
        md_blocks = re.findall(r'```(\w*)\n(.*?)```', content, re.DOTALL)
        
        # Find HTML code blocks
        soup = BeautifulSoup(content, 'html.parser')
        html_blocks = [(pre.get('class', [''])[0], pre.get_text()) 
                      for pre in soup.find_all('pre')]
        
        # Combine and format results
        code_blocks = []
        
        for lang, code in md_blocks:
            code_blocks.append({
                'language': lang or 'text',
                'code': code.strip()
            })
            
        for lang, code in html_blocks:
            code_blocks.append({
                'language': lang or 'text',
                'code': code.strip()
            })
            
        return code_blocks
        
    async def get_documentation(self, url: str) -> Dict[str, Any]:
        """
        Specialized method for fetching documentation pages.
        
        Args:
            url: Documentation URL to fetch
            
        Returns:
            Dictionary containing parsed documentation
        """
        # Define selectors for common documentation elements
        doc_selectors = {
            'headings': 'h1, h2, h3, h4, h5, h6',
            'code_blocks': 'pre code',
            'examples': '.example, .examples, .demo',
            'api_sections': '.api, .endpoint, .method'
        }
        
        # Fetch with JavaScript rendering for modern doc sites
        result = await self.get_data_from_url(url, use_js=True, selectors=doc_selectors)
        
        # Extract code blocks
        code_blocks = await self.extract_code_blocks(result['html'])
        
        # Structure the documentation
        return {
            'title': result['metadata']['title'],
            'description': result['metadata']['description'],
            'content': result['content'],
            'headings': result['selected_content'].get('headings', []),
            'code_blocks': code_blocks,
            'examples': result['selected_content'].get('examples', []),
            'api_sections': result['selected_content'].get('api_sections', [])
        }

    async def fetch_documentation(self, url: str) -> dict:
        """Fetch documentation from URL.
        
        Args:
            url: The URL to fetch documentation from.
            
        Returns:
            A dictionary containing the status, message, and content.
        """
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return {
                        "status": "error",
                        "message": f"Failed to fetch documentation: HTTP {response.status}",
                        "content": None
                    }
                    
                content = await response.text()
                return {
                    "status": "success",
                    "message": f"Documentation fetched from {url}",
                    "content": content
                }
        except Exception as e:
            logger.error(f"Error fetching documentation: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to fetch documentation: {str(e)}",
                "content": None
            }
            
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close() 
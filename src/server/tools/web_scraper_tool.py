"""Web scraper tool for extracting content from websites."""

from typing import Optional, List, Dict, Any
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import asyncio
import logging
import re
from datetime import datetime
from ..controllers.task_observability import TaskObservabilityManager, ObservabilityLevel

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter implementation."""
    
    def __init__(self, requests_per_second: float = 1.0):
        self.delay = 1.0 / requests_per_second
        self.last_request_time = 0.0

    async def wait(self):
        """Wait for rate limit."""
        now = asyncio.get_event_loop().time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.delay:
            await asyncio.sleep(self.delay - time_since_last)
        self.last_request_time = now

class ContentFilter:
    """Filter for removing unwanted content."""
    
    def __init__(self):
        pass
    
    def clean_html(self, html_content: str) -> str:
        """Clean HTML content by removing unwanted elements and extracting text."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Print debug info
        print("\nParsed HTML:", soup.prettify())

        # Remove unwanted elements
        for element in soup.find_all(['header', 'footer', 'nav', 'script', 'style']):
            element.decompose()

        # Find main content
        main_content = soup.find('main')
        if main_content:
            content = main_content
        else:
            content = soup.find('body') or soup

        # Extract text from remaining elements
        text_content = []
        for tag in content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
            if tag.name != 'pre':  # Skip pre tags to avoid code blocks
                text = tag.get_text(strip=True)
                if text:
                    text_content.append(text)

        # Print debug info
        print("\nExtracted Text:", text_content)

        return ' '.join(text_content)

    def extract_code_blocks(self, html_content: str) -> List[Dict[str, str]]:
        """Extract code blocks from HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        code_blocks = []

        for pre in soup.find_all('pre'):
            code = pre.find('code')
            if code:
                language = code.get('class', [''])[0] if code.get('class') else ''
                content = code.get_text(strip=True)
                code_blocks.append({
                    'language': language,
                    'content': content
                })

        return code_blocks

class WebScraperTool:
    """A tool for scraping web content with JavaScript rendering support."""

    def __init__(self, allowed_domains: Optional[List[str]] = None, max_depth: int = 3, max_pages: int = 100, headless: bool = True, observability: Optional[TaskObservabilityManager] = None):
        self.allowed_domains = allowed_domains
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.headless = headless
        self.observability = observability
        self.rate_limiter = RateLimiter()
        self.last_request_time = 0
        self.url_pattern = None  # Add pattern for URL matching

    def _log_observation(self, message: str, level: ObservabilityLevel = ObservabilityLevel.INFO):
        """Log an observation if observability is enabled."""
        if self.observability:
            self.observability.add_entry(message, level)

    def _is_allowed_domain(self, url: str) -> bool:
        if not self.allowed_domains:
            return True
        domain = urlparse(url).netloc
        return any(allowed_domain in domain for allowed_domain in self.allowed_domains)

    def _matches_pattern(self, url: str) -> bool:
        """Check if URL matches the specified pattern."""
        if not self.url_pattern:
            return True
        return bool(re.search(self.url_pattern, url))

    async def get_urls_to_scrape(self, start_url: str) -> List[str]:
        """Get all URLs to scrape starting from a given URL."""
        try:
            self._log_observation(f"Starting URL discovery from: {start_url}")
            
            urls_to_scrape = set()
            visited = set()
            queue = [start_url]

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                
                # Increase navigation timeout
                page.set_default_navigation_timeout(30000)
                
                while queue and len(urls_to_scrape) < self.max_pages:
                    url = queue.pop(0)
                    if url in visited:
                        continue
                        
                    visited.add(url)
                    self._log_observation(f"Checking URL: {url}")
                    
                    try:
                        # Visit the page
                        await page.goto(url, wait_until='networkidle')
                        
                        # Get all links using JavaScript evaluation for better coverage
                        links = await page.evaluate('''() => {
                            const links = Array.from(document.querySelectorAll('a[href]'));
                            return links.map(link => {
                                return {
                                    href: link.href,
                                    text: link.textContent.trim(),
                                    isNavLink: link.closest('nav') !== null
                                };
                            });
                        }''')
                        
                        self._log_observation(f"Found {len(links)} total links on page {url}")
                        
                        for link in links:
                            href = link['href']
                            # Normalize URL and remove any fragments
                            full_url = urljoin(start_url, href.split('#')[0])
                            
                            # Skip empty or javascript URLs
                            if not full_url or full_url.startswith('javascript:'):
                                continue
                                
                            # Check if URL matches our criteria
                            if (self._is_allowed_domain(full_url) and 
                                self._matches_pattern(full_url) and 
                                full_url not in visited):
                                
                                # Add debug info about matched URL
                                relative_path = full_url.replace('https://python.langchain.com/docs/integrations/tools/', '')
                                self._log_observation(f"Found matching URL: /{relative_path}")
                                
                                urls_to_scrape.add(full_url)
                                queue.append(full_url)
                            
                            # If it's a navigation link but doesn't match pattern, still visit it to find more links
                            elif (link['isNavLink'] and 
                                  self._is_allowed_domain(full_url) and 
                                  full_url not in visited and 
                                  'integrations/tools' in full_url):
                                queue.append(full_url)
                                self._log_observation(f"Adding navigation URL to queue: {full_url}")
                                
                    except Exception as e:
                        self._log_observation(f"Error processing {url}: {str(e)}", ObservabilityLevel.ERROR)
                        continue

                await browser.close()
                
            self._log_observation(f"URL discovery completed. Found {len(urls_to_scrape)} URLs matching pattern")
            # Sort URLs for consistent ordering
            return sorted(list(urls_to_scrape))
            
        except Exception as e:
            self._log_observation(f"Error during URL discovery: {str(e)}", ObservabilityLevel.ERROR)
            raise

    def _extract_content(self, soup: BeautifulSoup) -> str:
        content = []
        main_tag = soup.find('main')
        if main_tag:
            for tag in main_tag.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
                if tag.text.strip():
                    content.append(tag.text.strip())
        else:
            for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']):
                if tag.text.strip():
                    content.append(tag.text.strip())
        return ' '.join(content)

    def _extract_code_blocks(self, soup: BeautifulSoup) -> List[Dict[str, Optional[str]]]:
        code_blocks = []
        for pre in soup.find_all('pre'):
            code_class = pre.get('class', [])
            language = None
            if code_class and 'language-' in code_class[0]:
                language = code_class[0].replace('language-', '')
            code_blocks.append({
                'language': language,
                'content': pre.text.strip()
            })
        return code_blocks

    def _extract_metadata(self, soup: BeautifulSoup, page_title: str, selectors: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        metadata = {
            'title': page_title,
            'description': []
        }
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            metadata['description'].append(meta_desc.get('content', ''))

        if selectors:
            for key, selector in selectors.items():
                elements = soup.select(selector)
                metadata[key] = [el.text.strip() for el in elements if el.text.strip()]

        return metadata

    async def scrape_page(self, url: str, metadata_selectors: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        if not self._is_allowed_domain(url):
            if self.observability:
                self.observability.add_entry(f"Domain not allowed: {url}", ObservabilityLevel.ERROR)
            raise ValueError(f"Domain not allowed: {url}")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url)
                
                if self.observability:
                    self.observability.add_entry(f"Successfully loaded page: {url}", ObservabilityLevel.INFO)

                # Get the page content and title
                html_content = await page.content()
                page_title = await page.title()

                # Parse the HTML content
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract content, code blocks, and metadata
                content = self._extract_content(soup)
                code_blocks = self._extract_code_blocks(soup)
                metadata = self._extract_metadata(soup, page_title, metadata_selectors)

                result = {
                    'url': url,
                    'content': content,
                    'code_blocks': code_blocks,
                    'metadata': metadata
                }

                if self.observability:
                    self.observability.add_entry("Successfully extracted content and metadata", ObservabilityLevel.INFO)

                await browser.close()
                return result

        except Exception as e:
            if self.observability:
                self.observability.add_entry(f"Error scraping page: {str(e)}", ObservabilityLevel.ERROR)
            raise

    async def scrape_site(self, start_url: str, selectors: Optional[Dict[str, str]] = None) -> List[Dict]:
        """Scrape multiple pages starting from a given URL."""
        visited = set()
        results = []
        queue = [(start_url, 0)]

        while queue and len(visited) < self.max_pages:
            url, depth = queue.pop(0)
            if url in visited or depth > self.max_depth:
                continue

            try:
                result = await self.scrape_page(url, selectors)
                results.append(result)
                visited.add(url)

                if depth < self.max_depth:
                    # Add new URLs to the queue
                    soup = BeautifulSoup(result['content'], 'html.parser')
                    for link in soup.find_all('a'):
                        href = link.get('href')
                        if href and href.startswith('http') and self._is_allowed_domain(href):
                            queue.append((href, depth + 1))

            except Exception as e:
                if self.observability:
                    self.observability.add_entry(f"Error scraping page {url}: {str(e)}", ObservabilityLevel.ERROR)
                continue

        return results 
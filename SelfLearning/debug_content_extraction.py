#!/usr/bin/env python3
"""
Debug script to analyze content extraction and find the main article content.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from web_crawler.core.extractor import ContentExtractor


async def debug_content_extraction(url: str):
    """Debug content extraction for a specific URL."""
    
    print(f"🔍 Debugging content extraction for: {url}")
    print("=" * 60)
    
    # Fetch the page
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html_content = await response.text()
    
    print(f"📄 Page size: {len(html_content)} characters")
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove scripts and styles
    for element in soup(["script", "style"]):
        element.decompose()
    
    print(f"\n🔍 Looking for main content selectors...")
    
    # Test different content selectors
    content_selectors = [
        ('article', 'article'),
        ('main', 'main'),
        ('[role="main"]', '[role="main"]'),
        ('.article', '.article'),
        ('.story', '.story'),
        ('.post', '.post'),
        ('.content', '.content'),
        ('.main-content', '.main-content'),
        ('.article-content', '.article-content'),
        ('.story-content', '.story-content'),
        ('.Normal', '.Normal'),  # Times of India specific
        ('.article-body', '.article-body'),
        ('.post-content', '.post-content'),
        ('#main', '#main'),
        ('#content', '#content')
    ]
    
    found_elements = []
    
    for name, selector in content_selectors:
        elements = soup.select(selector)
        if elements:
            for i, element in enumerate(elements):
                text = element.get_text(strip=True)
                if len(text) > 100:  # Only consider substantial content
                    found_elements.append({
                        'selector': f"{name}[{i}]" if len(elements) > 1 else name,
                        'element': element,
                        'text_length': len(text),
                        'text_preview': text[:200] + "..." if len(text) > 200 else text
                    })
                    print(f"✅ Found {name}[{i}]: {len(text)} chars - {text[:100]}...")
    
    if not found_elements:
        print("❌ No main content selectors found, analyzing page structure...")
        
        # Find all divs with substantial text
        divs = soup.find_all('div')
        div_candidates = []
        
        for i, div in enumerate(divs):
            text = div.get_text(strip=True)
            if len(text) > 500:  # Substantial content
                # Calculate text density
                html_length = len(str(div))
                text_density = len(text) / html_length if html_length > 0 else 0
                
                if text_density > 0.1:  # At least 10% text
                    div_candidates.append({
                        'index': i,
                        'text_length': len(text),
                        'density': text_density,
                        'score': len(text) * text_density,
                        'classes': div.get('class', []),
                        'id': div.get('id', ''),
                        'text_preview': text[:300] + "..." if len(text) > 300 else text
                    })
        
        # Sort by score
        div_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"\n📊 Top content candidates by text density:")
        for i, candidate in enumerate(div_candidates[:5]):
            print(f"{i+1}. DIV (score: {candidate['score']:.1f})")
            print(f"   Length: {candidate['text_length']} chars")
            print(f"   Density: {candidate['density']:.3f}")
            print(f"   Classes: {candidate['classes']}")
            print(f"   ID: {candidate['id']}")
            print(f"   Preview: {candidate['text_preview'][:150]}...")
            print()
    
    # Test the extractor
    print(f"\n🧪 Testing ContentExtractor...")
    extractor = ContentExtractor()
    
    # Test article content extraction
    article_content = extractor.extract_article_content(html_content)
    print(f"Article extraction method: {article_content.get('extraction_method')}")
    print(f"Article content length: {article_content.get('word_count', 0)} words")
    if article_content.get('main_text'):
        preview = article_content['main_text'][:500] + "..." if len(article_content['main_text']) > 500 else article_content['main_text']
        print(f"Article preview: {preview}")
    
    # Test structured content extraction
    structured = extractor.extract_structured_content(html_content)
    print(f"\n📋 Structured content found:")
    print(f"   Headlines: {len(structured.get('headlines', []))}")
    print(f"   Paragraphs: {len(structured.get('paragraphs', []))}")
    print(f"   Lists: {len(structured.get('lists', []))}")
    
    if structured.get('paragraphs'):
        main_paragraphs = [p for p in structured['paragraphs'] if p['word_count'] > 20]
        print(f"   Substantial paragraphs (>20 words): {len(main_paragraphs)}")
        
        if main_paragraphs:
            longest = max(main_paragraphs, key=lambda x: x['word_count'])
            print(f"   Longest paragraph: {longest['word_count']} words")
            print(f"   Preview: {longest['text'][:200]}...")


if __name__ == "__main__":
    url = "https://timesofindia.indiatimes.com/technology/tech-news/silicon-valley-startup-ceo-challenges-us-h-1b-visa-fees-hike-says-100000-fees-will-favor/articleshow/124175606.cms"
    asyncio.run(debug_content_extraction(url))

import requests
from bs4 import BeautifulSoup
import re

url = "https://fitgirl-repacks.site/octopath-traveler-0-pc/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

r = requests.get(url, headers=HEADERS)
soup = BeautifulSoup(r.text, "html.parser")
entry_content = soup.find('div', class_='entry-content')

if entry_content:
    full_text = entry_content.get_text('\n')
    print(f"FULL TEXT PREVIEW:\n{full_text[:500]}...")
    
    # Check for spoilers
    spoiler_titles = entry_content.find_all(['div', 'span'], class_='su-spoiler-title')
    print(f"FOUND {len(spoiler_titles)} SPOILERS")
    for st in spoiler_titles:
        print(f"SPOILER TITLE: '{st.get_text()}'")
        
    # Test current logic
    description = "-"
    spoiler_title = entry_content.find(['div', 'span'], class_='su-spoiler-title', text=re.compile(r'Game Description', re.I))
    if spoiler_title:
        print("SPOILER TITLE FOUND VIA FIND")
        spoiler_content = spoiler_title.find_next_sibling('div', class_='su-spoiler-content')
        if spoiler_content:
            description = spoiler_content.get_text('\n').strip()
            print("SPOILER CONTENT FOUND")
    
    if description == "-":
        print("TRYING REGEX...")
        m_desc = re.search(r'(?:Game Description|Game Features)\s+(.*?)(?=\n+(?:Repack Features|Screenshots|Afraid of|Mirrors|Download Mirrors)|\Z)', full_text, re.DOTALL | re.IGNORECASE)
        if m_desc:
            description = m_desc.group(1).strip()
            print("REGEX MATCHED")
        else:
            print("REGEX FAILED")
            
    print(f"FINAL DESCRIPTION: {description[:100]}...")

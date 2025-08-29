from flask import Flask, render_template, request, jsonify, send_file
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import os
from icalendar import Calendar, Event
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

app = Flask(__name__)

# Event categories for classification
EVENT_CATEGORIES = {
    'music': ['concert', 'band', 'dj', 'music', 'live music', 'festival', 'acoustic', 'jazz', 'rock', 'pop'],
    'sports': ['game', 'match', 'tournament', 'league', 'sports', 'football', 'basketball', 'soccer', 'tennis', 'golf'],
    'arts': ['art', 'museum', 'gallery', 'exhibition', 'theater', 'performance', 'dance', 'ballet', 'opera', 'sculpture'],
    'technology': ['tech', 'coding', 'hackathon', 'conference', 'workshop', 'ai', 'startup', 'programming', 'software', 'digital'],
    'food': ['food', 'cooking', 'tasting', 'restaurant', 'culinary', 'wine', 'beer', 'chef', 'dining', 'cuisine'],
    'education': ['workshop', 'seminar', 'lecture', 'course', 'training', 'webinar', 'class', 'learning', 'tutorial'],
    'networking': ['networking', 'meetup', 'professional', 'business', 'career', 'entrepreneur', 'corporate'],
    'other': []
}

def categorize_event(title, description):
    """Categorize event based on title and description"""
    text = (title + ' ' + description).lower()
    for category, keywords in EVENT_CATEGORIES.items():
        if any(keyword in text for keyword in keywords):
            return category
    return 'other'

def parse_event_datetime(date_string, city):
    """Enhanced date parsing with better pattern recognition"""
    if not date_string or date_string == "Date/Time TBA":
        return None
    
    # Common date patterns
    patterns = [
        '%A, %B %d, %Y at %I:%M %p',  # Saturday, Aug 31, 2024 at 2:00 PM
        '%B %d, %Y at %I:%M %p',      # August 31, 2024 at 2:00 PM
        '%m/%d/%Y at %I:%M %p',      # 08/31/2024 at 2:00 PM
        '%Y-%m-%d %H:%M:%S',         # 2024-08-31 14:00:00
        '%A, %b %d at %I:%M %p',     # Saturday, Aug 31 at 2:00 PM
    ]
    
    for pattern in patterns:
        try:
            parsed_date = datetime.strptime(date_string, pattern)
            # Handle past dates
            now = datetime.now()
            if parsed_date < now:
                parsed_date = parsed_date.replace(year=now.year + 1)
            return parsed_date
        except ValueError:
            continue
    
    # Fallback to dateutil parser
    try:
        parsed_date = date_parser.parse(date_string, fuzzy=True)
        now = datetime.now()
        if parsed_date < now:
            parsed_date = parsed_date.replace(year=now.year + 1)
        return parsed_date
    except:
        return None

def parse_event_location(location_string, city):
    """Enhanced location parsing with better validation"""
    if not location_string or location_string.strip() == city:
        return f"Downtown {city}"
    
    # Clean up location text
    location = location_string.strip()
    
    # Remove common prefixes/suffixes
    prefixes_to_remove = ['Location:', 'Venue:', 'Address:', 'Where:']
    for prefix in prefixes_to_remove:
        if location.startswith(prefix):
            location = location[len(prefix):].strip()
    
    # If location is too short or generic, append city
    if len(location) < 5 or location.lower() in ['tba', 'to be announced', 'online', 'virtual']:
        return f"{city} Area"
    
    return location

def scrape_eventbrite_events(city):
    """Scrape events from Eventbrite with improved selectors"""
    events = []
    
    try:
        # Multiple Eventbrite URL patterns to try
        urls = [
            f"https://www.eventbrite.com/d/{city.lower().replace(' ', '-')}/events/",
            f"https://www.eventbrite.com/d/{city.lower()}/events/",
            f"https://www.eventbrite.com/e/search?q={city.replace(' ', '%20')}"
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        for url in urls:
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Multiple selector patterns for Eventbrite
                selectors = [
                    'article[data-testid="event-card"]',
                    'div[data-testid="event-card"]',
                    '.search-event-card',
                    '.event-card',
                    'article.event-card',
                    'div.event-card',
                    '[data-event-id]'
                ]
                
                event_cards = []
                for selector in selectors:
                    cards = soup.select(selector)
                    if cards:
                        event_cards = cards
                        break
                
                if event_cards:
                    for card in event_cards[:8]:  # Limit to 8 events
                        try:
                            # Extract title and URL with multiple patterns
                            title = None
                            event_url = None
                            title_selectors = [
                                'h3 a',
                                'h2 a', 
                                'h1 a',
                                '.event-title a',
                                '[data-testid="event-title"]',
                                'a[data-testid="event-title-link"]'
                            ]
                            
                            for sel in title_selectors:
                                title_elem = card.select_one(sel)
                                if title_elem:
                                    title = title_elem.get_text(strip=True)
                                    if title_elem.name == 'a' and title_elem.get('href'):
                                        event_url = title_elem.get('href')
                                        if event_url.startswith('/'):
                                            event_url = 'https://www.eventbrite.com' + event_url
                                    break
                            
                            if not title:
                                continue
                            
                            # Extract date/time with multiple patterns
                            date_time = "Date/Time TBA"
                            date_selectors = [
                                'time',
                                '[data-testid="event-datetime"]',
                                '.event-date',
                                '.date-time',
                                'span[data-testid="event-start-date"]'
                            ]
                            
                            for sel in date_selectors:
                                date_elem = card.select_one(sel)
                                if date_elem:
                                    date_time = date_elem.get_text(strip=True)
                                    if date_time and date_time != "Date/Time TBA":
                                        break
                            
                            # Extract location
                            location = f"Downtown {city}"
                            location_selectors = [
                                '[data-testid="event-location"]',
                                '.event-location',
                                '.venue-name',
                                'span[data-testid="event-venue"]'
                            ]
                            
                            for sel in location_selectors:
                                loc_elem = card.select_one(sel)
                                if loc_elem:
                                    loc_text = loc_elem.get_text(strip=True)
                                    if loc_text:
                                        location = parse_event_location(loc_text, city)
                                        break
                            
                            # Extract description
                            description = "No description available"
                            desc_selectors = [
                                '.event-description',
                                '.summary',
                                'p',
                                '[data-testid="event-summary"]'
                            ]
                            
                            for sel in desc_selectors:
                                desc_elem = card.select_one(sel)
                                if desc_elem:
                                    desc_text = desc_elem.get_text(strip=True)
                                    if desc_text and len(desc_text) > 20:
                                        description = desc_text[:200] + "..." if len(desc_text) > 200 else desc_text
                                        break
                            
                            # Parse datetime and categorize
                            parsed_datetime = parse_event_datetime(date_time, city)
                            category = categorize_event(title, description)
                            
                            events.append({
                                'title': title,
                                'date_time': date_time,
                                'parsed_datetime': parsed_datetime,
                                'location': location,
                                'description': description,
                                'category': category,
                                'event_url': event_url or f"https://www.eventbrite.com/d/{city.lower().replace(' ', '-')}/events/"
                            })
                            
                        except Exception as e:
                            continue
                    
                    if events:
                        break  # Found events, no need to try other URLs
                        
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"Error scraping Eventbrite: {e}")
    
    return events

def scrape_meetup_events(city):
    """Scrape events from Meetup.com"""
    events = []
    
    try:
        # Meetup search URL
        url = f"https://www.meetup.com/find/?keywords=&location={city.replace(' ', '%20')}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for event cards
        event_cards = soup.find_all(['div', 'article'], class_=re.compile(r'event|card'))
        
        for card in event_cards[:6]:  # Limit to 6 events
            try:
                # Extract title and URL
                title_elem = card.find(['h1', 'h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|event'))
                if not title_elem:
                    title_elem = card.find('a')
                
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                
                # Extract event URL
                event_url = None
                if title_elem.name == 'a' and title_elem.get('href'):
                    event_url = title_elem.get('href')
                    if event_url.startswith('/'):
                        event_url = 'https://www.meetup.com' + event_url
                elif title_elem.find('a'):
                    link_elem = title_elem.find('a')
                    if link_elem.get('href'):
                        event_url = link_elem.get('href')
                        if event_url.startswith('/'):
                            event_url = 'https://www.meetup.com' + event_url
                
                # Extract date
                date_elem = card.find(['time', 'span', 'div'], class_=re.compile(r'date|time'))
                date_time = date_elem.get_text(strip=True) if date_elem else "Date/Time TBA"
                
                # Extract location
                location_elem = card.find(['span', 'div'], class_=re.compile(r'location|venue|address'))
                location = parse_event_location(
                    location_elem.get_text(strip=True) if location_elem else city, 
                    city
                )
                
                # Extract description
                desc_elem = card.find(['p', 'div'], class_=re.compile(r'description|summary|excerpt'))
                description = "Meetup event - check Meetup.com for full details"
                if desc_elem:
                    desc_text = desc_elem.get_text(strip=True)
                    if len(desc_text) > 20:
                        description = desc_text[:200] + "..." if len(desc_text) > 200 else desc_text
                
                parsed_datetime = parse_event_datetime(date_time, city)
                category = categorize_event(title, description)
                
                events.append({
                    'title': title,
                    'date_time': date_time,
                    'parsed_datetime': parsed_datetime,
                    'location': location,
                    'description': description,
                    'category': category,
                    'event_url': event_url or f"https://www.meetup.com/find/?keywords=&location={city.replace(' ', '%20')}"
                })
                
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"Error scraping Meetup: {e}")
    
    return events

def get_events_from_multiple_sources(city):
    """Get events from multiple sources with fallback"""
    all_events = []
    
    # Try Eventbrite first
    print(f"Searching Eventbrite for events in {city}...")
    eventbrite_events = scrape_eventbrite_events(city)
    if eventbrite_events:
        all_events.extend(eventbrite_events)
        print(f"Found {len(eventbrite_events)} events from Eventbrite")
    
    # Try Meetup if we need more events
    if len(all_events) < 5:
        print(f"Searching Meetup for events in {city}...")
        meetup_events = scrape_meetup_events(city)
        if meetup_events:
            all_events.extend(meetup_events)
            print(f"Found {len(meetup_events)} events from Meetup")
    
    # Remove duplicates based on title similarity
    unique_events = []
    seen_titles = set()
    
    for event in all_events:
        title_key = event['title'].lower().strip()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_events.append(event)
    
    # If still no events, return enhanced demo events with proper dates
    if not unique_events:
        print(f"No events found from web sources, using demo events for {city}")
        # Use current date + future dates for demo events
        from datetime import timedelta
        base_date = datetime.now() + timedelta(days=1)
        
        unique_events = [
            {
                'title': f'Community Art Festival - {city}',
                'date_time': f'{(base_date + timedelta(days=1)).strftime("%A, %B %d, %Y at 2:00 PM")}',
                'parsed_datetime': base_date + timedelta(days=1, hours=14),
                'location': f'Downtown {city}',
                'description': 'Join us for a vibrant community art festival featuring local artists, live music, and food vendors. Experience the best of local creativity with interactive exhibits, workshops, and performances.',
                'category': 'arts',
                'event_url': f'https://www.eventbrite.com/d/{city.lower().replace(" ", "-")}/events/'
            },
            {
                'title': f'Tech Innovation Meetup - {city}',
                'date_time': f'{(base_date + timedelta(days=3)).strftime("%A, %B %d, %Y at 6:00 PM")}',
                'parsed_datetime': base_date + timedelta(days=3, hours=18),
                'location': f'{city} Convention Center',
                'description': 'Network with local tech professionals and learn about the latest trends in artificial intelligence, blockchain, and software development. Featuring keynote speakers and networking opportunities.',
                'category': 'technology',
                'event_url': f'https://www.meetup.com/find/?keywords=tech&location={city.replace(" ", "%20")}'
            },
            {
                'title': f'Weekend Farmers Market - {city}',
                'date_time': f'{(base_date + timedelta(days=2)).strftime("%A, %B %d, %Y at 8:00 AM")}',
                'parsed_datetime': base_date + timedelta(days=2, hours=8),
                'location': f'{city} City Square',
                'description': 'Fresh produce, local crafts, and delicious food from local vendors every weekend. Support local farmers and artisans while enjoying live music and family-friendly activities.',
                'category': 'food',
                'event_url': f'https://www.eventbrite.com/d/{city.lower().replace(" ", "-")}/food--and--drink--events/'
            },
            {
                'title': f'Live Jazz Night - {city}',
                'date_time': f'{(base_date + timedelta(days=4)).strftime("%A, %B %d, %Y at 8:00 PM")}',
                'parsed_datetime': base_date + timedelta(days=4, hours=20),
                'location': f'Blue Note Cafe, {city}',
                'description': 'An evening of smooth jazz featuring local musicians and guest performers. Enjoy craft cocktails and appetizers while listening to the best jazz music in the city.',
                'category': 'music',
                'event_url': f'https://www.eventbrite.com/d/{city.lower().replace(" ", "-")}/music--events/'
            },
            {
                'title': f'Business Networking Breakfast - {city}',
                'date_time': f'{(base_date + timedelta(days=5)).strftime("%A, %B %d, %Y at 7:30 AM")}',
                'parsed_datetime': base_date + timedelta(days=5, hours=7, minutes=30),
                'location': f'{city} Business Center',
                'description': 'Connect with local entrepreneurs, business owners, and professionals over breakfast. Exchange ideas, build partnerships, and grow your professional network.',
                'category': 'networking',
                'event_url': f'https://www.meetup.com/find/?keywords=networking&location={city.replace(" ", "%20")}'
            }
        ]
    
    return unique_events[:10]  # Limit to 10 events total

def create_weekend_digest(events):
    """Create a weekend plan digest from top 3 events"""
    if not events:
        return "No events found for this weekend."
    
    top_events = events[:3]
    digest = "🎉 Weekend Plan Digest 🎉\n\n"
    digest += f"Here are the top {len(top_events)} events happening this weekend:\n\n"
    
    for i, event in enumerate(top_events, 1):
        digest += f"{i}. {event['title']}\n"
        digest += f"   📅 {event['date_time']}\n"
        digest += f"   📍 {event['location']}\n"
        digest += f"   📝 {event['description'][:100]}...\n\n"
    
    digest += "Have a great weekend exploring these amazing events! 🌟"
    return digest

def create_pdf_report(events, city, digest):
    """Create a PDF report of events"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    story.append(Paragraph(f"Local Events in {city}", title_style))
    story.append(Spacer(1, 20))
    
    # Digest section
    story.append(Paragraph("Weekend Plan Digest", styles['Heading2']))
    story.append(Spacer(1, 12))
    digest_paragraphs = digest.split('\n')
    for para in digest_paragraphs:
        if para.strip():
            story.append(Paragraph(para, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Events section
    story.append(Paragraph("All Events", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    for event in events:
        story.append(Paragraph(f"<b>{event['title']}</b>", styles['Heading3']))
        story.append(Paragraph(f"<b>Date & Time:</b> {event['date_time']}", styles['Normal']))
        story.append(Paragraph(f"<b>Location:</b> {event['location']}", styles['Normal']))
        story.append(Paragraph(f"<b>Description:</b> {event['description']}", styles['Normal']))
        story.append(Spacer(1, 15))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


@app.route('/')
def index():
    """Render the main search page"""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_events():
    """Search for events in a given city"""
    city = request.form.get('city', 'Detroit').strip()
    
    if not city:
        return jsonify({'error': 'Please enter a city name'})
    
    # Scrape events from multiple sources
    events = get_events_from_multiple_sources(city)
    
    # Create digest
    digest = create_weekend_digest(events)
    
    return jsonify({
        'city': city,
        'events': events,
        'digest': digest,
        'total_events': len(events)
    })

@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    """Generate and download PDF report"""
    data = request.get_json()
    city = data.get('city', 'Unknown City')
    events = data.get('events', [])
    digest = data.get('digest', '')
    
    # Create PDF
    pdf_buffer = create_pdf_report(events, city, digest)
    
    # Save to temporary file
    filename = f"events_{city.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.pdf"
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )

@app.route('/filter-events', methods=['POST'])
def filter_events():
    """Filter events based on various criteria"""
    data = request.get_json()
    events = data.get('events', [])
    filters = data.get('filters', {})
    
    filtered_events = events
    
    # Category filter
    if filters.get('category') and filters['category'] != 'all':
        filtered_events = [e for e in filtered_events if e.get('category') == filters['category']]
    
    # Date range filter
    if filters.get('date_from'):
        from_date = datetime.strptime(filters['date_from'], '%Y-%m-%d')
        filtered_events = [e for e in filtered_events if e.get('parsed_datetime') and e['parsed_datetime'] >= from_date]
    
    if filters.get('date_to'):
        to_date = datetime.strptime(filters['date_to'], '%Y-%m-%d')
        filtered_events = [e for e in filtered_events if e.get('parsed_datetime') and e['parsed_datetime'] <= to_date]
    
    # Search filter
    if filters.get('search'):
        search_term = filters['search'].lower()
        filtered_events = [e for e in filtered_events if search_term in e['title'].lower() or search_term in e['description'].lower()]
    
    return jsonify({'events': filtered_events, 'total': len(filtered_events)})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

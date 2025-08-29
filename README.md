# Local Events Finder

A Python Flask web application that helps users discover local events in their city. The app scrapes event data from Eventbrite, displays results in a beautiful Bootstrap interface, and allows users to download event information as PDF reports.

## Features

- **City-based Event Search**: Enter any city to find local events
- **Beautiful UI**: Bootstrap 5 responsive design with modern styling
- **Event Cards**: Clean card layout displaying event details
- **Weekend Digest**: AI-generated summary of top 3 events
- **PDF Export**: Download event listings and digest as PDF
- **Fallback Data**: Demo events shown when scraping fails

## Installation

1. **Clone or download the project files**

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

1. **Search for Events**:
   - Enter a city name in the search box (defaults to "Detroit")
   - Click "Find Events" to search
   - View results in the card layout below

2. **View Weekend Digest**:
   - Automatically generated summary of top 3 events
   - Provides quick overview for weekend planning

3. **Download PDF Report**:
   - Click "Download as PDF" button
   - Gets a formatted PDF with all events and digest
   - File saved with city name and date

## Project Structure

```
local-events-finder/
├── app.py              # Main Flask application
├── templates/
│   └── index.html      # Bootstrap frontend template
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Dependencies

- **Flask**: Web framework
- **requests**: HTTP library for web scraping
- **BeautifulSoup4**: HTML parsing for event extraction
- **reportlab**: PDF generation
- **lxml**: XML/HTML parser

## Technical Details

### Event Scraping
- Targets Eventbrite's public event listings
- Uses BeautifulSoup to parse HTML content
- Extracts: title, date/time, location, description
- Fallback to demo events if scraping fails

### PDF Generation
- Uses ReportLab for professional PDF formatting
- Includes weekend digest and full event listings
- Automatic filename with city and date

### Frontend
- Bootstrap 5 for responsive design
- Font Awesome icons for visual appeal
- AJAX for seamless search experience
- Loading states and error handling

## Customization

### Adding More Event Sources
Modify the `scrape_eventbrite_events()` function in `app.py` to include additional event platforms.

### Styling Changes
Update the CSS in `templates/index.html` or add a separate stylesheet in a `static/` directory.

### PDF Formatting
Customize the `create_pdf_report()` function to change PDF layout and styling.

## Troubleshooting

**No events found**: The app includes fallback demo events when scraping fails. This is normal for cities with limited Eventbrite presence.

**PDF download issues**: Ensure all dependencies are installed correctly, particularly `reportlab`.

**Scraping errors**: Event websites may change their structure. The app is designed to handle this gracefully with fallback content.

## Demo Ready

This application is ready for demonstration with:
- Working search functionality
- Beautiful responsive interface
- PDF export capability
- Fallback demo data
- Error handling and loading states

Perfect for showcasing local event discovery capabilities!

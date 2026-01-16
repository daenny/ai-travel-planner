# Travel Planner - Development Guide

## Documentation Maintenance

**Important:** Always keep this file and README.md updated when making changes to:
- UI structure or navigation (tabs, sidebar sections)
- Configuration options or settings
- API key handling or storage
- New features or removed functionality
- Constants or configuration values

## Project Overview

A Streamlit-based travel planning assistant for family trips to any destination. Features conversational AI planning with automatic destination detection, blog content extraction, and PDF generation with multiple styles.

## Quick Start

```bash
# Install dependencies
pixi install

# Run the app
pixi run app
```

## Project Structure

```
ai_travel_planner/
├── app.py                 # Streamlit entry point - main UI logic
├── agents/                # AI provider implementations
│   ├── base.py            # Abstract TravelAgent class + dynamic system prompt
│   ├── claude_agent.py    # Anthropic Claude
│   ├── openai_agent.py    # OpenAI GPT
│   └── gemini_agent.py    # Google Gemini
├── services/              # External integrations
│   ├── unsplash.py        # Image fetching + caching
│   ├── blog_scraper.py    # HTML scraping for travel tips
│   ├── pdf_generator.py   # WeasyPrint PDF generation
│   └── destination_detector.py  # Automatic destination detection
├── models/                # Pydantic data models
│   ├── itinerary.py       # Itinerary, DayPlan, Activity, etc.
│   └── destination.py     # Destination and TripDestinations
├── storage/               # Persistence
│   └── json_store.py      # JSON file save/load
└── templates/             # Jinja2 HTML templates for PDFs
    ├── magazine.html      # Colorful travel magazine style
    ├── minimal.html       # Clean, elegant style
    └── guidebook.html     # Print-optimized with QR codes
```

## UI Structure

The app uses a 4-tab layout with a sidebar:

### Tabs
1. **Chat** - Conversational AI planning interface
2. **Itinerary** - View/edit generated itinerary, create from conversation
3. **Blog Tips** - Add blog URLs, extract tips, view extracted content
4. **Settings** - AI provider selection, API keys, language, Unsplash configuration

### Sidebar
- App title (dynamic based on destination)
- Mode indicator (Local/Remote, Debug)
- AI Provider status (read-only, shows current connection)
- Save/Load session files
- PDF generation controls

### Key Constants
- `PROVIDERS` - List of supported AI providers: `["Claude", "OpenAI", "Gemini"]`
- `PROVIDER_MODELS` - Dict mapping providers to available models
- `SUPPORTED_LANGUAGES` - List of supported content languages

## Key Patterns

### Adding a New AI Provider

1. Create `ai_travel_planner/agents/new_agent.py`
2. Inherit from `TravelAgent` base class
3. Implement required methods:
   - `chat(message, history)` - streaming generator
   - `generate_itinerary_json(requirements, current_itinerary)` - returns `Itinerary`
   - `name` and `model_id` properties
4. Add to `ai_travel_planner/agents/__init__.py`
5. In `ai_travel_planner/app.py`:
   - Add provider name to `PROVIDERS` constant
   - Add models to `PROVIDER_MODELS` dict
   - Add case in `get_agent()` function

### Adding a New PDF Style

1. Create `ai_travel_planner/templates/newstyle.html` (Jinja2 template)
2. Add enum value to `PDFStyle` in `ai_travel_planner/services/pdf_generator.py`
3. Template receives: `itinerary`, `qr_codes`, `b64image` filter

### Blog Integration

The blog scraper can use AI for intelligent extraction:
1. `BlogScraper.scrape_blog(url)` - Basic HTML scraping
2. `BlogScraper.scrape_with_ai(url, agent)` - AI-powered extraction using the travel agent
3. `BlogContent.to_context_string()` - Formats content for AI context

### Data Flow

```
User Chat → Agent.chat() → ChatMessage stored in PlannerSession
         ↓
"Generate Itinerary" → Agent.generate_itinerary_json() → Itinerary model
         ↓
"Generate PDF" → PDFGenerator.generate_pdf() → WeasyPrint → PDF file

Blog URL (Blog Tips tab) → BlogScraper.scrape_with_ai() → BlogContent → "Share tips" → Agent context
```

## API Key Storage

API keys can be stored in two ways:

### 1. System Keyring (Recommended for Local Mode)
Keys are securely stored in the OS keyring (GNOME Keyring, KWallet, macOS Keychain, Windows Credential Manager).
- Configure in the **Settings tab** (not sidebar)
- Use the "Save Key" button to store keys in keyring
- Click "Connect" to apply provider/model changes
- Keys persist across sessions securely
- Service name: `travel-planner`

### 2. Environment Variables (Fallback)
Create `.env` file with:
- `ANTHROPIC_API_KEY` - For Claude
- `OPENAI_API_KEY` - For OpenAI
- `GOOGLE_API_KEY` - For Gemini
- `UNSPLASH_ACCESS_KEY` - For images (optional but recommended)

The app checks keyring first, then falls back to environment variables.

### Auto-Detection
On startup, the app automatically detects and connects to the first available provider that has an API key configured (checks Claude, then OpenAI, then Gemini).

## Dependencies

Managed via pixi (conda-forge). Key packages:
- `streamlit` - Web UI
- `anthropic`, `openai`, `google-genai` - AI providers
- `weasyprint` - PDF generation (requires system libs)
- `beautifulsoup4` - Blog scraping
- `pydantic` - Data validation
- `jinja2` - PDF templating
- `qrcode` - QR codes for guidebook style
- `keyring` - Secure API key storage

## Common Tasks

### Modify the AI System Prompt

The system prompt is dynamically generated based on detected destinations. Edit these in `ai_travel_planner/agents/base.py`:
- `SYSTEM_PROMPT_TEMPLATE` - Main prompt template with `{destination_expertise}` placeholder
- `DEFAULT_EXPERTISE` - Expertise shown when no destination is detected
- `build_destination_expertise()` - Function that builds destination-specific expertise

### Change Itinerary JSON Schema

1. Update Pydantic models in `ai_travel_planner/models/itinerary.py`
2. Update `ITINERARY_JSON_PROMPT` in each agent file (claude, openai, gemini)
3. Update PDF templates if new fields need rendering

### Add New Activity Types

Add to `ActivityType` enum in `ai_travel_planner/models/itinerary.py`

### Customize PDF Styling

Edit the `<style>` section in the relevant template file in `ai_travel_planner/templates/`

## Testing

Run manual testing:
```bash
pixi run app
```

Test imports:
```bash
pixi run python -c "from ai_travel_planner.models import Itinerary; print('OK')"
```

## Known Issues

- WeasyPrint requires system libraries (cairo, pango) - usually pre-installed on Linux
- Large blog pages may timeout during scraping

## Code Style

- Type hints throughout
- Pydantic for data validation
- Generator-based streaming for chat responses
- Path objects for file handling
- f-strings for formatting

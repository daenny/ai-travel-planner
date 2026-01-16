# Travel Planner

A Streamlit-based travel planning assistant that helps you plan family trips to any destination. Chat with an AI agent to build your itinerary, extract tips from travel blogs, and generate beautiful PDF travel guides. The app automatically detects your destination and adapts its expertise accordingly.

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **AI-Powered Planning** - Chat with Claude, OpenAI, or Google Gemini to plan your trip
- **Auto-Detection** - Automatically connects to the first available AI provider on startup
- **Multiple Model Support** - Choose from various models (GPT-4o, Claude Sonnet, Gemini Pro, etc.)
- **Iterative Generation** - Generate long itineraries (10+ days) with real-time progress feedback
  - AI determines optimal trip duration from your conversation
  - Days generated in configurable blocks (2-4 days at a time)
  - Resume from partial completion if generation fails
- **Blog Tip Extraction** - Paste travel blog URLs in the Blog Tips tab and let AI extract useful tips
- **PDF Generation** - Export your itinerary in 3 beautiful styles:
  - **Magazine** - Colorful travel magazine aesthetic with large images
  - **Minimal** - Clean, elegant design focused on readability
  - **Guidebook** - Print-optimized with QR codes for bookings
- **Unsplash Integration** - Automatically fetch stunning travel photos for your PDF
- **Secure Key Storage** - API keys stored safely in your system keyring (configured in Settings tab)
- **Session Persistence** - Save and load your planning sessions
- **Multi-Language Support** - Generate content in multiple languages

## Installation

### Prerequisites

- [Pixi](https://pixi.sh/) package manager
- Python 3.12+

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd pdf_planner
   ```

2. Install dependencies:
   ```bash
   pixi install
   ```

3. (Optional) Create a `.env` file with your API keys:
   ```bash
   cp .env.example .env
   # Edit .env with your keys
   ```

   Or enter them directly in the app - they'll be saved securely in your system keyring.

## Usage

Start the application:

```bash
pixi run app
```

### Quick Start

1. **Auto-Connect** - The app automatically detects and connects to an available AI provider on startup
2. **Configure (Optional)** - Go to the **Settings tab** to change provider, model, or add API keys
3. **Chat** - Tell the AI where you want to travel (e.g., "I want to plan a 10-day trip to Japan")
4. **Add Blogs** - Go to the **Blog Tips tab**, paste travel blog URLs and click "Extract Tips"
5. **Share Tips** - In the Chat tab, click "Share tips with AI" to give the agent your blog research
6. **Generate Itinerary** - Click "Create Itinerary" in the Itinerary tab
   - Watch progress as days are generated in blocks
   - If generation fails, click "Resume" to continue from where it stopped
7. **Export PDF** - In the sidebar, choose a style and download your travel guide

The app will automatically detect your destination and update the title and AI expertise accordingly.

### API Keys

You'll need at least one of these API keys:

| Provider | Get Key From |
|----------|--------------|
| Claude | [Anthropic Console](https://console.anthropic.com/) |
| OpenAI | [OpenAI Platform](https://platform.openai.com/) |
| Gemini | [Google AI Studio](https://aistudio.google.com/) |
| Unsplash | [Unsplash Developers](https://unsplash.com/developers) (optional, for images) |

## Project Structure

```
pdf_planner/
├── ai_travel_planner/
│   ├── app.py              # Streamlit main application (4 tabs + sidebar)
│   ├── agents/             # AI provider implementations (Claude, OpenAI, Gemini)
│   ├── services/           # Unsplash, blog scraper, PDF generator
│   ├── models/             # Pydantic data models
│   ├── storage/            # JSON persistence
│   └── templates/          # PDF HTML templates (magazine, minimal, guidebook)
├── plans/                  # Saved sessions (JSON)
├── exports/                # Generated PDFs
├── images/                 # Cached Unsplash images
├── CLAUDE.md              # Development guide
└── README.md              # This file
```

## PDF Styles

### Magazine Style
Rich, colorful layout with large hero images and a travel magazine feel. Best for digital viewing.

### Minimal Style
Clean, elegant design with serif fonts and subtle styling. Great for those who prefer simplicity.

### Guidebook Style
Optimized for printing with compact layout, QR codes for booking links, and practical formatting. Perfect to take on your trip.

## Development

See [CLAUDE.md](CLAUDE.md) for development documentation including:
- How to add new AI providers
- How to create new PDF styles
- Architecture and data flow
- Common development tasks

## License

MIT License - feel free to use and modify for your own travel planning needs!

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- PDF generation powered by [WeasyPrint](https://weasyprint.org/)
- Images from [Unsplash](https://unsplash.com/)

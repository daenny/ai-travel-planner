# Travel Planner

A Streamlit-based travel planning assistant that helps you plan family trips to any destination. Chat with an AI agent to build your itinerary, extract tips from travel blogs, and generate beautiful PDF travel guides. The app automatically detects your destination and adapts its expertise accordingly.

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- **AI-Powered Planning** - Chat with Claude, OpenAI, or Google Gemini to plan your trip
- **Multiple Model Support** - Choose from various models (GPT-4o, Claude Sonnet, Gemini Pro, etc.)
- **Blog Tip Extraction** - Paste travel blog URLs and let AI extract useful tips and highlights
- **PDF Generation** - Export your itinerary in 3 beautiful styles:
  - **Magazine** - Colorful travel magazine aesthetic with large images
  - **Minimal** - Clean, elegant design focused on readability
  - **Guidebook** - Print-optimized with QR codes for bookings
- **Unsplash Integration** - Automatically fetch stunning travel photos for your PDF
- **Secure Key Storage** - API keys stored safely in your system keyring
- **Session Persistence** - Save and load your planning sessions

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

1. **Configure AI Provider** - Select Claude/OpenAI/Gemini in the sidebar and enter your API key
2. **Chat** - Tell the AI where you want to travel (e.g., "I want to plan a trip to Japan")
3. **Add Blogs** - Paste travel blog URLs to extract tips (AI will analyze them)
4. **Share Tips** - Click "Share tips with AI" to give the agent your blog research
5. **Generate Itinerary** - Click "Create Itinerary from Conversation" in the Itinerary tab
6. **Export PDF** - Choose a style and download your travel guide

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
├── src/
│   ├── app.py              # Streamlit main application
│   ├── agents/             # AI provider implementations
│   ├── services/           # Unsplash, blog scraper, PDF generator
│   ├── models/             # Pydantic data models
│   ├── storage/            # JSON persistence
│   └── templates/          # PDF HTML templates
├── plans/                  # Saved sessions (JSON)
├── exports/                # Generated PDFs
├── images/                 # Cached Unsplash images
└── CLAUDE.md              # Development guide
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

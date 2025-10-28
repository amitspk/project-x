# 🚀 Blog Question Generator

A production-grade system that transforms blog articles into interactive questions for enhanced reader engagement.

## 🎯 Overview

This system crawls blog articles, generates intelligent summaries, creates exploratory questions, and provides a Chrome extension to inject these questions into any website.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Crawler   │───▶│  LLM Services   │───▶│ Chrome Extension│
│                 │    │                 │    │                 │
│ • Crawl content │    │ • Summarization │    │ • Question      │
│ • Extract text  │    │ • Question gen  │    │   injection     │
│ • Save metadata │    │ • JSON output   │    │ • Answer drawer │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📦 Components

### 1. Web Crawler (`web_crawler/`)
- Production-grade web crawling with async support
- Rate limiting and error handling
- Content extraction and metadata capture
- Security features (SSRF protection)

### 2. LLM Services (`llm_service/`)
- Multi-provider LLM integration (OpenAI, Anthropic, Google)
- Content summarization service
- Question generation from summaries
- Configurable and extensible

### 3. UI Library (`ui-js/`)
- JavaScript library for question injection
- Answer drawer functionality
- Multiple placement strategies
- Responsive design

### 4. Chrome Extension (`chrome-extension/`)
- Inject questions on any website
- Upload custom question files
- Visual feedback and error handling
- Works with any webpage

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Chrome browser
- LLM API key (OpenAI, Anthropic, or Google)

### Installation

1. **Clone and setup:**
   ```bash
   cd SelfLearning
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure LLM API:**
   ```bash
   # Choose one:
   export OPENAI_API_KEY="sk-your-key-here"
   export ANTHROPIC_API_KEY="your-key-here"
   export GOOGLE_API_KEY="your-key-here"
   ```

3. **Load Chrome Extension:**
   - Open Chrome → `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked"
   - Select `chrome-extension/` folder

### Usage

#### Process a Blog Article
```bash
# Activate environment
source venv/bin/activate

# Process any blog URL
python3 blog_processor.py --url "https://medium.com/article-url"

# Custom output directory
python3 blog_processor.py --url "https://example.com/blog" --output-dir results
```

#### Use with Chrome Extension
1. Go to any website with paragraphs
2. Click the extension icon
3. Upload the generated `.questions.json` file
4. Click "Inject Custom Questions"
5. Click questions to see answer drawers!

## 📊 Example Output

### Generated Questions
```json
{
  "content_title": "Unit testing your React application with Jest and Enzyme",
  "questions": [
    {
      "id": "q1",
      "question": "How do Jest snapshots help ensure component rendering consistency?",
      "answer": "Jest snapshots create a saved representation of component output...",
      "question_type": "analytical",
      "confidence_score": 0.9,
      "estimated_answer_time": 45
    }
  ]
}
```

### Visual Result
- Questions appear as clickable boxes after paragraphs
- Click opens a slide-in drawer with the answer
- Professional styling with animations
- Mobile responsive design

## 🔧 Configuration

### LLM Services
Configure in environment variables:
```bash
# OpenAI (recommended)
export OPENAI_API_KEY="sk-..."

# Anthropic Claude
export ANTHROPIC_API_KEY="..."

# Google Gemini
export GOOGLE_API_KEY="..."
```

### Web Crawler
Modify `web_crawler/config/settings.py`:
```python
class CrawlerConfig:
    timeout: int = 30
    max_retries: int = 3
    requests_per_minute: int = 60
    user_agent: str = "BlogProcessor/1.0"
```

## 📁 Project Structure

```
SelfLearning/
├── blog_processor.py           # Main processing script
├── web_crawler/               # Web crawling module
│   ├── core/                 # Core crawler logic
│   ├── storage/              # File storage
│   └── utils/                # Utilities
├── llm_service/              # LLM integration
│   ├── core/                 # Core service
│   ├── providers/            # LLM providers
│   └── services/             # Summarization & questions
├── ui-js/                    # JavaScript library
│   ├── simple-question-injector.js
│   └── README.md
├── chrome-extension/         # Chrome extension
│   ├── manifest.json
│   ├── popup.html
│   └── popup.js
└── processed_content/        # Output directory
```

## 🛠️ Development

### Adding New LLM Providers
1. Create provider in `llm_service/providers/`
2. Implement `ILLMProvider` interface
3. Register in `llm_service/core/service.py`

### Customizing Question Generation
Modify prompts in:
- `llm_service/services/content_summarizer.py`
- `llm_service/services/simple_question_generator.py`

### Extending Chrome Extension
- Add features in `chrome-extension/popup.js`
- Modify UI in `chrome-extension/popup.html`
- Update injection logic in `ui-js/simple-question-injector.js`

## 🔍 Troubleshooting

### Common Issues

**"No LLM providers could be initialized"**
- Set up API keys as environment variables
- Check API key validity
- Ensure network connectivity

**"Web crawling failed"**
- Check URL accessibility
- Verify network connection
- Some sites may block crawlers

**"Chrome extension not working"**
- Reload extension in `chrome://extensions/`
- Check browser console for errors
- Try different websites

### Debug Mode
```bash
python3 blog_processor.py --url "https://example.com" --debug
```

## 📈 Performance

- **Web Crawling**: ~2-5 seconds per article
- **LLM Processing**: ~10-30 seconds depending on provider
- **Question Injection**: Instant
- **Memory Usage**: ~50-100MB during processing

## 🔒 Security

- SSRF protection in web crawler
- Input validation throughout
- No sensitive data stored
- Rate limiting implemented

## 📄 License

This project is for educational and research purposes.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📞 Support

For issues or questions:
1. Check troubleshooting section
2. Review logs with `--debug` flag
3. Test with different URLs/content

---

**Transform any blog into an interactive learning experience!** 🎉

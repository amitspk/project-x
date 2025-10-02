# 📖 Usage Guide

## 🚀 Quick Start

### 1. Setup Environment
```bash
# Activate virtual environment
source venv/bin/activate

# Set LLM API key (choose one)
export OPENAI_API_KEY="sk-your-key-here"
# OR
export ANTHROPIC_API_KEY="your-key-here"
# OR  
export GOOGLE_API_KEY="your-key-here"
```

### 2. Process a Blog Article
```bash
# Process any blog URL
python3 blog_processor.py --url "https://medium.com/article-url"

# Results saved to: processed_content/
```

### 3. Use with Chrome Extension
1. **Load Extension:**
   - Chrome → `chrome://extensions/`
   - Enable "Developer mode"
   - Click "Load unpacked" → Select `chrome-extension/` folder

2. **Test Questions:**
   - Go to any website with paragraphs
   - Click extension icon
   - Upload the `.questions.json` file from `processed_content/`
   - Click "Inject Custom Questions"
   - Click questions to see answers!

## 📋 Examples

### Process Medium Article
```bash
python3 blog_processor.py --url "https://medium.com/wehkamp-techblog/unit-testing-your-react-application-with-jest-and-enzyme-81c5545cee45"
```

### Process Wikipedia Article
```bash
python3 blog_processor.py --url "https://en.wikipedia.org/wiki/React_(JavaScript_library)"
```

### Custom Output Directory
```bash
python3 blog_processor.py --url "https://example.com/blog" --output-dir my_results
```

## 🎯 What You Get

### Generated Files
- `{article_id}.summary.json` - Article summary
- `{article_id}.questions.json` - Questions for Chrome extension

### Sample Questions
1. "How do Jest snapshots help ensure component rendering consistency?"
2. "What are the potential drawbacks of relying too heavily on snapshot testing?"
3. "How does mocking in Jest contribute to true unit testing practices?"

### Visual Results
- Questions appear as clickable boxes after paragraphs
- Click opens answer drawer from the right
- Professional styling with animations
- Works on any website

## 🔧 Troubleshooting

### No LLM API Key
```bash
# Error: "No LLM providers could be initialized"
# Solution: Set API key
export OPENAI_API_KEY="sk-your-key-here"
```

### Extension Not Working
1. Reload extension: `chrome://extensions/` → Click reload
2. Check file exists: Verify `.questions.json` file was generated
3. Try different website: Some sites may block content injection

### Web Crawling Failed
- Check URL is accessible
- Some sites block automated crawling
- Try different articles

## 💡 Tips

1. **Best URLs to try:**
   - Medium articles
   - Wikipedia pages
   - Technical blogs
   - News articles

2. **Good test websites for extension:**
   - Wikipedia articles
   - Medium posts
   - Any blog with multiple paragraphs

3. **Debug mode:**
   ```bash
   python3 blog_processor.py --url "https://example.com" --debug
   ```

## 🎉 Success!

When working correctly, you should see:
```
🚀 Blog Processing Pipeline
🌐 Step 1: Web Crawling
✅ Web crawling successful!
📝 Step 2: Content Processing  
✅ LLM processing successful!
💾 Step 3: Generate Output
✅ Output generated!
🎯 Processing Complete!
```

Ready to transform any blog into an interactive experience! 🚀

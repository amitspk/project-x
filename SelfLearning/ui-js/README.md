# Blog Question Injector - JavaScript Library

**Version**: 2.0  
**Purpose**: Production JavaScript library for publishers

---

## 📦 What This Is

This is the **production JavaScript library** that publishers embed on their blogs to inject AI-generated questions and answers.

This is **Service #2** in the 2-service architecture:
- **Service 1**: `content_processing_service/` (Backend API)
- **Service 2**: `ui-js/auto-blog-question-injector.js` (Frontend JS Library)

---

## 🚀 How Publishers Use It

Publishers add this script to their blog pages:

```html
<script src="https://your-cdn.com/auto-blog-question-injector.js"></script>
<script>
  AutoBlogQuestionInjector.autoInit({
    apiBaseUrl: 'https://api.your-service.com/api/v1'
  });
</script>
```

The library will automatically:
1. Detect the current blog URL
2. Fetch questions from the backend API
3. Inject UI components on the page
4. Handle user interactions

---

## 📁 Relationship to chrome-extension/

```
ui-js/
└── auto-blog-question-injector.js     ← PRODUCTION library

chrome-extension/
├── manifest.json                      ← Chrome wrapper (testing)
├── content.js                         ← Test loader
└── auto-blog-question-injector.js     ← Copy of library for testing
```

The `chrome-extension/` is just a **test harness** that:
- Loads the library for testing purposes
- Simulates how it works on publisher sites
- NOT for production deployment

---

## 🎯 Features

- Auto-detects blog URLs
- Fetches questions from backend API
- Injects pill-shaped question cards with icons
- Answer drawer with search functionality
- Similar articles suggestions
- Responsive design (desktop, tablet, mobile)
- Customizable styling and behavior

---

## 🔌 API Integration

The library calls these endpoints:

1. **GET /api/v1/questions/by-url**  
   Fetches questions for the current blog

2. **POST /api/v1/search/similar**  
   Finds related articles

3. **POST /api/v1/qa/ask**  
   Answers custom user questions

---

## 🎨 Customization

Publishers can customize:

```javascript
AutoBlogQuestionInjector.init('https://blog-url.com', {
  apiBaseUrl: 'https://api.your-service.com/api/v1',
  theme: 'default',
  randomizeOrder: true,
  questionsPerParagraph: 2,
  minParagraphLength: 100
});
```

---

## 📦 Distribution

For production:
1. Minify this file
2. Host on CDN (CloudFlare, AWS CloudFront, etc.)
3. Provide publishers with CDN URL
4. Publishers add script tag to their site

---

**This is the core product that publishers integrate!**

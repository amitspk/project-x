# Publisher Integration Guide

## 🚀 Quick Start - Get Your Blog Live in 5 Minutes!

### Step 1: Get Your API Key 🔑

Contact your administrator to onboard your publication. You'll receive:
- **API Key**: `pub_YOUR_UNIQUE_KEY_HERE`
- **Domain**: `example.com` (your registered domain)

**Keep your API key secure!** It's like a password.

---

## Step 2: Add the Script to Your Website

Add this code to your blog template (usually in the `<head>` section or before `</body>`):

```html
<!-- Blog Question Injector -->
<script src="https://your-cdn.com/auto-blog-question-injector.js"></script>
<script>
  // Initialize with YOUR API key
  AutoBlogQuestionInjector.autoInit({
    apiKey: 'pub_YOUR_UNIQUE_KEY_HERE'  // ← Replace with your actual API key
  });
</script>
```

**That's it!** 🎉 Questions will now appear automatically on your blog posts.

---

## 📋 Detailed Integration

### Option 1: Basic Integration (Recommended)

```html
<!DOCTYPE html>
<html>
<head>
    <title>Your Blog Post</title>
</head>
<body>
    <!-- Your blog content -->
    <article>
        <h1>Article Title</h1>
        <p>Your article content...</p>
    </article>

    <!-- Add this at the end of body -->
    <script src="/path/to/auto-blog-question-injector.js"></script>
    <script>
      AutoBlogQuestionInjector.autoInit({
        apiKey: 'pub_YOUR_API_KEY_HERE'
      });
    </script>
</body>
</html>
```

### Option 2: Custom Configuration

```html
<script src="/path/to/auto-blog-question-injector.js"></script>
<script>
  AutoBlogQuestionInjector.autoInit({
    // REQUIRED
    apiKey: 'pub_YOUR_API_KEY_HERE',
    
    // OPTIONAL: API Configuration
    apiBaseUrl: 'https://api.yourdomain.com/api/v1',  // Your API URL
    
    // OPTIONAL: UI Customization
    questionsPerParagraph: 2,    // How many questions per section
    animationDelay: 150,          // Animation timing (ms)
    
    // OPTIONAL: Debug mode
    debugMode: false              // Set to true for troubleshooting
  });
</script>
```

### Option 3: Manual Initialization

```html
<script src="/path/to/auto-blog-question-injector.js"></script>
<script>
  // Create instance
  const injector = new AutoBlogQuestionInjector({
    apiKey: 'pub_YOUR_API_KEY_HERE'
  });
  
  // Initialize with specific URL
  injector.init(window.location.href);
</script>
```

---

## 🎨 Styling (Optional)

The injected questions use default styling, but you can customize them:

```html
<style>
  /* Customize question cards */
  .abqi-question-card {
    border-radius: 12px !important;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  }
  
  /* Customize answer drawer */
  .abqi-answer-drawer {
    background: #ffffff !important;
    box-shadow: 0 10px 40px rgba(0,0,0,0.15) !important;
  }
  
  /* Customize icon */
  .abqi-icon {
    font-size: 28px !important;
  }
</style>
```

---

## 🔧 Platform-Specific Guides

### WordPress

1. Go to **Appearance > Theme Editor**
2. Edit `header.php` or `footer.php`
3. Add the script before `</head>` or `</body>`:

```php
<!-- Blog Question Injector -->
<script src="<?php echo get_template_directory_uri(); ?>/js/auto-blog-question-injector.js"></script>
<script>
  AutoBlogQuestionInjector.autoInit({
    apiKey: 'pub_YOUR_API_KEY_HERE'
  });
</script>
```

### Google Tag Manager

1. Create a new **Custom HTML** tag
2. Add this code:

```html
<script src="https://your-cdn.com/auto-blog-question-injector.js"></script>
<script>
  AutoBlogQuestionInjector.autoInit({
    apiKey: 'pub_YOUR_API_KEY_HERE'
  });
</script>
```

3. Set trigger to **All Pages** or **Blog Pages Only**
4. Publish

### React/Next.js

```jsx
// In your blog post component
import { useEffect } from 'react';

export default function BlogPost() {
  useEffect(() => {
    // Load the script
    const script = document.createElement('script');
    script.src = '/auto-blog-question-injector.js';
    script.onload = () => {
      window.AutoBlogQuestionInjector.autoInit({
        apiKey: 'pub_YOUR_API_KEY_HERE'
      });
    };
    document.body.appendChild(script);
    
    return () => {
      document.body.removeChild(script);
    };
  }, []);

  return (
    <article>
      {/* Your blog content */}
    </article>
  );
}
```

---

## ✅ Testing Your Integration

### 1. Check the Console

Open browser DevTools (F12) and look for:

```
[AutoBlogQuestionInjector] VERSION: 2025-10-14-FIX loaded
[AutoBlogQuestionInjector] AutoBlogQuestionInjector initialized
[AutoBlogQuestionInjector] 🚀 Attempting to fetch questions...
[AutoBlogQuestionInjector] ✅ Questions fetched successfully
```

### 2. Common Issues

**Error: "API key not provided"**
- Solution: Make sure you've set `apiKey: 'pub_...'` in the config

**Error: "401 Unauthorized"**
- Solution: Check if your API key is correct
- Contact admin to verify your key is active

**Error: "403 Forbidden - Domain mismatch"**
- Solution: Your domain doesn't match the registered domain
- Contact admin to update your registered domain

**No questions appearing**
- Check if the blog URL has been processed
- Check console for errors
- Enable debug mode: `debugMode: true`

---

## 🔐 Security Best Practices

### ✅ DO:
- Keep your API key secure
- Use environment variables for API keys (in backend/build systems)
- Regenerate your key if it's compromised
- Only use your key on your registered domain

### ❌ DON'T:
- Share your API key publicly
- Commit API keys to public repositories
- Use the same key across multiple domains
- Embed keys in client-side code without obfuscation (if possible, fetch from your backend)

### Advanced: Secure Key Storage

For extra security, store the key on your backend:

```javascript
// Frontend (public)
<script src="/auto-blog-question-injector.js"></script>
<script>
  // Fetch API key from your backend
  fetch('/api/get-blog-api-key')
    .then(r => r.json())
    .then(data => {
      AutoBlogQuestionInjector.autoInit({
        apiKey: data.apiKey
      });
    });
</script>
```

```javascript
// Your backend endpoint
app.get('/api/get-blog-api-key', (req, res) => {
  // Only serve to your own domain
  res.json({ apiKey: process.env.BLOG_API_KEY });
});
```

---

## 📊 Monitoring & Analytics

Check your API usage:
- Contact your admin for usage statistics
- Monitor console logs (with `debugMode: true`)
- Track engagement with questions on your blog

---

## 🆘 Support

### Need Help?

1. **Check Console Logs**: Enable `debugMode: true` and check browser console
2. **Test API Key**: Try it in a simple HTML file first
3. **Contact Support**: Email support@yourdomain.com with:
   - Your domain name
   - Error messages from console
   - Browser and version

### Regenerate Lost API Key

If you've lost your API key, contact your administrator. They can regenerate it for you.

**⚠️ Warning**: Regenerating your key will invalidate the old one immediately!

---

## 📚 API Reference

### AutoBlogQuestionInjector.autoInit(options)

Automatically initializes the injector on page load.

**Parameters:**
- `options` (Object):
  - `apiKey` (String) **[REQUIRED]**: Your publisher API key
  - `apiBaseUrl` (String): API base URL (default: provided by admin)
  - `questionsPerParagraph` (Number): Questions per section (default: 2)
  - `animationDelay` (Number): Animation timing in ms (default: 150)
  - `debugMode` (Boolean): Enable debug logging (default: false)

**Returns:** Promise<AutoBlogQuestionInjector>

**Example:**
```javascript
AutoBlogQuestionInjector.autoInit({
  apiKey: 'pub_YOUR_KEY',
  debugMode: true
});
```

---

## 🎯 Examples

### Example 1: Basic Blog

```html
<!DOCTYPE html>
<html>
<head>
    <title>My Blog Post</title>
</head>
<body>
    <article>
        <h1>10 Tips for Better Coding</h1>
        <p>Paragraph 1...</p>
        <p>Paragraph 2...</p>
        <!-- Questions will auto-inject here -->
    </article>

    <script src="https://cdn.yourdomain.com/auto-blog-question-injector.js"></script>
    <script>
      AutoBlogQuestionInjector.autoInit({
        apiKey: 'pub_abc123xyz789'
      });
    </script>
</body>
</html>
```

### Example 2: With Error Handling

```html
<script src="/auto-blog-question-injector.js"></script>
<script>
  AutoBlogQuestionInjector.autoInit({
    apiKey: 'pub_abc123xyz789',
    debugMode: true
  }).then(injector => {
    console.log('✅ Questions loaded!');
  }).catch(error => {
    console.error('❌ Failed to load questions:', error);
  });
</script>
```

---

## 📝 Changelog

### Version 2.1.0 (Current)
- ✅ Added API key authentication
- ✅ Improved error messages
- ✅ Added security warnings

### Version 2.0.0
- Initial release with auto-detection
- Responsive design
- Interactive answer drawers

---

## 📄 License & Terms

By using this service, you agree to:
- Keep your API key secure
- Use it only on your registered domain
- Not abuse the API or attempt unauthorized access

---

**Need your API key?** Contact your administrator to get started! 🚀


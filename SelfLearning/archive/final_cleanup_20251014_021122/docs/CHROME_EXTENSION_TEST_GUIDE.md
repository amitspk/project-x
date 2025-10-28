# 🔌 Chrome Extension Testing Guide - 2-Service Architecture

**Updated**: October 13, 2025  
**Status**: ✅ Ready to test with Content Processing Service

---

## ✅ What Was Updated

The Chrome extension has been configured to use the new Content Processing Service:

- ✅ **Old API**: `http://localhost:8001/api/v1`
- ✅ **New API**: `http://localhost:8005/api/v1`

Files updated:
- `chrome-extension/content.js`
- `chrome-extension/auto-blog-question-injector.js`
- `chrome-extension/config.js` (created)

---

## 🚀 How to Test

### **Step 1: Ensure Services Are Running**

```bash
# Check Content Processing Service
curl http://localhost:8005/health

# Check if questions are available
curl "http://localhost:8005/api/v1/questions/by-url?blog_url=https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a"
```

Expected: Should return 3 questions ✅

---

### **Step 2: Load/Reload Chrome Extension**

1. Open Chrome browser
2. Go to: `chrome://extensions/`
3. Enable "Developer mode" (top right toggle)
4. Click "Load unpacked" (or "Reload" if already loaded)
5. Select the `chrome-extension` directory from this project
6. Extension should load successfully ✅

---

### **Step 3: Visit the Processed Blog**

1. Open a new tab in Chrome
2. Visit: `https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a`
3. Wait for the page to load completely (~3-5 seconds)
4. Questions should automatically appear on the blog! 🎉

---

## 🎯 What You Should See

### **Before Extension**
- Regular Medium blog article
- No additional UI elements

### **After Extension (Expected)**
```
⚡ quick AI answers

┌─────────────────────────────────────────┐
│ 💡 How does ThreadLocal in Java differ  │
│    from traditional variables?          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 🔍 What was the motivation behind        │
│    introducing ThreadLocal in Java?     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 📊 Can you provide a practical example  │
│    of using ThreadLocal in Java apps?   │
└─────────────────────────────────────────┘
```

---

## 🖱️ Interactive Features to Test

### **1. Click on a Question**
- Click any question card
- Answer drawer should slide in from the right
- Should show:
  - Full question
  - Complete answer
  - Search box for custom questions
  - Related articles section

### **2. Search Custom Question**
- Click a question to open drawer
- Type a question in the search box (e.g., "What is thread safety?")
- Click search button
- AI answer should replace the original answer
- When you close and reopen, original answer should restore

### **3. View Related Articles**
- Click a question
- Scroll down in the drawer
- "Related Articles" section should show similar blogs
- Each article should be a clickable link
- Should show similarity percentage

### **4. Close Drawer**
- Click the X button or click outside
- Drawer should smoothly slide out
- Original question cards remain on page

---

## 🔍 Troubleshooting

### **Problem: Questions don't appear**

**Check 1: Is the service running?**
```bash
curl http://localhost:8005/health
```

**Check 2: Are questions in the database?**
```bash
curl "http://localhost:8005/api/v1/questions/by-url?blog_url=https://medium.com/@alxkm/effective-use-of-threadlocal-in-java-applications-f4eb6a648d4a"
```

**Check 3: Browser console errors?**
1. Open Chrome DevTools (F12)
2. Go to Console tab
3. Look for errors
4. Common issues:
   - CORS errors → Add CORS headers to Content Service
   - 404 errors → Service not running
   - Network errors → Wrong URL in extension

**Check 4: Is the extension loaded?**
- Go to `chrome://extensions/`
- Find "Blog Question Injector"
- Should have "Enabled" toggle ON
- Try clicking "Reload" button

---

### **Problem: Questions appear but don't work**

**Check 1: Click handler working?**
- Open Console (F12)
- Click a question
- Should see logs like "Question clicked: ..."

**Check 2: Answer drawer appearing?**
- Check if drawer HTML is created
- Look for element with class `abqi-drawer`
- Check CSS is loaded

**Check 3: API calls working?**
- Open Network tab in DevTools
- Click a question
- Should see API call to `/api/v1/similar/blogs`
- Check response status

---

### **Problem: Similar blogs don't show**

**Reason**: Need more blogs in database!

The similarity search requires multiple blogs to compare. Currently we only have 1 blog processed.

**Solution**: Process more blogs:
```bash
curl -X POST http://localhost:8005/api/v1/processing/process \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://medium.com/another-java-article",
    "num_questions": 5
  }'
```

---

## 📊 Test Different URLs

Once you've verified it works, test with other blogs:

### **Test with More Medium Articles**

1. Process a new blog:
```bash
curl -X POST http://localhost:8005/api/v1/processing/process \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "PASTE_MEDIUM_ARTICLE_URL_HERE",
    "num_questions": 5
  }'
```

2. Wait for processing (~10 seconds)

3. Visit that URL in Chrome

4. Questions should appear!

---

## 🎨 Customize the Appearance

The extension uses modern pill-shaped cards with pastel colors:

- **Icons**: 💡 🔍 📊 🎯 ⚡ 🚀
- **Colors**: Soft pastels (light blue, pink, green, etc.)
- **Style**: Rounded corners, subtle shadows
- **Animation**: Smooth fade-in and slide effects

To customize:
- Edit CSS in `chrome-extension/auto-blog-question-injector.js`
- Look for the `getStyles()` method
- Modify colors, sizes, animations

---

## 📱 Mobile Responsiveness

The extension is fully responsive! Test on:

- **Desktop**: Full cards with icons
- **Tablet**: Slightly smaller cards
- **Mobile**: Compact view, optimized touch targets

Note: Chrome extensions work best on desktop. For mobile, you'd need a bookmarklet or mobile app.

---

## 🔄 Quick Reset

If things get messed up:

1. **Reload Extension**:
   - Go to `chrome://extensions/`
   - Click "Reload" button

2. **Clear Browser Cache**:
   - Settings → Privacy → Clear browsing data
   - Select "Cached images and files"

3. **Restart Services**:
   ```bash
   # Restart Content Service
   pkill -f content_processing_service
   ./venv/bin/python -m content_processing_service.run_server
   ```

4. **Reload Page**:
   - Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)

---

## ✅ Test Checklist

- [ ] Extension loads without errors
- [ ] Visit processed blog URL
- [ ] Questions appear on page
- [ ] "⚡ quick AI answers" header shows once
- [ ] Question cards have correct icons
- [ ] Questions are styled correctly
- [ ] Clicking question opens drawer
- [ ] Drawer shows full answer
- [ ] Search box is visible
- [ ] Related articles section exists
- [ ] Closing drawer works
- [ ] Reopening shows original answer
- [ ] Multiple questions work
- [ ] Page scrolling still works
- [ ] Blog content not disrupted

---

## 🎉 Success Criteria

Your test is successful when:

1. ✅ Questions appear automatically on the blog
2. ✅ Questions are clickable and show answers
3. ✅ Answer drawer works smoothly
4. ✅ Search functionality works
5. ✅ Similar articles display (if multiple blogs processed)
6. ✅ Extension doesn't break the blog's original content
7. ✅ Performance is good (no lag or freezing)

---

## 📸 Expected Screenshots

### **Questions Injected**
You should see pill-shaped cards with:
- Icon on the left (💡 🔍 📊)
- Question text
- Hover effect
- Smooth animations

### **Answer Drawer**
When clicked, right-side drawer with:
- Full answer text
- Search bar at bottom
- "Related Articles" section
- Close button (X)

---

## 🚀 Next Steps After Testing

1. **Process More Blogs**:
   - Build up your database with more articles
   - Test similarity search with 10+ blogs

2. **Test on Different Sites**:
   - Supported: Medium, Dev.to, Hashnode, Substack
   - Process blogs from each platform

3. **Share with Users**:
   - Package extension for distribution
   - Add to Chrome Web Store (optional)

4. **Monitor Performance**:
   - Check API response times
   - Monitor MongoDB query performance
   - Watch Redis cache hit rates

---

## 💡 Pro Tips

1. **Enable Debug Mode**: Set `debugMode: true` in extension config to see detailed logs

2. **Use Extension Popup**: Click extension icon for manual controls

3. **Test Network Conditions**: Use Chrome DevTools to simulate slow 3G

4. **Check Memory Usage**: Open Chrome Task Manager to monitor extension resource usage

5. **Test with Ad Blockers**: Ensure extension works with common ad blockers

---

**Ready to test! Visit the Medium article and watch the magic happen! ✨**


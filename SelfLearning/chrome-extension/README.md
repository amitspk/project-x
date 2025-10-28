# Blog Question Injector - Chrome Extension

A Chrome extension that allows you to inject interactive questions into any website to test question placement and engagement features.

## 🚀 Features

### **Inject Questions on Any Website**
- **Default Questions**: Smart questions generated for any webpage
- **Custom JSON Upload**: Upload your generated question JSON files
- **Multiple Placement Strategies**: Test after_paragraph, sidebar, floating, etc.
- **Theme Support**: Default, dark, and minimal themes

### **Easy Testing Interface**
- **One-Click Injection**: Simple popup interface
- **Real-Time Statistics**: See question count and placement info
- **Quick Removal**: Remove all questions with one click
- **Settings Persistence**: Remembers your theme and debug preferences

### **Context Menu Integration**
- **Right-Click Injection**: Inject questions via context menu
- **Selection-Based Questions**: Generate questions for selected text
- **Quick Actions**: Fast access without opening popup

## 📦 Installation

### **Method 1: Load Unpacked (Development)**

1. **Open Chrome Extensions**:
   ```
   chrome://extensions/
   ```

2. **Enable Developer Mode**:
   - Toggle "Developer mode" in the top right

3. **Load Extension**:
   - Click "Load unpacked"
   - Select the `chrome-extension` folder
   - Extension will appear in your toolbar

### **Method 2: Create Icons (Optional)**

The extension works without icons, but for a better experience:

1. **Convert the SVG**:
   - Use the provided `icons/icon.svg`
   - Convert to PNG files: 16x16, 32x32, 48x48, 128x128
   - Name them: `icon16.png`, `icon32.png`, `icon48.png`, `icon128.png`

2. **Place in Icons Folder**:
   ```
   chrome-extension/icons/
   ├── icon16.png
   ├── icon32.png
   ├── icon48.png
   └── icon128.png
   ```

## 🎯 How to Use

### **Basic Usage**

1. **Navigate to Any Website**:
   - Open any blog, article, or webpage

2. **Click Extension Icon**:
   - Click the Blog Question Injector icon in toolbar
   - Popup interface will open

3. **Inject Questions**:
   - Click "Inject Default Questions" for smart questions
   - Or upload your JSON file and click "Inject Custom Questions"

4. **Interact with Questions**:
   - Questions appear based on placement strategies
   - Click any question to open the answer drawer
   - Test different themes and animations

### **Using Your Generated JSON Files**

1. **Upload JSON**:
   - Click "Upload JSON File" in the popup
   - Select any file from your `generated_questions/` folder
   - Example: `timesofindia_indiatimes_com_...questions.json`

2. **Inject Custom Questions**:
   - Click "Inject Custom Questions"
   - Your real questions will be placed according to their metadata

3. **Test Placement**:
   - See how `after_paragraph` questions appear
   - Check `sidebar` and `floating` placements
   - Verify `inline_highlight` functionality

### **Context Menu Usage**

1. **Right-Click on Page**:
   - Select "Inject Questions Here"
   - Questions will be added immediately

2. **Select Text First**:
   - Highlight any text on the page
   - Right-click → "Generate Questions for Selection"
   - Custom question created for that text

3. **Quick Removal**:
   - Right-click → "Remove All Questions"

## ⚙️ Settings & Options

### **Theme Options**
- **Default**: Clean, professional appearance
- **Dark**: Dark mode for dark websites
- **Minimal**: Subtle, minimal styling

### **Debug Mode**
- **Enable**: See console logs and detailed information
- **Disable**: Clean, production-like experience

### **Persistent Settings**
- Theme and debug preferences are saved
- Restored when you reopen the extension

## 🔧 File Structure

```
chrome-extension/
├── manifest.json          # Extension configuration
├── popup.html            # Extension popup interface
├── popup.js              # Popup logic and controls
├── content.js            # Content script (runs on all pages)
├── background.js         # Background service worker
├── question-injector.js  # Main question injector module
├── icons/               # Extension icons
│   ├── icon.svg         # SVG template
│   └── placeholder.txt  # Icon instructions
└── README.md           # This file
```

## 🎯 Use Cases

### **For Developers**
- **Test Question Placement**: See how questions look on different websites
- **Validate JSON Files**: Upload and test your generated question files
- **Debug Placement Logic**: Use debug mode to see placement decisions
- **Theme Testing**: Test how questions look with different themes

### **For Content Creators**
- **Preview Questions**: See how questions will look on your blog
- **Test User Experience**: Experience the full interaction flow
- **Validate Engagement**: Test if questions enhance content engagement
- **Cross-Site Testing**: Test questions on various website layouts

### **For Quality Assurance**
- **Regression Testing**: Ensure questions work across different sites
- **Browser Compatibility**: Test in different Chrome versions
- **Performance Testing**: Check impact on page load and performance
- **User Experience**: Validate the complete user journey

## 🚀 Advanced Usage

### **Testing Your Generated Files**

```javascript
// Your workflow:
1. Generate questions: python content_processor.py --process-all
2. Open Chrome extension on target website
3. Upload: generated_questions/your_file.json
4. Click: "Inject Custom Questions"
5. Test: All placement strategies and interactions
```

### **Bulk Testing Multiple Sites**

1. **Open Multiple Tabs**:
   - Different blog sites, news sites, documentation
   
2. **Test Same JSON**:
   - Upload your JSON file in each tab
   - See how placement adapts to different layouts
   
3. **Compare Results**:
   - Note which sites work best
   - Identify layout patterns that work well

### **Custom Question Development**

1. **Start with Extension**:
   - Use default questions to understand placement
   
2. **Iterate JSON Structure**:
   - Modify your question generation prompts
   - Test new placement strategies
   
3. **Refine Based on Results**:
   - Adjust paragraph detection logic
   - Improve question relevance

## 🐛 Troubleshooting

### **Extension Not Loading**
- Check Chrome version (requires Chrome 88+)
- Ensure Developer Mode is enabled
- Reload extension after code changes

### **Questions Not Appearing**
- Check browser console for errors (F12)
- Enable Debug Mode in extension settings
- Verify JSON file structure is correct

### **Placement Issues**
- Some websites have complex layouts
- Try different placement strategies
- Check if content is in iframes (not supported)

### **Performance Issues**
- Large JSON files may take time to process
- Complex websites may have slower injection
- Disable other extensions if conflicts occur

## 🔒 Privacy & Permissions

### **Required Permissions**
- **activeTab**: Access current tab for injection
- **storage**: Save user preferences
- **scripting**: Inject question scripts
- **host_permissions**: Access all websites for testing

### **Data Handling**
- **No Data Collection**: Extension doesn't send data anywhere
- **Local Storage Only**: Settings saved locally in Chrome
- **No Network Requests**: All processing happens locally

## 📈 Performance

### **Optimized for Speed**
- **Lazy Loading**: Scripts loaded only when needed
- **Efficient DOM Queries**: Optimized element selection
- **Memory Management**: Proper cleanup when removing questions

### **Minimal Impact**
- **Small Bundle Size**: ~15KB total extension size
- **No Background Processing**: Only active when used
- **Clean Removal**: Complete cleanup when questions removed

## 🤝 Development

### **Making Changes**

1. **Edit Files**: Modify any extension files
2. **Reload Extension**: Go to `chrome://extensions/` and click reload
3. **Test Changes**: Open popup or inject questions to test

### **Adding Features**

1. **Popup Features**: Edit `popup.html` and `popup.js`
2. **Injection Logic**: Modify `content.js`
3. **Background Tasks**: Update `background.js`

### **Debugging**

1. **Popup Debugging**: Right-click popup → "Inspect"
2. **Content Script Debugging**: F12 on any webpage
3. **Background Script**: `chrome://extensions/` → "Inspect views: background page"

## 📞 Support

### **Common Issues**
- Check the troubleshooting section above
- Enable debug mode for detailed logs
- Test with simple websites first

### **Extension Development**
- Chrome Extension documentation: https://developer.chrome.com/docs/extensions/
- Manifest V3 guide: https://developer.chrome.com/docs/extensions/mv3/

---

**Ready to test your question injection system on any website!** 🎉

Install the extension, upload your generated JSON files, and see your questions come to life on any webpage.

---

## 🔄 Relationship to ui-js/

**IMPORTANT**: This chrome-extension is a **test harness only**!

The actual production library is in: `../ui-js/auto-blog-question-injector.js`

This extension:
- ✅ Tests the library in a browser environment
- ✅ Simulates how it works on publisher sites
- ❌ Is NOT what publishers deploy

Publishers deploy: `ui-js/auto-blog-question-injector.js`


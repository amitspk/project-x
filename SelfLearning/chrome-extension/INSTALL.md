# Quick Installation Guide

## 🚀 Install the Chrome Extension (2 minutes)

### **Step 1: Open Chrome Extensions**
1. Open Google Chrome
2. Go to: `chrome://extensions/`
3. Or: Menu → More Tools → Extensions

### **Step 2: Enable Developer Mode**
1. Look for "Developer mode" toggle in the top right
2. Click to enable it
3. New buttons will appear

### **Step 3: Load the Extension**
1. Click "Load unpacked" button
2. Navigate to and select this folder:
   ```
   ~/Documents/personal_repo/SelfLearning/chrome-extension
   ```
3. Click "Select Folder"

### **Step 4: Verify Installation**
- Extension should appear in the list
- Look for "Blog Question Injector" 
- You should see it in your Chrome toolbar (puzzle piece icon)

## 🎯 Quick Test

### **Test 1: Default Questions**
1. Go to any website (e.g., `https://medium.com`)
2. Click the extension icon in toolbar
3. Click "Inject Default Questions"
4. Questions should appear on the page!

### **Test 2: Your JSON File**
1. Stay on the same website
2. Click "Upload JSON File" in the popup
3. Select: `~/Documents/personal_repo/SelfLearning/generated_questions/timesofindia_indiatimes_com_timesofindia_indiatimes_com_technology_tech_news_silicon_valley_startup_ceo_challenges_us_h_1b_vi_questions.json`
4. Click "Inject Custom Questions"
5. Your real generated questions appear!

## 🐛 Troubleshooting

### **"Failed to load extension" Error**
✅ **Fixed!** The manifest has been updated to work without icons.

### **Extension Not Visible**
- Check if it's hidden: Click puzzle piece icon in toolbar
- Pin the extension for easy access

### **Questions Not Appearing**
- Check browser console (F12) for errors
- Enable "Debug Mode" in extension popup
- Try on a simple website first (like Wikipedia)

### **Permission Errors**
- Make sure you selected the correct folder
- The folder should contain `manifest.json`
- Try reloading the extension

## 🔄 Making Changes

If you modify the extension code:
1. Go to `chrome://extensions/`
2. Find "Blog Question Injector"
3. Click the refresh/reload icon
4. Test your changes

## ✅ Success Indicators

You'll know it's working when:
- ✅ Extension loads without errors
- ✅ Icon appears in Chrome toolbar
- ✅ Popup opens when clicked
- ✅ Questions inject on websites
- ✅ Drawers open when questions are clicked

**Ready to test your question injection system on any website!** 🎉

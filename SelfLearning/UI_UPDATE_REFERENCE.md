# UI Update Reference - Question Card Design

## 🎨 Design Implementation (Based on Screenshot)

### Header
**"Some Questions in Mind?"**
- Font: 20px, Bold (700)
- Color: #1a1a1a
- Margin: 32px top, 24px bottom

### Question Cards

#### Structure
```
┌─────────────────────────────────────┐
│  🤔 (Icon - Circular, 56px)         │
│                                     │
│  Question text here...              │
│  (15px, Semi-bold, #2c3e50)        │
│                                     │
│  EXPLORE →                          │
│  (12px, Bold, uppercase)            │
└─────────────────────────────────────┘
```

#### Colors (Rotating 3 colors)
1. **Beige** (Card 1): `#f5f0e8` → Hover: `#ede7dd`
2. **Purple** (Card 2): `#e8e4f3` → Hover: `#ddd7eb`
3. **Coral** (Card 3): `#fce8e6` → Hover: `#f7ddd9`

#### Dimensions
- Border Radius: 16px
- Padding: 20px
- Margin between cards: 12px
- Icon: 56px circle (white background with border)
- Gap between icon & text: 16px
- Gap between text & button: 12px

### Interactions

#### Hover Effects
1. **Card**: Lifts 3px up with enhanced shadow
2. **Arrow**: Slides 3px to the right
3. **Background**: Slightly darker shade

#### Click Behavior
- Opens answer drawer (existing functionality)
- Card gets active state with stronger shadow

### Responsive Breakpoints

#### Desktop (>1024px)
- Icon: 56px
- Text: 15px
- Padding: 20px
- Border Radius: 16px

#### Tablet (769px - 1024px)
- Icon: 52px
- Text: 14px
- Padding: 18px
- Border Radius: 16px

#### Mobile (<768px)
- Icon: 48px
- Text: 14px
- Padding: 16px
- Border Radius: 14px
- Explore button: 11px

## 📝 Key Changes from Old Design

| Aspect | Old Design | New Design |
|--------|-----------|------------|
| Header | "⚡ quick AI answers" | "Some Questions in Mind?" |
| Layout | Horizontal pill | Vertical card |
| Shape | Rounded pill (50px radius) | Rounded rectangle (16px radius) |
| Colors | Green, Purple, Blue | Beige, Purple, Coral |
| Structure | Icon + Text (side by side) | Icon → Text → Button (stacked) |
| Button | None | "EXPLORE →" button |
| Icon Position | Left (inline) | Top-left (stacked) |

## 🚀 Testing Instructions

1. **Reload Extension**
   ```
   chrome://extensions/
   → Find "Auto Blog Question Injector"
   → Click refresh icon 🔄
   ```

2. **Test URL**
   ```
   https://www.baeldung.com/java-hashmap
   ```

3. **Expected Result**
   - Header: "Some Questions in Mind?"
   - Cards with beige, purple, coral backgrounds
   - Circular icons on top-left
   - Question text below icon
   - "EXPLORE →" button at bottom
   - Smooth hover animations

## 📦 Files Modified

- ✅ `ui-js/auto-blog-question-injector.js`
- ✅ `chrome-extension/auto-blog-question-injector.js`

Both files are identical and contain the complete new design implementation.


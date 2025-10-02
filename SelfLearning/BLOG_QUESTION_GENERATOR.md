# Blog Question Generator

A production-grade system that generates exploratory questions from blog content with metadata for JavaScript library injection and intelligent placement.

## 🎯 Overview

This system analyzes blog content and generates ~10 exploratory questions that:
- **Enhance reader engagement** with thought-provoking questions
- **Provide intelligent placement** with paragraph-level precision
- **Include comprehensive metadata** for JavaScript integration
- **Support multiple question types** (clarification, examples, comparisons, etc.)
- **Offer production-ready JSON output** for web deployment

## 🚀 Features

### **Content Analysis**
- **Paragraph Detection**: Automatically identifies and indexes paragraphs
- **Context Analysis**: Extracts topic, keywords, difficulty level, content type
- **Section Mapping**: Associates questions with specific content sections
- **Reading Time Estimation**: Calculates estimated reading time

### **Question Generation**
- **10 Question Types**: Clarification, deeper dive, practical, comparison, example, implication, related, challenge, future, beginner
- **Smart Distribution**: Balanced variety across question types
- **Confidence Scoring**: LLM confidence ratings (0-1) for each question
- **Contextual Relevance**: Questions tied to specific paragraph content

### **JavaScript Integration**
- **Placement Strategies**: After paragraph, before section, inline highlight, sidebar, floating
- **Animation Support**: Fade in, slide up, bounce animations
- **Trigger Events**: Scroll, click, hover, time-based triggers
- **Priority System**: 1-10 priority levels for question importance
- **Theme Support**: Default, highlight, subtle themes

## 📋 JSON Output Schema

```json
{
  "content_id": "unique_identifier",
  "content_title": "Blog Post Title",
  "content_context": {
    "topic": "Main Topic",
    "keywords": ["keyword1", "keyword2"],
    "difficulty_level": "beginner|intermediate|advanced",
    "content_type": "tutorial|explanation|news|review",
    "estimated_reading_time": 5
  },
  "questions": [
    {
      "id": "q1",
      "question": "Exploratory question text?",
      "answer": "Detailed answer with context...",
      "question_type": "clarification|example|comparison|...",
      "context": "Relevant context from content",
      "metadata": {
        "placement_strategy": "after_paragraph|before_section|...",
        "target_paragraph": {
          "paragraph_index": 0,
          "text_snippet": "First 50 chars for identification...",
          "word_count": 45,
          "section_title": "Section Name"
        },
        "priority": 9,
        "delay_ms": 500,
        "trigger_event": "scroll",
        "animation": "fade_in",
        "theme": "default"
      },
      "confidence_score": 0.9
    }
  ],
  "generation_timestamp": "2025-01-28T19:31:24.256Z",
  "llm_model": "gpt-4",
  "total_questions": 10,
  "average_confidence": 0.84
}
```

## 🛠️ Usage

### **Command Line Interface**

```bash
# From file
python blog_question_generator.py --file blog.txt --title "Blog Title" --num-questions 10

# From direct content
python blog_question_generator.py --content "Your blog content..." --output questions.json

# From URL (with web crawler)
python blog_question_generator.py --url https://example.com/blog --num-questions 12

# With custom settings
python blog_question_generator.py --file blog.txt --content-id "blog_001" --output custom.json
```

### **Programmatic Usage**

```python
from llm_service import LLMService
from llm_service.services.question_generator import QuestionGenerator

# Initialize services
llm_service = LLMService()
await llm_service.initialize()

question_generator = QuestionGenerator(llm_service)

# Generate questions
question_set = await question_generator.generate_questions(
    content=blog_content,
    title="Blog Title",
    num_questions=10
)

# Convert to JSON
json_output = question_set_to_json(question_set)
```

### **JavaScript Integration**

```javascript
// Load questions from generated JSON
fetch('questions.json')
  .then(response => response.json())
  .then(questionsData => {
    new BlogQuestionManager(questionsData);
  });

// The BlogQuestionManager handles:
// - Scroll-based question triggering
// - Intelligent paragraph placement
// - Animation and theming
// - User interaction tracking
```

## 📊 Example Output

**Generated for Machine Learning Blog:**
- **8 Questions Generated**
- **Average Confidence: 0.84**
- **Question Types**: 4 clarification, 3 comparison, 1 example
- **All Placed**: After specific paragraphs with scroll triggers

**Sample Questions:**
1. "How does machine learning differ from traditional programming?" (Confidence: 0.90)
2. "Can you provide an example of supervised learning?" (Confidence: 0.85)
3. "How does unsupervised learning differ from supervised learning?" (Confidence: 0.85)

## 🎨 JavaScript Library Features

### **BlogQuestionManager Class**
```javascript
class BlogQuestionManager {
  constructor(questionsData)     // Initialize with JSON data
  setupScrollListener()          // Handle scroll-based triggers
  injectQuestions()             // Place questions in DOM
  showQuestion(question)        // Animate question appearance
  toggleAnswer(questionId)      // Show/hide answers
  findTargetParagraph(ref)      // Locate target paragraphs
}
```

### **Placement Strategies**
- **`after_paragraph`**: Insert after specific paragraph
- **`before_section`**: Insert before section heading
- **`inline_highlight`**: Highlight text with question bubble
- **`sidebar`**: Place in sidebar with reference line
- **`floating`**: Floating question bubble

### **Animation Options**
- **`fade_in`**: Smooth opacity transition
- **`slide_up`**: Slide from bottom
- **`bounce`**: Bouncy entrance effect

### **Trigger Events**
- **`scroll`**: Show when paragraph comes into view
- **`click`**: Show on paragraph click
- **`hover`**: Show on paragraph hover
- **`time`**: Show after time delay

## 🔧 Configuration

### **Environment Setup**
```bash
# Required API key
export OPENAI_API_KEY="your-openai-key"

# Optional configuration
export LLM_DEFAULT_TEMPERATURE="0.7"
export LLM_DEFAULT_MAX_TOKENS="4000"
```

### **Question Generation Parameters**
- **`num_questions`**: 5-15 questions (default: 10)
- **`temperature`**: 0.1-1.0 creativity level (default: 0.7)
- **`max_tokens`**: Response length limit (default: 4000)

## 📁 File Structure

```
llm_service/
├── models/
│   └── question_schema.py     # JSON schema and data models
├── services/
│   └── question_generator.py # Question generation logic
└── core/
    └── service.py            # LLM service integration

blog_question_generator.py    # CLI interface
javascript_integration_example.html  # Web integration demo
sample_blog.txt              # Example blog content
ml_questions.json           # Generated questions output
```

## 🎯 Use Cases

### **Educational Platforms**
- **Interactive Learning**: Engage students with contextual questions
- **Comprehension Checks**: Verify understanding at key points
- **Discussion Starters**: Generate classroom discussion topics

### **Content Marketing**
- **Reader Engagement**: Increase time on page with interactive elements
- **Lead Generation**: Capture emails through question interactions
- **Content Analytics**: Track which questions resonate most

### **Documentation Sites**
- **User Guidance**: Help users understand complex concepts
- **FAQ Generation**: Create frequently asked questions automatically
- **Support Reduction**: Answer common questions proactively

### **News and Media**
- **Reader Education**: Provide context for complex topics
- **Engagement Metrics**: Track reader interaction with content
- **Personalization**: Adapt questions based on reader behavior

## 🚀 Production Deployment

### **Performance Considerations**
- **Lazy Loading**: Questions load as users scroll
- **Caching**: Cache generated questions for repeat visitors
- **Analytics**: Track question engagement and effectiveness

### **Integration Steps**
1. **Generate Questions**: Run CLI tool on your blog content
2. **Upload JSON**: Store questions.json on your server
3. **Include Library**: Add BlogQuestionManager to your site
4. **Initialize**: Load questions and start the manager
5. **Customize**: Adjust styling and behavior for your brand

### **Monitoring and Analytics**
```javascript
// Track question interactions
questionManager.on('questionShown', (questionId) => {
  analytics.track('Question Shown', { questionId });
});

questionManager.on('answerToggled', (questionId) => {
  analytics.track('Answer Viewed', { questionId });
});
```

## 🔮 Advanced Features

### **A/B Testing Support**
- Test different question types and placements
- Measure engagement and conversion impact
- Optimize question generation parameters

### **Personalization**
- Adapt questions based on user reading history
- Adjust difficulty level for different audiences
- Customize question types for user preferences

### **Multi-language Support**
- Generate questions in multiple languages
- Localize question types and cultural context
- Support RTL languages and different writing systems

The Blog Question Generator provides a complete solution for creating engaging, contextual questions that enhance reader experience and provide valuable insights for content creators.

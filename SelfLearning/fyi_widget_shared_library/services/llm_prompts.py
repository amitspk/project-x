"""
Shared prompts and format templates for LLM providers.

These are used across all providers (OpenAI, Anthropic, etc.)
"""

# PART 1: OUTPUT FORMAT ENFORCEMENT (Non-negotiable, always used)
# ----------------------------------------------------------------
# Pure format instruction - no role, just format rules

OUTPUT_FORMAT_INSTRUCTION = """You MUST respond ONLY with valid JSON in the exact format specified below.
Do not include any text, explanation, or markdown outside the JSON structure.
Never deviate from the required JSON schema.

CRITICAL REQUIREMENTS:
- Every question MUST have both "question" and "answer" fields populated with non-empty strings
- All questions must be complete and valid
- Do not include any questions with empty, null, or missing fields"""


# PART 2: ROLE + INSTRUCTIONS (Customizable with fallback)
# ----------------------------------------------------------
# Combines the LLM's role and content generation instructions
# Publishers can customize this entire section

DEFAULT_QUESTIONS_PROMPT = """You are an expert AI assistant specializing in creating curiosity-driven, value-adding questions for a content engagement widget.

Your primary goal is to generate a diverse set of questions based on the provided article text. You will follow the "Verbalized Blended Insight Framework."

FRAMEWORK PRINCIPLES:

1. Knowledge Expansion: Each question must promise a genuine, deep-dive answer that goes beyond the surface-level facts of the article.

2. Commercial Viability: The question's phrasing must naturally contain high-value keywords and concepts with a strong, existing ad market.

3. Psychological Framing: Each question must be framed using a powerful psychological hook (e.g., promising a secret, highlighting a hidden danger, challenging a common assumption).

4. Defined Tone of Voice: The tone must be curious, insightful, and intelligent—never sensationalist.

DIVERSITY REQUIREMENT (Verbalized Sampling):

To ensure a high degree of conceptual diversity and avoid "mode collapse," you must use the Verbalized Sampling (VS) technique. For each generated question, you must also provide its corresponding probability relative to the full distribution of possible responses given the input prompt, on a scale from 0.0 to 1.0.

CRITICAL CONSTRAINTS:

1. No Cannibalization: Questions must not ask for information that is already explicitly answered in the provided article text.

2. Concise Answerability: Ensure all questions are realistically answerable in a brief, summary format (approx. 150-200 words / 800-1000 characters) suitable for a mobile UI panel. Avoid overly broad topics.

3. Question Length: All questions must be a maximum of 80 characters."""

DEFAULT_SUMMARY_PROMPT = """You are a helpful assistant that creates semantic-rich summaries for blog posts optimized for article discovery and relatedness matching.

Create a comprehensive summary that includes:

1. **Title (concise, maximum 100 characters)**: Generate an accurate, descriptive title that captures the main topic and key focus of the article. This title should be clear, informative, and reflect the primary subject matter.

2. **Main Summary (2-3 sentences)**: Capture the core topic, main message, and primary focus of the article. Include key concepts, themes, topics, or subject matter that readers might ask questions about. Make it semantically rich with relevant terminology and descriptive language that captures the essence of the content.

3. **Key Points (3-5 points)**: Extract the most important ideas, concepts, topics, and themes covered in the article. Each key point should:
   - Represent a distinct topic, concept, or theme that could generate questions
   - Include relevant terminology and subject-specific language appropriate to the content domain
   - Be semantically meaningful for content discovery and relatedness matching
   - Cover different aspects of the article (main ideas, practical applications, comparisons, insights, examples, etc.)

4. **Optimization for Semantic Search**: Structure the summary to maximize semantic similarity matching with potential questions. Include:
   - Core topics and themes readers might explore or ask about
   - Related concepts, ideas, or subject matter mentioned
   - Key information, insights, or points discussed
   - Relevant terminology, names, or domain-specific language that appears in the content

The summary will be vectorized and used to find related articles when users click on questions. Ensure it captures the semantic essence and key topics that would help match questions to relevant articles across any content domain (technology, food, news, education, lifestyle, business, etc.)."""


# FORMAT TEMPLATES (Non-negotiable - Schema Definition)
# -------------------------------------------------------
# Shown to LLM as examples of exact JSON structure required

QUESTIONS_JSON_FORMAT = """{
    "questions": [
        {
            "question": "Question text here?",
            "answer": "Detailed answer here.",
            "icon": "💡"
        }
    ]
}"""

SUMMARY_JSON_FORMAT = """{
    "title": "A concise, descriptive title (max 100 characters)",
    "summary": "A 2-3 sentence summary of the main content",
    "key_points": ["key point 1", "key point 2", "key point 3"]
}"""


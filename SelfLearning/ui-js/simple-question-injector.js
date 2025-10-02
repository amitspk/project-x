/**
 * Simple Blog Question Injector
 * Automatically detects paragraphs and places 3 questions after every paragraph
 * Shows actual question text, not just symbols
 */

class SimpleBlogQuestionInjector {
    constructor() {
        this.questions = [];
        this.currentQuestionIndex = 0;
        this.injectedElements = [];
        this.isInjected = false;
    }

    /**
     * Load questions from a JSON file URL
     * @param {string} jsonUrl - URL to the questions JSON file
     * @param {Object} options - Configuration options
     */
    static async loadFromFile(jsonUrl, options = {}) {
        try {
            const response = await fetch(jsonUrl);
            if (!response.ok) {
                throw new Error(`Failed to fetch questions: ${response.status}`);
            }
            const data = await response.json();
            return SimpleBlogQuestionInjector.loadFromData(data, options);
        } catch (error) {
            console.error('Error loading questions from file:', error);
            throw error;
        }
    }

    /**
     * Load questions from data object
     * @param {Object} data - Questions data object
     * @param {Object} options - Configuration options
     */
    static async loadFromData(data, options = {}) {
        const injector = new SimpleBlogQuestionInjector();
        await injector.initialize(data, options);
        return injector;
    }

    /**
     * Initialize the injector with questions data
     * @param {Object} data - Questions data
     * @param {Object} options - Configuration options
     */
    async initialize(data, options = {}) {
        this.options = {
            theme: 'default',
            questionsPerParagraph: 3,
            debugMode: false,
            animationDelay: 100,
            ...options
        };

        // Extract questions from data
        this.questions = data.questions || [];
        
        if (this.options.debugMode) {
            console.log('SimpleBlogQuestionInjector initialized with', this.questions.length, 'questions');
        }

        // Auto-inject questions
        await this.injectQuestions();
    }

    /**
     * Find all main content paragraphs on the page
     */
    findMainParagraphs() {
        // Look for paragraphs in common content containers
        const contentSelectors = [
            'article p',
            '.content p',
            '.post-content p', 
            '.entry-content p',
            '.article-content p',
            'main p',
            '.story p',
            '.text p',
            'p' // fallback to all paragraphs
        ];

        let paragraphs = [];
        
        for (const selector of contentSelectors) {
            paragraphs = Array.from(document.querySelectorAll(selector));
            if (paragraphs.length > 0) {
                if (this.options.debugMode) {
                    console.log(`Found ${paragraphs.length} paragraphs using selector: ${selector}`);
                }
                break;
            }
        }

        // Filter out very short paragraphs (likely not main content)
        paragraphs = paragraphs.filter(p => {
            const text = p.textContent.trim();
            return text.length > 50 && !this.isNavigationOrUI(p);
        });

        if (this.options.debugMode) {
            console.log(`Filtered to ${paragraphs.length} main content paragraphs`);
        }

        return paragraphs;
    }

    /**
     * Check if a paragraph is likely navigation or UI element
     */
    isNavigationOrUI(paragraph) {
        const text = paragraph.textContent.toLowerCase();
        const uiKeywords = ['menu', 'navigation', 'subscribe', 'follow', 'share', 'comment', 'login', 'register'];
        return uiKeywords.some(keyword => text.includes(keyword)) || 
               paragraph.closest('nav, header, footer, .menu, .sidebar');
    }

    /**
     * Inject questions after paragraphs
     */
    async injectQuestions() {
        if (this.isInjected) {
            this.cleanup();
        }

        const paragraphs = this.findMainParagraphs();
        
        if (paragraphs.length === 0) {
            console.warn('No suitable paragraphs found for question injection');
            return;
        }

        if (this.questions.length === 0) {
            console.warn('No questions available for injection');
            return;
        }

        let questionIndex = 0;
        
        // Place questions after every paragraph (up to available questions)
        for (let i = 0; i < paragraphs.length && questionIndex < this.questions.length; i++) {
            const paragraph = paragraphs[i];
            const questionsToPlace = Math.min(
                this.options.questionsPerParagraph, 
                this.questions.length - questionIndex
            );

            for (let j = 0; j < questionsToPlace && questionIndex < this.questions.length; j++) {
                const question = this.questions[questionIndex];
                await this.injectQuestionAfterParagraph(paragraph, question, j);
                questionIndex++;
                
                // Small delay for animation effect
                if (this.options.animationDelay > 0) {
                    await this.sleep(this.options.animationDelay);
                }
            }
        }

        this.isInjected = true;
        
        if (this.options.debugMode) {
            console.log(`Injected ${questionIndex} questions after ${paragraphs.length} paragraphs`);
        }
    }

    /**
     * Inject a single question after a paragraph
     */
    async injectQuestionAfterParagraph(paragraph, question, index) {
        const questionElement = this.createQuestionElement(question, index);
        
        // Insert after the paragraph
        paragraph.parentNode.insertBefore(questionElement, paragraph.nextSibling);
        
        // Track for cleanup
        this.injectedElements.push(questionElement);
        
        // Animate in
        setTimeout(() => {
            questionElement.classList.add('sbqi-visible');
        }, 50);
    }

    /**
     * Create a question element
     */
    createQuestionElement(question, index) {
        const container = document.createElement('div');
        container.className = 'sbqi-question-container';
        container.setAttribute('data-question-id', question.id || `q-${index}`);
        
        const questionBox = document.createElement('div');
        questionBox.className = 'sbqi-question-box';
        
        const questionText = document.createElement('div');
        questionText.className = 'sbqi-question-text';
        questionText.textContent = question.question;
        
        // Click handler to open drawer
        questionBox.addEventListener('click', () => {
            this.openAnswerDrawer(question, questionBox);
        });
        
        questionBox.appendChild(questionText);
        container.appendChild(questionBox);
        
        // Add styles if not already added
        this.ensureStyles();
        
        return container;
    }

    /**
     * Open answer drawer
     */
    openAnswerDrawer(question, questionBox) {
        // Close any existing drawer
        this.closeAnswerDrawer();
        
        // Create drawer overlay
        const overlay = document.createElement('div');
        overlay.className = 'sbqi-drawer-overlay';
        overlay.id = 'sbqi-drawer-overlay';
        
        // Create drawer
        const drawer = document.createElement('div');
        drawer.className = 'sbqi-drawer';
        
        // Drawer header
        const header = document.createElement('div');
        header.className = 'sbqi-drawer-header';
        
        const title = document.createElement('h3');
        title.className = 'sbqi-drawer-title';
        title.textContent = 'Question & Answer';
        
        const closeBtn = document.createElement('button');
        closeBtn.className = 'sbqi-drawer-close';
        closeBtn.innerHTML = '×';
        closeBtn.addEventListener('click', () => this.closeAnswerDrawer());
        
        header.appendChild(title);
        header.appendChild(closeBtn);
        
        // Drawer content
        const content = document.createElement('div');
        content.className = 'sbqi-drawer-content';
        
        const questionSection = document.createElement('div');
        questionSection.className = 'sbqi-drawer-question';
        questionSection.innerHTML = `<strong>💭 Question:</strong><br>${question.question}`;
        
        const answerSection = document.createElement('div');
        answerSection.className = 'sbqi-drawer-answer';
        answerSection.innerHTML = `<strong>💡 Answer:</strong><br>${question.answer}`;
        
        // Question metadata
        const metadata = document.createElement('div');
        metadata.className = 'sbqi-drawer-metadata';
        metadata.innerHTML = `
            <div class="sbqi-metadata-item">
                <span class="sbqi-metadata-label">Type:</span>
                <span class="sbqi-metadata-value">${question.question_type || 'exploratory'}</span>
            </div>
            <div class="sbqi-metadata-item">
                <span class="sbqi-metadata-label">Confidence:</span>
                <span class="sbqi-metadata-value">${Math.round((question.confidence_score || 0.8) * 100)}%</span>
            </div>
            <div class="sbqi-metadata-item">
                <span class="sbqi-metadata-label">Reading time:</span>
                <span class="sbqi-metadata-value">${question.estimated_answer_time || 30}s</span>
            </div>
        `;
        
        content.appendChild(questionSection);
        content.appendChild(answerSection);
        content.appendChild(metadata);
        
        drawer.appendChild(header);
        drawer.appendChild(content);
        overlay.appendChild(drawer);
        
        // Add to page
        document.body.appendChild(overlay);
        
        // Animate in
        setTimeout(() => {
            overlay.classList.add('sbqi-drawer-visible');
        }, 10);
        
        // Close on overlay click
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                this.closeAnswerDrawer();
            }
        });
        
        // Close on escape key
        const escapeHandler = (e) => {
            if (e.key === 'Escape') {
                this.closeAnswerDrawer();
                document.removeEventListener('keydown', escapeHandler);
            }
        };
        document.addEventListener('keydown', escapeHandler);
        
        // Mark question as active
        questionBox.classList.add('sbqi-active');
    }
    
    /**
     * Close answer drawer
     */
    closeAnswerDrawer() {
        const overlay = document.getElementById('sbqi-drawer-overlay');
        if (overlay) {
            overlay.classList.remove('sbqi-drawer-visible');
            setTimeout(() => {
                if (overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 300);
        }
        
        // Remove active state from all questions
        document.querySelectorAll('.sbqi-question-box.sbqi-active').forEach(box => {
            box.classList.remove('sbqi-active');
        });
    }

    /**
     * Ensure CSS styles are loaded
     */
    ensureStyles() {
        if (document.getElementById('sbqi-styles')) {
            return;
        }

        const style = document.createElement('style');
        style.id = 'sbqi-styles';
        style.textContent = `
            .sbqi-question-container {
                margin: 20px 0;
                opacity: 0;
                transform: translateY(10px);
                transition: all 0.3s ease;
            }
            
            .sbqi-question-container.sbqi-visible {
                opacity: 1;
                transform: translateY(0);
            }
            
            .sbqi-question-box {
                background: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                padding: 15px;
                cursor: pointer;
                transition: all 0.2s ease;
                margin-bottom: 10px;
            }
            
            .sbqi-question-box:hover {
                background: #e9ecef;
                border-color: #007bff;
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(0,123,255,0.1);
            }
            
            .sbqi-question-box.sbqi-active {
                background: #007bff;
                color: white;
                border-color: #0056b3;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0,123,255,0.2);
            }
            
            .sbqi-question-text {
                font-weight: 600;
                font-size: 16px;
                line-height: 1.4;
            }
            
            .sbqi-question-text::before {
                content: "💭 ";
                margin-right: 8px;
            }
            
            /* Drawer Styles */
            .sbqi-drawer-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                z-index: 10000;
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
            }
            
            .sbqi-drawer-overlay.sbqi-drawer-visible {
                opacity: 1;
                visibility: visible;
            }
            
            .sbqi-drawer {
                position: absolute;
                right: 0;
                top: 0;
                width: 400px;
                max-width: 90vw;
                height: 100%;
                background: white;
                box-shadow: -2px 0 10px rgba(0, 0, 0, 0.1);
                transform: translateX(100%);
                transition: transform 0.3s ease;
                display: flex;
                flex-direction: column;
            }
            
            .sbqi-drawer-overlay.sbqi-drawer-visible .sbqi-drawer {
                transform: translateX(0);
            }
            
            .sbqi-drawer-header {
                padding: 20px;
                border-bottom: 1px solid #e9ecef;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: #f8f9fa;
            }
            
            .sbqi-drawer-title {
                margin: 0;
                font-size: 18px;
                color: #495057;
            }
            
            .sbqi-drawer-close {
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: #6c757d;
                padding: 0;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: all 0.2s ease;
            }
            
            .sbqi-drawer-close:hover {
                background: #e9ecef;
                color: #495057;
            }
            
            .sbqi-drawer-content {
                flex: 1;
                padding: 20px;
                overflow-y: auto;
            }
            
            .sbqi-drawer-question {
                margin-bottom: 25px;
                padding: 15px;
                background: #e3f2fd;
                border-radius: 8px;
                border-left: 4px solid #2196f3;
            }
            
            .sbqi-drawer-answer {
                margin-bottom: 25px;
                padding: 15px;
                background: #e8f5e8;
                border-radius: 8px;
                border-left: 4px solid #4caf50;
            }
            
            .sbqi-drawer-question strong,
            .sbqi-drawer-answer strong {
                display: block;
                margin-bottom: 8px;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .sbqi-drawer-metadata {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #e9ecef;
            }
            
            .sbqi-metadata-item {
                display: flex;
                justify-content: space-between;
                margin-bottom: 8px;
            }
            
            .sbqi-metadata-item:last-child {
                margin-bottom: 0;
            }
            
            .sbqi-metadata-label {
                font-weight: 600;
                color: #6c757d;
            }
            
            .sbqi-metadata-value {
                color: #495057;
            }
            
            /* Mobile responsiveness */
            @media (max-width: 768px) {
                .sbqi-drawer {
                    width: 100%;
                    max-width: 100%;
                }
            }
            
            /* Dark theme support */
            @media (prefers-color-scheme: dark) {
                .sbqi-question-box {
                    background: #343a40;
                    border-color: #495057;
                    color: #f8f9fa;
                }
                
                .sbqi-question-box:hover {
                    background: #495057;
                }
                
                .sbqi-drawer {
                    background: #212529;
                }
                
                .sbqi-drawer-header {
                    background: #343a40;
                    border-bottom-color: #495057;
                }
                
                .sbqi-drawer-title {
                    color: #f8f9fa;
                }
                
                .sbqi-drawer-close {
                    color: #adb5bd;
                }
                
                .sbqi-drawer-close:hover {
                    background: #495057;
                    color: #f8f9fa;
                }
                
                .sbqi-drawer-question {
                    background: #1a365d;
                    border-left-color: #3182ce;
                }
                
                .sbqi-drawer-answer {
                    background: #1a2e1a;
                    border-left-color: #38a169;
                }
                
                .sbqi-drawer-metadata {
                    background: #343a40;
                    border-color: #495057;
                }
                
                .sbqi-metadata-label {
                    color: #adb5bd;
                }
                
                .sbqi-metadata-value {
                    color: #f8f9fa;
                }
            }
        `;
        
        document.head.appendChild(style);
    }

    /**
     * Clean up injected questions
     */
    cleanup() {
        // Close any open drawer
        this.closeAnswerDrawer();
        
        // Remove injected elements
        this.injectedElements.forEach(element => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
        });
        this.injectedElements = [];
        this.isInjected = false;
        
        if (this.options.debugMode) {
            console.log('Cleaned up injected questions');
        }
    }

    /**
     * Destroy the injector
     */
    destroy() {
        this.cleanup();
        
        // Remove styles
        const styleElement = document.getElementById('sbqi-styles');
        if (styleElement) {
            styleElement.remove();
        }
    }

    /**
     * Utility function for delays
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// Make it globally available
window.SimpleBlogQuestionInjector = SimpleBlogQuestionInjector;

// Usage examples:
// SimpleBlogQuestionInjector.loadFromFile('questions.json');
// SimpleBlogQuestionInjector.loadFromData(questionsData);

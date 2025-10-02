/**
 * Blog Question Injector
 * 
 * A simple JavaScript module that takes a JSON file and automatically
 * injects questions into blog content with interactive answer drawers.
 * 
 * Usage:
 *   // From JSON file
 *   BlogQuestionInjector.loadFromFile('/path/to/questions.json');
 *   
 *   // From JSON data
 *   BlogQuestionInjector.loadFromData(questionData);
 * 
 * @version 1.0.0
 * @author Senior Software Engineer
 */

class BlogQuestionInjector {
    constructor(questionData, options = {}) {
        this.questionData = questionData;
        this.options = {
            theme: 'default',
            animationDuration: 300,
            drawerPosition: 'right',
            debugMode: false,
            ...options
        };
        
        this.injectedQuestions = new Map();
        this.currentDrawer = null;
        this.isInitialized = false;
        
        // Bind methods
        this.handleQuestionClick = this.handleQuestionClick.bind(this);
        this.closeDrawer = this.closeDrawer.bind(this);
        this.handleEscapeKey = this.handleEscapeKey.bind(this);
        
        this.log('BlogQuestionInjector initialized', this.questionData);
    }
    
    /**
     * Static method to load and initialize from JSON file
     */
    static async loadFromFile(jsonFilePath, options = {}) {
        try {
            const response = await fetch(jsonFilePath);
            if (!response.ok) {
                throw new Error(`Failed to load questions: ${response.status} ${response.statusText}`);
            }
            
            const questionData = await response.json();
            return await BlogQuestionInjector.loadFromData(questionData, options);
            
        } catch (error) {
            console.error('Failed to load question file:', error);
            throw error;
        }
    }
    
    /**
     * Static method to load and initialize from JSON data
     */
    static async loadFromData(questionData, options = {}) {
        try {
            const injector = new BlogQuestionInjector(questionData, options);
            await injector.initialize();
            return injector;
            
        } catch (error) {
            console.error('Failed to initialize from data:', error);
            throw error;
        }
    }
    
    /**
     * Initialize the question injector
     */
    async initialize() {
        if (this.isInitialized) {
            this.log('Already initialized');
            return;
        }
        
        try {
            // Validate question data
            this.validateQuestionData();
            
            // Inject CSS styles
            this.injectStyles();
            
            // Set up event listeners
            this.setupEventListeners();
            
            // Auto-inject all questions
            await this.injectAllQuestions();
            
            this.isInitialized = true;
            this.log('Initialization complete - injected questions automatically');
            
        } catch (error) {
            console.error('BlogQuestionInjector initialization failed:', error);
            throw error;
        }
    }
    
    /**
     * Validate the question data structure
     */
    validateQuestionData() {
        if (!this.questionData || !this.questionData.questions) {
            throw new Error('Invalid question data: missing questions array');
        }
        
        if (!Array.isArray(this.questionData.questions)) {
            throw new Error('Invalid question data: questions must be an array');
        }
        
        this.log('Question data validation passed');
    }
    
    /**
     * Inject all questions based on their placement strategies
     */
    async injectAllQuestions() {
        const { questions } = this.questionData;
        
        // Sort questions by priority (higher priority first)
        const sortedQuestions = questions.sort((a, b) => 
            (b.metadata?.priority || 5) - (a.metadata?.priority || 5)
        );
        
        let injectedCount = 0;
        
        for (const question of sortedQuestions) {
            try {
                const success = await this.injectQuestion(question);
                if (success) {
                    injectedCount++;
                }
            } catch (error) {
                console.warn('Failed to inject question:', question.id, error);
            }
        }
        
        this.log(`Injected ${injectedCount} out of ${questions.length} questions`);
    }
    
    /**
     * Inject a single question based on its placement strategy
     */
    async injectQuestion(question) {
        const { metadata } = question;
        if (!metadata) {
            this.log('Question missing metadata:', question.id);
            return false;
        }
        
        const strategy = metadata.placement_strategy;
        const targetParagraph = metadata.target_paragraph;
        
        let targetElement = null;
        
        switch (strategy) {
            case 'after_paragraph':
                targetElement = this.findParagraphElement(targetParagraph);
                if (targetElement) {
                    this.insertAfterElement(targetElement, question);
                }
                break;
                
            case 'before_section':
                targetElement = this.findSectionElement(targetParagraph);
                if (targetElement) {
                    this.insertBeforeElement(targetElement, question);
                }
                break;
                
            case 'inline_highlight':
                targetElement = this.findParagraphElement(targetParagraph);
                if (targetElement) {
                    this.insertInlineHighlight(targetElement, question);
                }
                break;
                
            case 'sidebar':
                this.insertSidebar(question);
                targetElement = true; // Sidebar doesn't need specific target
                break;
                
            case 'floating':
                this.insertFloating(question);
                targetElement = true; // Floating doesn't need specific target
                break;
                
            default:
                this.log('Unknown placement strategy:', strategy);
                return false;
        }
        
        if (targetElement) {
            this.injectedQuestions.set(question.id, question);
            this.log('Injected question:', question.id, strategy);
            return true;
        }
        
        return false;
    }
    
    /**
     * Find paragraph element based on paragraph reference
     */
    findParagraphElement(paragraphRef) {
        if (!paragraphRef) return null;
        
        const { paragraph_index, text_snippet } = paragraphRef;
        
        // Try to find by paragraph index first
        const paragraphs = document.querySelectorAll('p, div.paragraph, .content p, article p');
        
        if (paragraph_index < paragraphs.length) {
            const candidate = paragraphs[paragraph_index];
            
            // Verify with text snippet if available
            if (text_snippet) {
                const candidateText = candidate.textContent.trim();
                const snippetWords = text_snippet.split(' ').slice(0, 5).join(' ');
                
                if (candidateText.includes(snippetWords)) {
                    return candidate;
                }
            } else {
                return candidate;
            }
        }
        
        // Fallback: search by text snippet
        if (text_snippet) {
            const snippetWords = text_snippet.split(' ').slice(0, 5).join(' ');
            
            for (const paragraph of paragraphs) {
                if (paragraph.textContent.includes(snippetWords)) {
                    return paragraph;
                }
            }
        }
        
        this.log('Could not find paragraph element for:', paragraphRef);
        return null;
    }
    
    /**
     * Find section element (heading) based on paragraph reference
     */
    findSectionElement(paragraphRef) {
        if (!paragraphRef || !paragraphRef.section_title) return null;
        
        const sectionTitle = paragraphRef.section_title;
        const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
        
        for (const heading of headings) {
            if (heading.textContent.trim().includes(sectionTitle)) {
                return heading;
            }
        }
        
        return null;
    }
    
    /**
     * Insert question after an element
     */
    insertAfterElement(element, question) {
        const questionElement = this.createQuestionElement(question);
        element.parentNode.insertBefore(questionElement, element.nextSibling);
        
        // Apply animation
        this.animateQuestionAppearance(questionElement, question.metadata);
    }
    
    /**
     * Insert question before an element
     */
    insertBeforeElement(element, question) {
        const questionElement = this.createQuestionElement(question);
        element.parentNode.insertBefore(questionElement, element);
        
        // Apply animation
        this.animateQuestionAppearance(questionElement, question.metadata);
    }
    
    /**
     * Insert inline highlight within paragraph
     */
    insertInlineHighlight(element, question) {
        const highlightElement = this.createInlineHighlight(question);
        element.appendChild(highlightElement);
        
        // Apply animation
        this.animateQuestionAppearance(highlightElement, question.metadata);
    }
    
    /**
     * Insert sidebar question
     */
    insertSidebar(question) {
        let sidebar = document.getElementById('bqi-sidebar');
        
        if (!sidebar) {
            sidebar = this.createSidebar();
            document.body.appendChild(sidebar);
        }
        
        const questionElement = this.createSidebarQuestion(question);
        sidebar.appendChild(questionElement);
        
        // Apply animation
        this.animateQuestionAppearance(questionElement, question.metadata);
    }
    
    /**
     * Insert floating question
     */
    insertFloating(question) {
        const floatingElement = this.createFloatingQuestion(question);
        document.body.appendChild(floatingElement);
        
        // Apply animation
        this.animateQuestionAppearance(floatingElement, question.metadata);
    }
    
    /**
     * Create question element
     */
    createQuestionElement(question) {
        const element = document.createElement('div');
        element.className = `bqi-question bqi-theme-${this.options.theme}`;
        element.setAttribute('data-question-id', question.id);
        element.setAttribute('data-question-type', question.question_type);
        
        const confidence = question.confidence_score || 0.5;
        const confidenceClass = confidence > 0.8 ? 'high' : confidence > 0.5 ? 'medium' : 'low';
        
        element.innerHTML = `
            <div class="bqi-question-content">
                <div class="bqi-question-icon">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                        <path d="M5.255 5.786a.237.237 0 0 0 .241.247h.825c.138 0 .248-.113.266-.25.09-.656.54-1.134 1.342-1.134.686 0 1.314.343 1.314 1.168 0 .635-.374.927-.965 1.371-.673.489-1.206 1.06-1.168 1.987l.003.217a.25.25 0 0 0 .25.246h.811a.25.25 0 0 0 .25-.25v-.105c0-.718.273-.927 1.01-1.486.609-.463 1.244-.977 1.244-2.056 0-1.511-1.276-2.241-2.673-2.241-1.267 0-2.655.59-2.75 2.286zm1.557 5.763c0 .533.425.927 1.01.927.609 0 1.028-.394 1.028-.927 0-.552-.42-.94-1.029-.94-.584 0-1.009.388-1.009.94z"/>
                    </svg>
                </div>
                <div class="bqi-question-text">
                    <span class="bqi-question-label">Question:</span>
                    ${this.escapeHtml(question.question)}
                </div>
                <div class="bqi-question-meta">
                    <span class="bqi-confidence bqi-confidence-${confidenceClass}">
                        ${Math.round(confidence * 100)}% relevant
                    </span>
                    <span class="bqi-type">${question.question_type.replace('_', ' ')}</span>
                </div>
            </div>
        `;
        
        // Add click handler
        element.addEventListener('click', () => this.handleQuestionClick(question));
        
        return element;
    }
    
    /**
     * Create inline highlight element
     */
    createInlineHighlight(question) {
        const element = document.createElement('span');
        element.className = `bqi-inline-highlight bqi-theme-${this.options.theme}`;
        element.setAttribute('data-question-id', question.id);
        element.innerHTML = `
            <span class="bqi-highlight-icon">💡</span>
            <span class="bqi-highlight-text">Explore this concept</span>
        `;
        
        element.addEventListener('click', (e) => {
            e.stopPropagation();
            this.handleQuestionClick(question);
        });
        
        return element;
    }
    
    /**
     * Create sidebar container
     */
    createSidebar() {
        const sidebar = document.createElement('div');
        sidebar.id = 'bqi-sidebar';
        sidebar.className = `bqi-sidebar bqi-theme-${this.options.theme}`;
        sidebar.innerHTML = `
            <div class="bqi-sidebar-header">
                <h3>Explore Further</h3>
                <button class="bqi-sidebar-toggle" onclick="this.parentElement.parentElement.classList.toggle('collapsed')">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                        <path fill-rule="evenodd" d="M1.646 4.646a.5.5 0 0 1 .708 0L8 10.293l5.646-5.647a.5.5 0 0 1 .708.708l-6 6a.5.5 0 0 1-.708 0l-6-6a.5.5 0 0 1 0-.708z"/>
                    </svg>
                </button>
            </div>
            <div class="bqi-sidebar-content"></div>
        `;
        
        return sidebar;
    }
    
    /**
     * Create sidebar question element
     */
    createSidebarQuestion(question) {
        const element = document.createElement('div');
        element.className = 'bqi-sidebar-question';
        element.setAttribute('data-question-id', question.id);
        
        element.innerHTML = `
            <div class="bqi-sidebar-question-text">
                ${this.escapeHtml(question.question)}
            </div>
            <div class="bqi-sidebar-question-type">
                ${question.question_type.replace('_', ' ')}
            </div>
        `;
        
        element.addEventListener('click', () => this.handleQuestionClick(question));
        
        return element;
    }
    
    /**
     * Create floating question element
     */
    createFloatingQuestion(question) {
        const element = document.createElement('div');
        element.className = `bqi-floating-question bqi-theme-${this.options.theme}`;
        element.setAttribute('data-question-id', question.id);
        
        // Position randomly on the right side
        const topPosition = Math.random() * 60 + 20; // 20-80% from top
        element.style.top = `${topPosition}%`;
        
        element.innerHTML = `
            <div class="bqi-floating-content">
                <div class="bqi-floating-icon">?</div>
                <div class="bqi-floating-preview">
                    ${this.escapeHtml(question.question.substring(0, 50))}...
                </div>
            </div>
        `;
        
        element.addEventListener('click', () => this.handleQuestionClick(question));
        
        return element;
    }
    
    /**
     * Handle question click - open drawer with answer
     */
    handleQuestionClick(question) {
        this.log('Question clicked:', question.id);
        
        // Close existing drawer
        if (this.currentDrawer) {
            this.closeDrawer();
        }
        
        // Create and show new drawer
        this.currentDrawer = this.createDrawer(question);
        document.body.appendChild(this.currentDrawer);
        
        // Animate drawer appearance
        requestAnimationFrame(() => {
            this.currentDrawer.classList.add('open');
        });
        
        // Track interaction
        this.trackInteraction('question_clicked', question.id);
    }
    
    /**
     * Create drawer element
     */
    createDrawer(question) {
        const drawer = document.createElement('div');
        drawer.className = `bqi-drawer bqi-drawer-${this.options.drawerPosition} bqi-theme-${this.options.theme}`;
        drawer.setAttribute('data-question-id', question.id);
        
        const confidence = question.confidence_score || 0.5;
        const confidenceClass = confidence > 0.8 ? 'high' : confidence > 0.5 ? 'medium' : 'low';
        
        drawer.innerHTML = `
            <div class="bqi-drawer-overlay"></div>
            <div class="bqi-drawer-content">
                <div class="bqi-drawer-header">
                    <div class="bqi-drawer-title">
                        <span class="bqi-drawer-icon">💡</span>
                        Explore This Concept
                    </div>
                    <button class="bqi-drawer-close" aria-label="Close">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                        </svg>
                    </button>
                </div>
                
                <div class="bqi-drawer-body">
                    <div class="bqi-question-section">
                        <h3 class="bqi-section-title">Question</h3>
                        <div class="bqi-question-display">
                            ${this.escapeHtml(question.question)}
                        </div>
                        <div class="bqi-question-metadata">
                            <span class="bqi-question-type-badge">${question.question_type.replace('_', ' ')}</span>
                            <span class="bqi-confidence-badge bqi-confidence-${confidenceClass}">
                                ${Math.round(confidence * 100)}% relevant
                            </span>
                        </div>
                    </div>
                    
                    <div class="bqi-answer-section">
                        <h3 class="bqi-section-title">Detailed Answer</h3>
                        <div class="bqi-answer-content">
                            ${this.formatAnswer(question.answer)}
                        </div>
                    </div>
                    
                    ${question.context ? `
                        <div class="bqi-context-section">
                            <h3 class="bqi-section-title">Context</h3>
                            <div class="bqi-context-content">
                                "${this.escapeHtml(question.context)}"
                            </div>
                        </div>
                    ` : ''}
                </div>
                
                <div class="bqi-drawer-footer">
                    <div class="bqi-drawer-actions">
                        <button class="bqi-action-button bqi-secondary" onclick="window.open('https://www.google.com/search?q=${encodeURIComponent(question.question)}', '_blank')">
                            Search More
                        </button>
                        <button class="bqi-action-button bqi-primary" onclick="this.closest('.bqi-drawer').querySelector('.bqi-drawer-close').click()">
                            Got It!
                        </button>
                    </div>
                    <div class="bqi-drawer-attribution">
                        Generated by Blog Question AI
                    </div>
                </div>
            </div>
        `;
        
        // Add event listeners
        const overlay = drawer.querySelector('.bqi-drawer-overlay');
        const closeButton = drawer.querySelector('.bqi-drawer-close');
        
        overlay.addEventListener('click', this.closeDrawer);
        closeButton.addEventListener('click', this.closeDrawer);
        
        return drawer;
    }
    
    /**
     * Close the current drawer
     */
    closeDrawer() {
        if (!this.currentDrawer) return;
        
        this.currentDrawer.classList.remove('open');
        
        setTimeout(() => {
            if (this.currentDrawer && this.currentDrawer.parentNode) {
                this.currentDrawer.parentNode.removeChild(this.currentDrawer);
            }
            this.currentDrawer = null;
        }, this.options.animationDuration);
        
        this.trackInteraction('drawer_closed');
    }
    
    /**
     * Animate question appearance based on metadata
     */
    animateQuestionAppearance(element, metadata) {
        const animation = metadata?.animation || 'fade_in';
        const triggerEvent = metadata?.trigger_event || 'immediate';
        
        // Set initial state
        element.style.opacity = '0';
        element.style.transform = this.getInitialTransform(animation);
        
        const animate = () => {
            element.style.transition = `all ${this.options.animationDuration}ms ease-out`;
            element.style.opacity = '1';
            element.style.transform = 'none';
        };
        
        // Apply trigger event
        switch (triggerEvent) {
            case 'scroll':
                this.setupScrollTrigger(element, animate);
                break;
            case 'hover':
                this.setupHoverTrigger(element, animate);
                break;
            case 'click':
                this.setupClickTrigger(element, animate);
                break;
            case 'time':
                setTimeout(animate, 2000); // 2 second delay
                break;
            default:
                requestAnimationFrame(animate);
        }
    }
    
    /**
     * Get initial transform for animation
     */
    getInitialTransform(animation) {
        switch (animation) {
            case 'slide_up':
                return 'translateY(20px)';
            case 'slide_down':
                return 'translateY(-20px)';
            case 'slide_left':
                return 'translateX(20px)';
            case 'slide_right':
                return 'translateX(-20px)';
            case 'bounce':
                return 'scale(0.8)';
            case 'fade_in':
            default:
                return 'scale(0.95)';
        }
    }
    
    /**
     * Setup scroll trigger for animation
     */
    setupScrollTrigger(element, callback) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    callback();
                    observer.unobserve(element);
                }
            });
        }, { threshold: 0.1 });
        
        observer.observe(element);
    }
    
    /**
     * Setup hover trigger for animation
     */
    setupHoverTrigger(element, callback) {
        const parent = element.parentElement;
        if (parent) {
            parent.addEventListener('mouseenter', callback, { once: true });
        }
    }
    
    /**
     * Setup click trigger for animation
     */
    setupClickTrigger(element, callback) {
        const parent = element.parentElement;
        if (parent) {
            parent.addEventListener('click', callback, { once: true });
        }
    }
    
    /**
     * Setup global event listeners
     */
    setupEventListeners() {
        // Escape key to close drawer
        document.addEventListener('keydown', this.handleEscapeKey);
        
        // Resize handler for responsive adjustments
        window.addEventListener('resize', this.handleResize.bind(this));
    }
    
    /**
     * Handle escape key press
     */
    handleEscapeKey(event) {
        if (event.key === 'Escape' && this.currentDrawer) {
            this.closeDrawer();
        }
    }
    
    /**
     * Handle window resize
     */
    handleResize() {
        // Adjust floating questions positions if needed
        const floatingQuestions = document.querySelectorAll('.bqi-floating-question');
        floatingQuestions.forEach(element => {
            // Recalculate position if needed
        });
    }
    
    /**
     * Format answer text with basic markdown support
     */
    formatAnswer(answer) {
        if (!answer) return '';
        
        return answer
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^(.*)$/, '<p>$1</p>');
    }
    
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Track user interactions for analytics
     */
    trackInteraction(event, questionId = null) {
        if (this.options.debugMode) {
            console.log('BQI Interaction:', event, questionId);
        }
        
        // Send to analytics if configured
        if (window.gtag) {
            window.gtag('event', event, {
                custom_parameter_1: questionId,
                custom_parameter_2: this.questionData.content_id
            });
        }
    }
    
    /**
     * Inject CSS styles
     */
    injectStyles() {
        if (document.getElementById('bqi-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'bqi-styles';
        style.textContent = this.getCSS();
        document.head.appendChild(style);
    }
    
    /**
     * Get CSS styles for the question injector
     */
    getCSS() {
        return `
            /* Blog Question Injector Styles */
            .bqi-question {
                margin: 20px 0;
                padding: 16px;
                background: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.2s ease;
                position: relative;
            }
            
            .bqi-question:hover {
                background: #e3f2fd;
                border-color: #2196f3;
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(33, 150, 243, 0.15);
            }
            
            .bqi-question-content {
                display: flex;
                align-items: flex-start;
                gap: 12px;
            }
            
            .bqi-question-icon {
                flex-shrink: 0;
                width: 24px;
                height: 24px;
                color: #2196f3;
                margin-top: 2px;
            }
            
            .bqi-question-text {
                flex: 1;
                font-size: 16px;
                line-height: 1.5;
                color: #333;
            }
            
            .bqi-question-label {
                font-weight: 600;
                color: #2196f3;
                margin-right: 8px;
            }
            
            .bqi-question-meta {
                display: flex;
                gap: 12px;
                margin-top: 8px;
                font-size: 12px;
            }
            
            .bqi-confidence {
                padding: 2px 6px;
                border-radius: 4px;
                font-weight: 500;
            }
            
            .bqi-confidence-high { background: #e8f5e8; color: #2e7d32; }
            .bqi-confidence-medium { background: #fff3e0; color: #f57c00; }
            .bqi-confidence-low { background: #ffebee; color: #c62828; }
            
            .bqi-type {
                padding: 2px 6px;
                background: #e3f2fd;
                color: #1976d2;
                border-radius: 4px;
                text-transform: capitalize;
            }
            
            /* Inline Highlight */
            .bqi-inline-highlight {
                display: inline-block;
                margin: 0 4px;
                padding: 4px 8px;
                background: #fff3e0;
                border: 1px solid #ffb74d;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.2s ease;
            }
            
            .bqi-inline-highlight:hover {
                background: #ffe0b2;
                transform: scale(1.05);
            }
            
            .bqi-highlight-icon {
                margin-right: 4px;
            }
            
            /* Sidebar */
            .bqi-sidebar {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 300px;
                max-height: 80vh;
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
                z-index: 1000;
                overflow: hidden;
                transition: all 0.3s ease;
            }
            
            .bqi-sidebar.collapsed {
                height: 60px;
            }
            
            .bqi-sidebar-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 16px;
                background: #f5f5f5;
                border-bottom: 1px solid #e0e0e0;
            }
            
            .bqi-sidebar-header h3 {
                margin: 0;
                font-size: 16px;
                color: #333;
            }
            
            .bqi-sidebar-toggle {
                background: none;
                border: none;
                cursor: pointer;
                padding: 4px;
                border-radius: 4px;
                transition: background 0.2s ease;
            }
            
            .bqi-sidebar-toggle:hover {
                background: #e0e0e0;
            }
            
            .bqi-sidebar-content {
                max-height: calc(80vh - 60px);
                overflow-y: auto;
            }
            
            .bqi-sidebar-question {
                padding: 12px 16px;
                border-bottom: 1px solid #f0f0f0;
                cursor: pointer;
                transition: background 0.2s ease;
            }
            
            .bqi-sidebar-question:hover {
                background: #f8f9fa;
            }
            
            .bqi-sidebar-question-text {
                font-size: 14px;
                line-height: 1.4;
                color: #333;
                margin-bottom: 4px;
            }
            
            .bqi-sidebar-question-type {
                font-size: 12px;
                color: #666;
                text-transform: capitalize;
            }
            
            /* Floating Questions */
            .bqi-floating-question {
                position: fixed;
                right: 20px;
                width: 60px;
                height: 60px;
                background: #2196f3;
                border-radius: 50%;
                cursor: pointer;
                z-index: 999;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 12px rgba(33, 150, 243, 0.3);
            }
            
            .bqi-floating-question:hover {
                transform: scale(1.1);
                box-shadow: 0 6px 20px rgba(33, 150, 243, 0.4);
            }
            
            .bqi-floating-content {
                text-align: center;
                color: white;
            }
            
            .bqi-floating-icon {
                font-size: 24px;
                font-weight: bold;
            }
            
            .bqi-floating-preview {
                display: none;
                position: absolute;
                right: 70px;
                top: 50%;
                transform: translateY(-50%);
                background: #333;
                color: white;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 12px;
                white-space: nowrap;
                max-width: 200px;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            
            .bqi-floating-question:hover .bqi-floating-preview {
                display: block;
            }
            
            /* Drawer */
            .bqi-drawer {
                position: fixed;
                top: 0;
                right: 0;
                width: 100%;
                height: 100%;
                z-index: 10000;
                pointer-events: none;
                transition: all 0.3s ease;
            }
            
            .bqi-drawer.open {
                pointer-events: all;
            }
            
            .bqi-drawer-overlay {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0);
                transition: background 0.3s ease;
            }
            
            .bqi-drawer.open .bqi-drawer-overlay {
                background: rgba(0, 0, 0, 0.5);
            }
            
            .bqi-drawer-content {
                position: absolute;
                top: 0;
                right: 0;
                width: 100%;
                max-width: 500px;
                height: 100%;
                background: white;
                transform: translateX(100%);
                transition: transform 0.3s ease;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }
            
            .bqi-drawer.open .bqi-drawer-content {
                transform: translateX(0);
            }
            
            .bqi-drawer-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px;
                border-bottom: 1px solid #e0e0e0;
                background: #f8f9fa;
            }
            
            .bqi-drawer-title {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 18px;
                font-weight: 600;
                color: #333;
            }
            
            .bqi-drawer-close {
                background: none;
                border: none;
                cursor: pointer;
                padding: 8px;
                border-radius: 4px;
                transition: background 0.2s ease;
            }
            
            .bqi-drawer-close:hover {
                background: #e0e0e0;
            }
            
            .bqi-drawer-body {
                flex: 1;
                overflow-y: auto;
                padding: 20px;
            }
            
            .bqi-section-title {
                margin: 0 0 12px 0;
                font-size: 16px;
                font-weight: 600;
                color: #333;
            }
            
            .bqi-question-section,
            .bqi-answer-section,
            .bqi-context-section {
                margin-bottom: 24px;
            }
            
            .bqi-question-display {
                font-size: 18px;
                line-height: 1.5;
                color: #333;
                margin-bottom: 12px;
                padding: 16px;
                background: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #2196f3;
            }
            
            .bqi-question-metadata {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }
            
            .bqi-question-type-badge,
            .bqi-confidence-badge {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
                text-transform: capitalize;
            }
            
            .bqi-question-type-badge {
                background: #e3f2fd;
                color: #1976d2;
            }
            
            .bqi-answer-content {
                font-size: 16px;
                line-height: 1.6;
                color: #333;
            }
            
            .bqi-answer-content p {
                margin: 0 0 16px 0;
            }
            
            .bqi-answer-content p:last-child {
                margin-bottom: 0;
            }
            
            .bqi-context-content {
                font-style: italic;
                color: #666;
                padding: 12px;
                background: #f5f5f5;
                border-radius: 4px;
            }
            
            .bqi-drawer-footer {
                padding: 20px;
                border-top: 1px solid #e0e0e0;
                background: #f8f9fa;
            }
            
            .bqi-drawer-actions {
                display: flex;
                gap: 12px;
                margin-bottom: 12px;
            }
            
            .bqi-action-button {
                padding: 10px 16px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: all 0.2s ease;
                flex: 1;
            }
            
            .bqi-action-button.bqi-primary {
                background: #2196f3;
                color: white;
            }
            
            .bqi-action-button.bqi-primary:hover {
                background: #1976d2;
            }
            
            .bqi-action-button.bqi-secondary {
                background: #e0e0e0;
                color: #333;
            }
            
            .bqi-action-button.bqi-secondary:hover {
                background: #d0d0d0;
            }
            
            .bqi-drawer-attribution {
                text-align: center;
                font-size: 12px;
                color: #666;
            }
            
            /* Responsive Design */
            @media (max-width: 768px) {
                .bqi-sidebar {
                    width: 280px;
                    right: 10px;
                }
                
                .bqi-drawer-content {
                    max-width: 100%;
                }
                
                .bqi-floating-question {
                    width: 50px;
                    height: 50px;
                    right: 15px;
                }
                
                .bqi-floating-icon {
                    font-size: 20px;
                }
            }
            
            /* Theme Variations */
            .bqi-theme-dark .bqi-question {
                background: #2d2d2d;
                border-color: #404040;
                color: #e0e0e0;
            }
            
            .bqi-theme-dark .bqi-question:hover {
                background: #3d3d3d;
                border-color: #2196f3;
            }
            
            .bqi-theme-minimal .bqi-question {
                background: transparent;
                border: 1px dashed #ccc;
                padding: 12px;
            }
            
            .bqi-theme-minimal .bqi-question:hover {
                border-style: solid;
                border-color: #2196f3;
            }
        `;
    }
    
    /**
     * Debug logging
     */
    log(...args) {
        if (this.options.debugMode) {
            console.log('[BlogQuestionInjector]', ...args);
        }
    }
    
    /**
     * Public API methods
     */
    
    /**
     * Manually inject a specific question
     */
    async injectSpecificQuestion(questionId) {
        const question = this.questionData.questions.find(q => q.id === questionId);
        if (question) {
            return await this.injectQuestion(question);
        }
        return false;
    }
    
    /**
     * Remove all injected questions
     */
    removeAllQuestions() {
        document.querySelectorAll('[data-question-id]').forEach(element => {
            element.remove();
        });
        
        const sidebar = document.getElementById('bqi-sidebar');
        if (sidebar) {
            sidebar.remove();
        }
        
        this.injectedQuestions.clear();
        this.log('All questions removed');
    }
    
    /**
     * Get statistics about injected questions
     */
    getStatistics() {
        return {
            totalQuestions: this.questionData.questions.length,
            injectedQuestions: this.injectedQuestions.size,
            averageConfidence: this.questionData.average_confidence,
            contentTopic: this.questionData.content_context?.topic,
            placementStrategies: [...new Set(this.questionData.questions.map(q => q.metadata?.placement_strategy))]
        };
    }
    
    /**
     * Destroy the injector and clean up
     */
    destroy() {
        this.removeAllQuestions();
        
        if (this.currentDrawer) {
            this.closeDrawer();
        }
        
        const styles = document.getElementById('bqi-styles');
        if (styles) {
            styles.remove();
        }
        
        document.removeEventListener('keydown', this.handleEscapeKey);
        window.removeEventListener('resize', this.handleResize);
        
        this.isInitialized = false;
        this.log('BlogQuestionInjector destroyed');
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BlogQuestionInjector;
}

// Global registration
window.BlogQuestionInjector = BlogQuestionInjector;

/**
 * SIMPLE USAGE EXAMPLES
 * 
 * 1. Load from JSON file (most common use case):
 *    BlogQuestionInjector.loadFromFile('/generated_questions/my_blog_post_questions.json');
 * 
 * 2. Load from JSON data:
 *    BlogQuestionInjector.loadFromData(questionData);
 * 
 * 3. With options:
 *    BlogQuestionInjector.loadFromFile('/path/to/questions.json', { theme: 'dark' });
 * 
 * That's it! The module will automatically:
 * - Read the placement strategies from the JSON
 * - Inject questions in the right places
 * - Set up click handlers for the drawer
 * - Handle all animations and interactions
 */

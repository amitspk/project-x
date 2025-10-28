/**
 * Auto Blog Question Injector
 * 
 * Automatically detects blog URLs, calls the Blog Manager API, and injects questions
 * into blog content with interactive answer drawers.
 * 
 * Features:
 * - Auto-detects current page URL and calls Blog Manager API
 * - Adapts to new API response format from /api/v1/blogs/by-url
 * - Intelligent paragraph detection and question placement
 * - Interactive answer drawers with rich metadata
 * - Responsive design with mobile support
 * - Error handling and fallback mechanisms
 * - Secure API key authentication
 * 
 * Usage:
 *   // REQUIRED: Set your API key first (get it from your admin)
 *   AutoBlogQuestionInjector.autoInit({
 *     apiKey: 'pub_YOUR_API_KEY_HERE'  // ← Your unique API key
 *   });
 *   
 *   // Or with manual initialization
 *   const injector = new AutoBlogQuestionInjector({
 *     apiKey: 'pub_YOUR_API_KEY_HERE'
 *   });
 *   injector.init('https://example.com/blog-post');
 * 
 * @version 2.1.0
 * @author Senior Software Engineer
 */

class AutoBlogQuestionInjector {
    constructor(options = {}) {
        console.log('[AutoBlogQuestionInjector] VERSION: 2025-10-14-FIX loaded');
        this.options = {
            // API Configuration
            apiBaseUrl: 'http://localhost:8005/api/v1',
            apiKey: null,  // REQUIRED: Publisher's API key
            apiTimeout: 10000,
            
            // UI Configuration
            theme: 'default',
            questionsPerParagraph: 2,
            animationDelay: 150,
            debugMode: true,  // Enable for debugging
            
            // Auto-detection settings
            autoDetectUrl: true,
            
            // Placement settings
            placementStrategy: 'after_paragraphs',
            minParagraphLength: 100,
            
            // Question ordering
            randomizeOrder: true,  // New option: randomize question order
            
            ...options
        };
        
        // Validate API key
        if (!this.options.apiKey) {
            console.error('[AutoBlogQuestionInjector] ⚠️ WARNING: API key not provided! Get your API key from your account dashboard.');
            console.error('[AutoBlogQuestionInjector] Usage: AutoBlogQuestionInjector.autoInit({ apiKey: "pub_YOUR_KEY" })');
        }
        
        this.questions = [];
        this.blogInfo = null;
        this.injectedElements = [];
        this.isInitialized = false;
        this.currentDrawer = null;
        
        // Bind methods
        this.handleQuestionClick = this.handleQuestionClick.bind(this);
        this.closeDrawer = this.closeDrawer.bind(this);
        this.handleEscapeKey = this.handleEscapeKey.bind(this);
        
        this.log('AutoBlogQuestionInjector initialized');
    }
    
    /**
     * Static method for auto-initialization
     */
    static async autoInit(options = {}) {
        console.log('[AutoBlogQuestionInjector] autoInit() called');
        try {
            // Prevent multiple initializations - check for existing instance OR in-progress initialization
            if (window._autoInjectorInstance) {
                console.log('[AutoBlogQuestionInjector] Instance already exists, returning existing one');
                return window._autoInjectorInstance;
            }
            
            // Check if initialization is already in progress
            if (window._autoInitInProgress) {
                console.log('[AutoBlogQuestionInjector] Initialization already in progress, waiting...');
                // Wait for the in-progress initialization to complete
                while (window._autoInitInProgress && !window._autoInjectorInstance) {
                    await new Promise(resolve => setTimeout(resolve, 100));
                }
                return window._autoInjectorInstance;
            }
            
            // Mark initialization as in progress
            window._autoInitInProgress = true;
            
            // Also clean up any orphaned question elements and headers
            document.querySelectorAll('.abqi-question-container, .abqi-question-box, .abqi-drawer-overlay, .abqi-section-header, .abqi-answer-drawer').forEach(el => el.remove());
            
            console.log('[AutoBlogQuestionInjector] Creating NEW instance');
            const injector = new AutoBlogQuestionInjector(options);
            
            // Store global instance immediately to prevent race condition
            window._autoInjectorInstance = injector;
            
            // Wait for DOM to be ready
            if (document.readyState === 'loading') {
                console.log('[AutoBlogQuestionInjector] ⏰ Waiting for DOMContentLoaded...');
                await new Promise(resolve => {
                    document.addEventListener('DOMContentLoaded', resolve);
                });
                console.log('[AutoBlogQuestionInjector] ✅ DOM ready!');
            } else {
                console.log('[AutoBlogQuestionInjector] ✅ DOM already ready, state:', document.readyState);
            }
            
            console.log('[AutoBlogQuestionInjector] 🚀 ABOUT TO CALL autoDetectAndInit()');
            // Auto-detect and initialize
            await injector.autoDetectAndInit();
            console.log('[AutoBlogQuestionInjector] ✅ autoDetectAndInit() completed');
            
            // Mark initialization as complete
            window._autoInitInProgress = false;
            
            return injector;
            
        } catch (error) {
            console.error('AutoBlogQuestionInjector auto-initialization failed:', error);
            window._autoInitInProgress = false;
            window._autoInjectorInstance = null;
            return null;
        }
    }
    
    /**
     * Static method for manual initialization
     */
    static async init(blogUrl, options = {}) {
        console.log('[AutoBlogQuestionInjector] init() called with URL:', blogUrl);
        try {
            console.log('[AutoBlogQuestionInjector] Creating NEW instance in init()');
            const injector = new AutoBlogQuestionInjector(options);
            await injector.initialize(blogUrl);
            return injector;
            
        } catch (error) {
            console.error('AutoBlogQuestionInjector initialization failed:', error);
            return null;
        }
    }
    
    /**
     * Auto-detect current page and initialize - attempts to fetch questions for any URL
     * The backend will validate if the publisher is onboarded
     */
    async autoDetectAndInit() {
        const currentUrl = window.location.href;
        
        console.log('[AutoBlogQuestionInjector] 🔍 Auto-detecting blog URL:', currentUrl);
        console.log('[AutoBlogQuestionInjector] 🚀 Attempting to fetch questions (backend will validate publisher)...');
        
        try {
            await this.initialize(currentUrl);
        } catch (error) {
            console.log('[AutoBlogQuestionInjector] ℹ️ No questions available for this URL:', error.message);
            // Don't inject anything - keep blog untouched
            // This is expected for non-onboarded publishers or pages without questions
        }
    }
    
    /**
     * Initialize with a specific blog URL
     */
    async initialize(blogUrl) {
        if (this.isInitialized) {
            console.log('[AutoBlogQuestionInjector] ⚠️ Already initialized');
            return;
        }
        
        console.log('[AutoBlogQuestionInjector] 🎯 Starting initialize() with URL:', blogUrl);
        
        try {
            // FORCE cleanup of ALL question elements before initialization
            console.log('[AutoBlogQuestionInjector] 🧹 Force cleaning DOM before initialization...');
            const selectorsToClean = [
                '.abqi-question-container',
                '.abqi-question-box', 
                '.abqi-drawer-overlay',
                '.abqi-section-header',
                '.abqi-answer-drawer'
            ];
            
            let cleanedCount = 0;
            selectorsToClean.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    if (el.parentNode) {
                        el.parentNode.removeChild(el);
                        cleanedCount++;
                    }
                });
            });
            
            if (cleanedCount > 0) {
                console.log(`[AutoBlogQuestionInjector] 🧹 Cleaned up ${cleanedCount} orphaned elements`);
            }
            
            console.log('[AutoBlogQuestionInjector] 📡 Fetching questions from API...');
            
            // Fetch questions from API
            const apiData = await this.fetchQuestionsFromAPI(blogUrl);
            
            console.log('[AutoBlogQuestionInjector] 📦 API response:', apiData);
            
            if (!apiData || !apiData.success) {
                throw new Error('Failed to fetch questions from API');
            }
            
            // Check if we actually have questions
            if (!apiData.questions || apiData.questions.length === 0) {
                throw new Error('No questions available for this blog');
            }
            
            // Store data
            this.questions = apiData.questions || [];
            this.blogInfo = apiData.blog_info || {};
            
            // Note: Randomization is now handled server-side via API parameter
            // No need for client-side shuffling
            
            console.log(`[AutoBlogQuestionInjector] ✅ Loaded ${this.questions.length} questions for blog:`, this.blogInfo.title);
            
            // Set up UI
            console.log('[AutoBlogQuestionInjector] 🎨 Injecting styles...');
            this.injectStyles();
            console.log('[AutoBlogQuestionInjector] 🔧 Setting up event listeners...');
            this.setupEventListeners();
            
            // Inject questions
            console.log('[AutoBlogQuestionInjector] 💉 Injecting questions into DOM...');
            await this.injectAllQuestions();
            
            this.isInitialized = true;
            console.log('[AutoBlogQuestionInjector] 🎉 Initialization complete!');
            
        } catch (error) {
            console.log('[AutoBlogQuestionInjector] ❌ Initialization failed, keeping blog untouched:', error.message);
            throw error;
        }
    }
    
    /**
     * Fetch questions from the Blog Manager API
     */
    async fetchQuestionsFromAPI(blogUrl) {
        // Updated for Content Processing Service (2-service architecture)
        // Support server-side randomization via API parameter
        const randomizeParam = this.options.randomizeOrder ? '&randomize=true' : '';
        const apiUrl = `${this.options.apiBaseUrl}/questions/by-url?blog_url=${encodeURIComponent(blogUrl)}${randomizeParam}`;
        
        this.log('Fetching questions from API:', apiUrl);
        
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), this.options.apiTimeout);
            
            // Build headers with API key
            const headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            };
            
            // Add API key if provided
            if (this.options.apiKey) {
                headers['X-API-Key'] = this.options.apiKey;
            } else {
                console.warn('[AutoBlogQuestionInjector] ⚠️ No API key provided - request may fail');
            }
            
            const response = await fetch(apiUrl, {
                method: 'GET',
                headers: headers,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (!response.ok) {
                throw new Error(`API request failed: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            this.log('API response received:', data);
            
            return data;
            
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('API request timed out');
            }
            throw error;
        }
    }
    
    /**
     * Analyze page layout to adapt question placement
     */
    analyzePageLayout() {
        // Find the main content container
        const contentSelectors = [
            '[itemprop="articleBody"]',
            '.storyDetails', '.detail',
            'article', 'main',
            '.content', '.post-content', '.article-content'
        ];
        
        let contentContainer = null;
        for (const selector of contentSelectors) {
            contentContainer = document.querySelector(selector);
            if (contentContainer) {
                this.log(`Found content container: ${selector}`);
                break;
            }
        }
        
        if (!contentContainer) {
            contentContainer = document.body;
        }
        
        // Get layout metrics
        const containerStyles = getComputedStyle(contentContainer);
        const contentWidth = contentContainer.offsetWidth;
        const containerPadding = parseInt(containerStyles.paddingLeft) + parseInt(containerStyles.paddingRight);
        const effectiveWidth = contentWidth - containerPadding;
        
        return {
            container: contentContainer,
            width: effectiveWidth,
            fontSize: parseInt(containerStyles.fontSize),
            lineHeight: containerStyles.lineHeight,
            color: containerStyles.color,
            backgroundColor: containerStyles.backgroundColor,
            // Determine optimal card width based on content width
            cardWidth: effectiveWidth > 1000 ? '32%' : effectiveWidth > 600 ? '48%' : '100%',
            cardsPerRow: effectiveWidth > 1000 ? 3 : effectiveWidth > 600 ? 2 : 1,
            shouldUseFullWidth: effectiveWidth < 600
        };
    }
    
    /**
     * Inject all questions into the page with adaptive layout
     */
    async injectAllQuestions() {
        if (this.questions.length === 0) {
            this.log('No questions to inject');
            return;
        }

        const paragraphs = this.findMainParagraphs();
        if (paragraphs.length === 0) {
            this.log('No suitable paragraphs found for question injection');
            return;
        }

        // Analyze page layout
        const layout = this.analyzePageLayout();
        this.log(`Layout analysis: ${layout.width}px wide, ${layout.cardsPerRow} cards per row`);
        
        const questionsPerGroup = 3;
        const numGroups = Math.ceil(this.questions.length / questionsPerGroup);
        
        // Smart distribution: Place groups evenly throughout content
        // Skip first 2 paragraphs (intro) and last 1 paragraph (outro)
        const usableParagraphs = paragraphs.slice(2, -1);
        if (usableParagraphs.length === 0) {
            this.log('Not enough paragraphs for smart placement');
            return;
        }
        
        const paragraphInterval = Math.max(3, Math.floor(usableParagraphs.length / (numGroups + 1)));

        let questionIndex = 0;
        let isFirstGroup = true;
        const figmaColors = [
          '#FEF4E3','#F9F6FE','#FEE3E3','#E4F8FA','#F4FAE3','#E7E5F9','#FFE1EB',
          '#E4FAFE','#FAF3E3','#E3E7FA','#E3F5FA','#F8FAF5','#F6F7FC'
        ];

        for (let groupIdx = 0; groupIdx < numGroups && questionIndex < this.questions.length; groupIdx++) {
            const paragraphIndex = Math.min((groupIdx + 1) * paragraphInterval, usableParagraphs.length - 1);
            const insertionParagraph = usableParagraphs[paragraphIndex];

            if (!insertionParagraph || !insertionParagraph.parentNode) {
                this.log('❌ Invalid insertion paragraph, skipping group');
                break;
            }

            // Insert section header only for the first group
            let insertionPoint = insertionParagraph.nextSibling;
            if (isFirstGroup) {
                const headerElement = document.createElement('div');
                headerElement.className = 'abqi-section-header';
                headerElement.innerHTML = 'Some Questions in Mind?';
                headerElement.style.maxWidth = layout.width + 'px';
                headerElement.style.margin = '48px auto 24px auto';
                insertionParagraph.parentNode.insertBefore(headerElement, insertionPoint);
                this.injectedElements.push(headerElement);
                insertionPoint = headerElement.nextSibling;
                isFirstGroup = false;
            }

            // Create adaptive grid container
            const gridContainer = document.createElement('div');
            gridContainer.className = 'abqi-questions-grid';
            gridContainer.style.maxWidth = layout.width + 'px';
            gridContainer.style.margin = '32px auto';
            gridContainer.style.display = 'grid';
            gridContainer.style.gridTemplateColumns = layout.shouldUseFullWidth 
                ? '1fr' 
                : `repeat(auto-fit, minmax(${layout.cardsPerRow === 3 ? '280px' : '320px'}, 1fr))`;
            gridContainer.style.gap = '20px';
            gridContainer.style.padding = '0 16px';

            // Add question cards to this group
            const questionsInThisGroup = Math.min(questionsPerGroup, this.questions.length - questionIndex);
            for (let j = 0; j < questionsInThisGroup; j++) {
                const question = this.questions[questionIndex];
                const pastelColor = figmaColors[questionIndex % figmaColors.length];
                
                const figmaCard = document.createElement('div');
                figmaCard.className = 'figma-question-card';
                figmaCard.style.background = pastelColor;
                figmaCard.innerHTML = `
                <div class="figma-qcard-content">
                    <div class="figma-qcard-question">${this.formatFigmaQuestion(question.question)}</div>
                </div>
                <div class="figma-qcard-footer">
                  <span class="figma-qcard-explore">EXPLORE</span>
                  <span class="figma-qcard-arrow">
                    <svg width="32" height="20" viewBox="0 0 32 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                      <linearGradient id="figma-arrow-gradient-${questionIndex}" x1="0" y1="10" x2="32" y2="10" gradientUnits="userSpaceOnUse">
                        <stop stop-color="#903FC0"/>
                        <stop offset="0.32" stop-color="#FF66B2"/>
                        <stop offset="0.65" stop-color="#FF7556"/>
                        <stop offset="1" stop-color="#FFD257"/>
                      </linearGradient>
                    </defs>
                    <path d="M5 10H27" stroke="url(#figma-arrow-gradient-${questionIndex})" stroke-width="2.4" stroke-linecap="round"/>
                    <path d="M23.25 6.5L27 10L23.25 13.5" stroke="url(#figma-arrow-gradient-${questionIndex})" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </span>
                </div>
                `;
                figmaCard.style.cursor = 'pointer';
                figmaCard.addEventListener('click', () => this.handleQuestionClick(question));
                gridContainer.appendChild(figmaCard);
                questionIndex++;
            }
            
            // Insert the grid after the paragraph
            insertionParagraph.parentNode.insertBefore(gridContainer, insertionPoint);
            this.injectedElements.push(gridContainer);
        }
        
        this.log(`✅ Injected ${questionIndex} questions in ${numGroups} groups (adaptive layout)`);
    }
    
    
    /**
     * Find main content paragraphs on the page
     */
    findMainParagraphs() {
        // Comprehensive selectors for different blog platforms
        const contentSelectors = [
            // Hindustan Times
            '.storyDetails p, .detail p, [itemprop="articleBody"] p, .storyPara p',
            // Medium
            'article p, .postArticle-content p, .section-content p',
            // Dev.to
            '.crayons-article__main p, #article-body p',
            // Hashnode
            '.article-content p, .prose p',
            // Substack
            '.markup p, .post-content p',
            // WordPress
            '.entry-content p, .post-content p, .content p',
            // Generic
            'article p, main p, .content p, .post p, .article p',
            // Fallback
            'p'
        ];
        
        let paragraphs = [];
        
        // Try selectors in order of specificity
        for (const selector of contentSelectors) {
            paragraphs = Array.from(document.querySelectorAll(selector));
            if (paragraphs.length > 0) {
                this.log(`Found ${paragraphs.length} paragraphs using selector: ${selector}`);
                break;
            }
        }
        
        // Filter paragraphs by content quality
        paragraphs = paragraphs.filter(p => {
            const text = p.textContent.trim();
            
            // Basic content checks
            if (text.length < this.options.minParagraphLength) return false;
            if (this.isNavigationOrUI(p)) return false;
            if (this.isCodeBlock(p)) return false;
            if (this.isQuote(p)) return false;
            
            // Check if paragraph has good rendering context
            if (!this.hasGoodRenderingContext(p)) return false;
            
            // Check if paragraph is actually visible
            const rect = p.getBoundingClientRect();
            if (rect.height === 0 || rect.width === 0) return false;
            
            // Check if paragraph has proper display
            const styles = getComputedStyle(p);
            if (styles.display === 'none' || styles.visibility === 'hidden') return false;
            
            return true;
        });
        
        this.log(`Filtered to ${paragraphs.length} suitable paragraphs`);
        return paragraphs;
    }
    
    /**
     * Check if paragraph is navigation or UI element
     */
    isNavigationOrUI(paragraph) {
        const text = paragraph.textContent.toLowerCase().trim();
        
        // Skip very short text (likely UI elements)
        if (text.length < 50) {
            return true;
        }
        
        const uiKeywords = [
            'subscribe', 'follow us', 'share this', 'comment', 'login', 'register',
            'menu', 'navigation', 'footer', 'header', 'sidebar', 'advertisement',
            'read more', 'continue reading', 'related posts', 'tags:', 'categories:',
            'sign up', 'newsletter', 'get updates', 'latest stories', 'trending',
            'also read', 'more from', 'published on', 'updated on', 'by:', 'author:'
        ];
        
        // Check text content
        if (uiKeywords.some(keyword => text.includes(keyword))) {
            return true;
        }
        
        // Check parent elements (including HT-specific selectors)
        const uiSelectors = [
            'nav', 'header', 'footer', '.menu', '.sidebar', '.navigation',
            '.social', '.share', '.comments', '.related', '.tags', '.categories',
            '.advertisement', '.ads', '.promo', '.author', '.byline', '.meta',
            '.breadcrumb', '.pagination', '.trending', '.latest', '.recommended'
        ];
        
        return uiSelectors.some(selector => paragraph.closest(selector));
    }
    
    /**
     * Check if paragraph is a code block
     */
    isCodeBlock(paragraph) {
        const codeSelectors = ['pre', 'code', '.highlight', '.code-block', '.gist'];
        return codeSelectors.some(selector => 
            paragraph.matches(selector) || paragraph.closest(selector)
        );
    }
    
    /**
     * Check if paragraph is a quote
     */
    isQuote(paragraph) {
        return paragraph.matches('blockquote, .quote') || 
               paragraph.closest('blockquote, .quote') ||
               paragraph.textContent.trim().startsWith('"');
    }
    
    /**
     * Check if paragraph has good rendering context for injection
     */
    hasGoodRenderingContext(paragraph) {
        // Check if paragraph has a valid parent that can accept children
        const parent = paragraph.parentNode;
        if (!parent || parent.nodeType !== Node.ELEMENT_NODE) {
            return false;
        }
        
        // Check if parent is a problematic container
        const problematicParents = ['table', 'thead', 'tbody', 'tr', 'td', 'th', 'ul', 'ol', 'dl'];
        if (problematicParents.includes(parent.tagName.toLowerCase())) {
            return false;
        }
        
        // Check if parent has flow layout (not flex/grid with restricted children)
        const parentStyles = getComputedStyle(parent);
        
        // Avoid injecting into tightly controlled flex/grid containers
        if (parentStyles.display === 'inline' || parentStyles.display === 'inline-block') {
            return false;
        }
        
        // Check if paragraph itself has proper dimensions
        const styles = getComputedStyle(paragraph);
        if (styles.position === 'absolute' || styles.position === 'fixed') {
            return false;
        }
        
        // Ensure paragraph is in the normal document flow
        if (styles.float !== 'none') {
            return false;
        }
        
        return true;
    }
    
    /**
     * Inject a question at a specific insertion point
     */
    /**
     * Create a question element with new API format
     */
    createQuestionElement(question, index, colorClass = null) {
        const container = document.createElement('div');
        container.className = 'abqi-question-container';
        container.setAttribute('data-question-id', question.id);
        container.setAttribute('data-question-order', question.question_order || index + 1);
        
        const questionBox = document.createElement('div');
        questionBox.className = 'abqi-question-box';
        
        // Use provided color class, or pick a random one if not provided
        if (colorClass) {
            questionBox.classList.add(colorClass);
        } else {
            const colorClasses = [
                'abqi-color-beige',
                'abqi-color-purple',
                'abqi-color-coral',
                'abqi-color-mint',
                'abqi-color-lavender',
                'abqi-color-peach',
                'abqi-color-sky',
                'abqi-color-lemon'
            ];
            const randomColorIndex = Math.floor(Math.random() * colorClasses.length);
            questionBox.classList.add(colorClasses[randomColorIndex]);
        }
        
        // Question content wrapper (colored area)
        const questionContent = document.createElement('div');
        questionContent.className = 'abqi-question-content';
        
        // Icon container
        const questionIcon = document.createElement('div');
        questionIcon.className = 'abqi-question-icon';
        questionIcon.innerHTML = this.getQuestionTypeIcon(question.question_type);
        
        // Question text
        const questionText = document.createElement('div');
        questionText.className = 'abqi-question-text';
        questionText.textContent = question.question;
        
        // Assemble colored content area
        questionContent.appendChild(questionIcon);
        questionContent.appendChild(questionText);
        
        // White footer area with explore button
        const footer = document.createElement('div');
        footer.className = 'abqi-question-footer';
        
        const exploreBtn = document.createElement('button');
        exploreBtn.className = 'abqi-explore-btn';
        exploreBtn.innerHTML = 'EXPLORE <span class="abqi-arrow">→</span>';
        
        footer.appendChild(exploreBtn);
        
        // Assemble card structure
        questionBox.appendChild(questionContent);
        questionBox.appendChild(footer);
        container.appendChild(questionBox);
        
        // Click handler
        questionBox.addEventListener('click', () => this.handleQuestionClick(question));
        
        return container;
    }
    
    /**
     * Get icon for question type
     */
    getQuestionTypeIcon(questionType) {
        const icons = {
            'what if': '🤔',
            'comparison and contrast': '⚖️',
            'cause and effect': '🔗',
            'exploratory': '🔍',
            'analytical': '📊',
            'synthesis': '🧩',
            'evaluation': '⭐',
            'application': '🛠️',
            'comprehension': '💡',
            'knowledge': '📚'
        };
        
        return icons[questionType] || '❓';
    }
    
    /**
     * Format question type for display
     */
    formatQuestionType(questionType) {
        return questionType
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
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
        setTimeout(() => {
            this.currentDrawer.classList.add('abqi-drawer-open');
        }, 10);
        
        // Mark question as active
        document.querySelectorAll('.abqi-question-box').forEach(box => {
            box.classList.remove('abqi-active');
        });
        
        const questionElement = document.querySelector(`[data-question-id="${question.id}"] .abqi-question-box`);
        if (questionElement) {
            questionElement.classList.add('abqi-active');
        }
    }
    
    /**
     * Create drawer element based on Figma design (Group 1000007927)
     */
    createDrawer(question) {
        const drawer = document.createElement('div');
        drawer.className = 'abqi-drawer-overlay';
        drawer.setAttribute('data-question-id', question.id);
        
        const drawerContent = document.createElement('div');
        drawerContent.className = 'abqi-drawer';
        
        // Header with centered close button
        const header = document.createElement('div');
        header.className = 'abqi-drawer-header';
        
        const closeBtn = document.createElement('button');
        closeBtn.className = 'abqi-drawer-close';
        closeBtn.innerHTML = '×';
        closeBtn.setAttribute('aria-label', 'Close drawer');
        closeBtn.addEventListener('click', () => this.closeDrawer());
        
        header.appendChild(closeBtn);
        
        // Content with gradient background at top
        const content = document.createElement('div');
        content.className = 'abqi-drawer-content';
        
        // Ask Anything search section at top
        const searchSection = document.createElement('div');
        searchSection.className = 'abqi-drawer-search';
        searchSection.innerHTML = `
            <div class="abqi-search-container">
                <div class="abqi-search-inner">
                    <div class="abqi-search-icon-wrapper">
                        <svg class="abqi-search-icon" width="23" height="23" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <defs>
                                <linearGradient id="aiGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                    <stop offset="0%" style="stop-color:#863FFA;stop-opacity:1" />
                                    <stop offset="100%" style="stop-color:#863FFA;stop-opacity:0.8" />
                                </linearGradient>
                            </defs>
                            <path d="M12 2L13.5 8.5L20 10L13.5 11.5L12 18L10.5 11.5L4 10L10.5 8.5L12 2Z" fill="url(#aiGradient)"/>
                            <circle cx="12" cy="12" r="10" stroke="url(#aiGradient)" stroke-width="1.5" fill="none" opacity="0.5"/>
                            <path d="M16 8L17 10L19 11L17 12L16 14L15 12L13 11L15 10L16 8Z" fill="url(#aiGradient)" opacity="0.6"/>
                        </svg>
                    </div>
                    <div class="abqi-search-divider"></div>
                    <input type="text" class="abqi-search-input" placeholder="Ask anything..." />
                </div>
            </div>
        `;
        
        // AI Response section (dark background card) - Position #2
        const aiResponseSection = document.createElement('div');
        aiResponseSection.className = 'abqi-drawer-ai-response-wrapper';
        aiResponseSection.innerHTML = `
            <div class="abqi-drawer-ai-response">
                <div class="abqi-ai-response-content">
                    <div class="abqi-ai-response-text collapsed">${this.formatAnswer(question.answer)}</div>
                    <button class="abqi-read-more-btn">Read More →</button>
                </div>
            </div>
            <div class="abqi-ai-disclaimer">*AI Response. Error Possible. Double-check it.</div>
        `;
        
        // Store original answer for restoration
        aiResponseSection.setAttribute('data-original-answer', question.answer);
        
        // Sponsored Ads section - Position #3
        const sponsoredAdsSection = document.createElement('div');
        sponsoredAdsSection.className = 'abqi-drawer-sponsored';
        sponsoredAdsSection.innerHTML = `
            <div class="abqi-section-heading">Sponsored Ads</div>
            <div class="abqi-sponsored-grid">
                <div class="abqi-sponsored-item">
                    <div class="abqi-sponsored-card abqi-placeholder-beige"></div>
                    <div class="abqi-sponsored-info">
                        <div class="abqi-sponsored-name">Kutchina Breakfast Maker - Aroma</div>
                        <div class="abqi-sponsored-price">
                            <span class="abqi-price-current">₹4,999</span>
                            <span class="abqi-price-discount">38% off</span>
                            <span class="abqi-price-original">₹7,999</span>
                        </div>
                    </div>
                </div>
                <div class="abqi-sponsored-item">
                    <div class="abqi-sponsored-card abqi-placeholder-blue"></div>
                    <div class="abqi-sponsored-info">
                        <div class="abqi-sponsored-name">Kutchina Breakfast Maker - Aroma</div>
                        <div class="abqi-sponsored-price">
                            <span class="abqi-price-current">₹4,999</span>
                            <span class="abqi-price-discount">38% off</span>
                            <span class="abqi-price-original">₹7,999</span>
                        </div>
                    </div>
                </div>
                <div class="abqi-sponsored-item">
                    <div class="abqi-sponsored-card abqi-placeholder-green"></div>
                    <div class="abqi-sponsored-info">
                        <div class="abqi-sponsored-name">Kutchina Breakfast Maker - Aroma</div>
                        <div class="abqi-sponsored-price">
                            <span class="abqi-price-current">₹4,999</span>
                            <span class="abqi-price-discount">38% off</span>
                            <span class="abqi-price-original">₹7,999</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Some Questions in Mind section (HORIZONTAL SCROLL with circular badges) - Position #4
        const questionsSection = document.createElement('div');
        questionsSection.className = 'abqi-drawer-questions';
        const relatedQuestions = this.getRelatedQuestions(question);
        const badgeColors = ['#FFE8F7', '#E8F4DF', '#DDB8E9', '#FFF4DF']; // Pink, Green, Purple, Yellow
        questionsSection.innerHTML = `
            <div class="abqi-questions-heading-wrap">
              <div class="abqi-section-heading">Some Questions in Mind?</div>
              <div class="abqi-questions-underline">
                <svg xmlns="http://www.w3.org/2000/svg" width="88" height="6" viewBox="0 0 88 6" fill="none">
                  <path d="M0.811035 4.6176C5.249 3.31814 14.4638 0.830599 15.8194 1.27613C17.5139 1.83304 21.6291 6.10275 26.2284 3.68944C30.8278 1.27613 33.4906 -0.208908 38.8161 2.20434C44.1417 4.61759 46.3203 4.61759 51.8879 2.94686C57.4556 1.27613 57.6976 2.01867 62.7811 2.94686C67.8646 3.87504 73.1901 3.68937 78.7578 2.94686C83.2119 2.35285 85.9392 1.46177 86.7461 1.09049"
                      stroke="url(#paint0_linear_114_1724)" stroke-opacity="0.8" stroke-width="1.5" stroke-linecap="round"/>
                  <defs>
                    <linearGradient id="paint0_linear_114_1724" x1="0.811036" y1="5.32699" x2="86.6857" y2="0.0018701" gradientUnits="userSpaceOnUse">
                      <stop stop-color="#903FC0"/>
                      <stop offset="0.326923" stop-color="#FF66B2"/>
                      <stop offset="0.653846" stop-color="#FF7556"/>
                      <stop offset="1" stop-color="#FFD257"/>
                    </linearGradient>
                  </defs>
                </svg>
              </div>
            </div>
            <div class="abqi-questions-scroll-container">
                <div class="abqi-questions-bubbles">
                    ${relatedQuestions.map((q, index) => `
                        <button class="abqi-question-bubble" data-question-index="${index}">
                            <span class="abqi-bubble-text">${this.escapeHtml(q.text)}</span>
                            <div class="abqi-bubble-badge" style="background-color: ${badgeColors[index % badgeColors.length]}">
                                <svg width="12" height="19" viewBox="0 0 12 19" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M2 2L9 9.5L2 17" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" opacity="0.6"/>
                                </svg>
                            </div>
                        </button>
                    `).join('')}
                </div>
                <div class="abqi-questions-gradient-fade"></div>
            </div>
        `;
        
        // Related Articles section (with icons) - Position #5
        const relatedArticlesSection = document.createElement('div');
        relatedArticlesSection.className = 'abqi-drawer-related';
        relatedArticlesSection.innerHTML = `
            <div class="abqi-section-heading">Related Articles</div>
            <div class="abqi-related-articles-container">
                <div class="abqi-similar-blogs-loading">
                    <div class="abqi-loading-spinner"></div>
                    <div class="abqi-loading-text">Finding related articles...</div>
                </div>
            </div>
        `;
        
        // Assemble sections in CORRECT Figma order (100% match)
        content.appendChild(searchSection);
        content.appendChild(aiResponseSection);
        content.appendChild(this.createDividerSVG());
        content.appendChild(sponsoredAdsSection);
        content.appendChild(this.createDividerSVG());
        content.appendChild(questionsSection);
        content.appendChild(this.createDividerSVG());
        content.appendChild(relatedArticlesSection);
        // Do NOT overwrite content.innerHTML after this point.
        
        drawerContent.appendChild(header);
        drawerContent.appendChild(content);
        drawer.appendChild(drawerContent);
        
        // Close on overlay click
        drawer.addEventListener('click', (e) => {
            if (e.target === drawer) {
                this.closeDrawer();
            }
        });
        
        // Setup functionality
        this.setupSearchFunctionality(drawer, question);
        this.setupReadMoreFunctionality(drawer);
        this.setupQuestionBubbles(drawer, question);
        this.loadSimilarArticles(drawer, question);
        
        return drawer;
    }
    
    /**
     * Get related questions for the "Some Questions in Mind" section
     */
    getRelatedQuestions(currentQuestion) {
        // Get other questions from the same blog (excluding current)
        const otherQuestions = this.questions
            .filter(q => q.id !== currentQuestion.id)
            .slice(0, 4); // Show up to 4 related questions
        
        return otherQuestions.map(q => ({
            id: q.id,
            text: q.question,
            icon: '💭',
            question: q
        }));
    }
    
    /**
     * Setup Read More button functionality
     */
    setupReadMoreFunctionality(drawer) {
        const readMoreBtn = drawer.querySelector('.abqi-read-more-btn');
        const responseText = drawer.querySelector('.abqi-ai-response-text');
        
        if (!readMoreBtn || !responseText) return;
        
        readMoreBtn.addEventListener('click', () => {
            const isCollapsed = responseText.classList.contains('collapsed');
            
            if (isCollapsed) {
                responseText.classList.remove('collapsed');
                readMoreBtn.textContent = 'Read Less ↑';
            } else {
                responseText.classList.add('collapsed');
                readMoreBtn.textContent = 'Read More →';
                // Scroll to top of drawer
                drawer.querySelector('.abqi-drawer-content').scrollTop = 0;
            }
        });
    }
    
    /**
     * Setup question bubble click handlers
     */
    setupQuestionBubbles(drawer, currentQuestion) {
        const bubbles = drawer.querySelectorAll('.abqi-question-bubble');
        
        bubbles.forEach((bubble, index) => {
            bubble.addEventListener('click', () => {
                const relatedQuestions = this.getRelatedQuestions(currentQuestion);
                if (relatedQuestions[index]) {
                    const newQuestion = relatedQuestions[index].question;
                    // Close current drawer and open new one
                    this.closeDrawer();
                    setTimeout(() => {
                        this.handleQuestionClick(newQuestion);
                    }, 300);
                }
            });
        });
    }
    
    /**
     * Load similar articles (renamed from loadSimilarBlogs)
     */
    async loadSimilarArticles(drawer, question) {
        const articlesContainer = drawer.querySelector('.abqi-related-articles-container');
        
        if (!articlesContainer) {
            this.log('Related articles container not found in drawer');
            return;
        }
        
        try {
            // Call similar blogs API
            const similarBlogs = await this.callSimilarBlogsAPI(question.id);
            
            if (similarBlogs && similarBlogs.length > 0) {
                this.displayRelatedArticles(articlesContainer, similarBlogs);
            } else {
                this.showNoRelatedArticles(articlesContainer);
            }
            
        } catch (error) {
            this.log('Error loading related articles:', error);
            this.showRelatedArticlesError(articlesContainer);
        }
    }
    
    /**
     * Display related articles in the container (Figma-styled with icons)
     */
    displayRelatedArticles(container, articles) {
        // Icon options for articles
        const icons = ['☁️', '💼', '💰'];
        
        const articlesHtml = articles.map((article, index) => {
            const icon = icons[index % icons.length];
            const titleWithHighlight = this.highlightKeywords(article.title);
            return `
                <div class="abqi-related-article-item">
                    <div class="abqi-article-icon">${icon}</div>
                    <div class="abqi-article-content">
                        <a href="${article.url}" target="_blank" rel="noopener noreferrer" class="abqi-article-title">
                            ${titleWithHighlight}
                        </a>
                        <span class="abqi-article-link">${this.escapeHtml(article.url)}</span>
                    </div>
                </div>
            `;
        }).join('');
        
        container.innerHTML = `
            <div class="abqi-related-articles-list">
                ${articlesHtml}
            </div>
        `;
    }
    
    /**
     * Highlight keywords in article titles (simulates bold text from Figma)
     */
    highlightKeywords(title) {
        // This is a simple implementation - could be enhanced with actual keyword detection
        const keywords = ['breakfast', 'energy', 'skip', 'affect', 'during'];
        let highlighted = this.escapeHtml(title);
        
        keywords.forEach(keyword => {
            const regex = new RegExp(`(${keyword})`, 'gi');
            highlighted = highlighted.replace(regex, '<strong>$1</strong>');
        });
        
        return highlighted;
    }
    
    /**
     * Show message when no related articles found
     */
    showNoRelatedArticles(container) {
        container.innerHTML = `
            <div class="abqi-related-articles-empty">
                <div class="abqi-empty-icon">📚</div>
                <div class="abqi-empty-message">No related articles found</div>
            </div>
        `;
    }
    
    /**
     * Show error message for related articles
     */
    showRelatedArticlesError(container) {
        container.innerHTML = `
            <div class="abqi-related-articles-error">
                <div class="abqi-error-icon">⚠️</div>
                <div class="abqi-error-message">Unable to load related articles</div>
            </div>
        `;
    }
    
    /**
     * Load similar blogs for the question
     */
    async loadSimilarBlogs(drawer, question) {
        const similarBlogsContainer = drawer.querySelector('.abqi-similar-blogs-container');
        
        if (!similarBlogsContainer) {
            this.log('Similar blogs container not found in drawer');
            return;
        }
        
        try {
            // Call similar blogs API
            const similarBlogs = await this.callSimilarBlogsAPI(question.id);
            
            if (similarBlogs && similarBlogs.length > 0) {
                this.displaySimilarBlogs(similarBlogsContainer, similarBlogs);
            } else {
                this.showNoSimilarBlogs(similarBlogsContainer);
            }
            
        } catch (error) {
            this.log('Error loading similar blogs:', error);
            this.showSimilarBlogsError(similarBlogsContainer);
        }
    }
    
    /**
     * Call the Similar Blogs API endpoint
     */
    async callSimilarBlogsAPI(questionId) {
        // Use provided API base URL or fallback to localhost
        const baseUrl = this.options.apiBaseUrl || 'http://localhost:8005/api/v1';
        // Updated for Content Processing Service (2-service architecture)
        const apiUrl = `${baseUrl}/search/similar`;
        
        this.log(`Calling Similar Blogs API: ${apiUrl}`);
        
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question_id: questionId,
                limit: 3
            })
        });
        
        if (!response.ok) {
            throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Content Processing Service returns data directly (no success wrapper)
        return data.similar_blogs || [];
    }
    
    /**
     * Display similar blogs in the container
     */
    displaySimilarBlogs(container, similarBlogs) {
        const blogsHtml = similarBlogs.map(blog => `
            <div class="abqi-similar-blog-item">
                <a href="${blog.url}" target="_blank" rel="noopener noreferrer" class="abqi-similar-blog-title">
                    ${this.escapeHtml(blog.title)}
                </a>
            </div>
        `).join('');
        
        container.innerHTML = `
            <div class="abqi-similar-blogs-list">
                ${blogsHtml}
            </div>
        `;
    }
    
    /**
     * Show message when no similar blogs found
     */
    showNoSimilarBlogs(container) {
        container.innerHTML = `
            <div class="abqi-similar-blogs-empty">
                <div class="abqi-empty-icon">📚</div>
                <div class="abqi-empty-message">No related articles found</div>
            </div>
        `;
    }
    
    /**
     * Show error message for similar blogs
     */
    showSimilarBlogsError(container) {
        container.innerHTML = `
            <div class="abqi-similar-blogs-error">
                <div class="abqi-error-icon">⚠️</div>
                <div class="abqi-error-message">Unable to load related articles</div>
            </div>
        `;
    }
    
    /**
     * Setup search functionality for the drawer
     */
    setupSearchFunctionality(drawer, originalQuestion) {
        const searchInput = drawer.querySelector('.abqi-search-input');
        const answerSection = drawer.querySelector('.abqi-drawer-ai-response');
        const responseText = drawer.querySelector('.abqi-ai-response-text');
        const readMoreBtn = drawer.querySelector('.abqi-read-more-btn');
        
        if (!searchInput || !responseText) {
            this.log('Search elements not found in drawer');
            return;
        }
        
        // Handle search submit
        const performSearch = async () => {
            const query = searchInput.value.trim();
            if (!query || query.length < 5) {
                this.showSearchError('Please enter at least 5 characters');
                return;
            }
            
            try {
                // Show loading state
                responseText.innerHTML = `
                    <div class="abqi-loading">
                        <div class="abqi-loading-spinner"></div>
                        <div class="abqi-loading-text">Getting AI answer...</div>
                    </div>
                `;
                responseText.classList.remove('collapsed');
                
                // Call Q&A API
                const response = await this.callQAAPI(query);
                
                // Display new answer
                responseText.innerHTML = this.formatAnswer(response.answer);
                responseText.classList.add('collapsed');
                
                // Update read more button
                if (readMoreBtn) {
                    readMoreBtn.textContent = 'Read More →';
                    readMoreBtn.style.display = 'inline-flex';
                }
                
                // Add metadata
                const metadata = document.createElement('div');
                metadata.className = 'abqi-search-metadata';
                metadata.innerHTML = `<small>AI Answer • ${response.word_count} words • ${Math.round(response.processing_time_ms)}ms</small>`;
                responseText.parentElement.appendChild(metadata);
                
            } catch (error) {
                this.log('Search error:', error);
                responseText.innerHTML = `
                    <div class="abqi-unavailable">
                        <div class="abqi-unavailable-icon">⚠️</div>
                        <div class="abqi-unavailable-title">AI Service Unavailable</div>
                        <div class="abqi-unavailable-message">Please try again later.</div>
                    </div>
                `;
                this.showSearchError('AI service not available at the moment. Please try again later.');
            }
        };
        
        // Enter key in search input
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                performSearch();
            }
        });
        
        // Store original answer for restoration when drawer reopens
        drawer.setAttribute('data-original-question-id', originalQuestion.id);
    }
    
    /**
     * Call the Q&A API endpoint
     */
    async callQAAPI(question) {
        // Use provided API base URL or fallback to localhost
        const baseUrl = this.options.apiBaseUrl || 'http://localhost:8005/api/v1';
        const apiUrl = `${baseUrl}/qa/ask`;
        
        this.log(`Calling Q&A API: ${apiUrl}`);
        
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question
            })
        });
        
        if (!response.ok) {
            throw new Error(`API request failed: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'API returned error');
        }
        
        return data;
    }
    
    /**
     * Show loading state in answer display
     */
    showSearchLoading(answerDisplay) {
        answerDisplay.innerHTML = `
            <div class="abqi-loading">
                <div class="abqi-loading-spinner"></div>
                <div class="abqi-loading-text">Getting AI answer...</div>
            </div>
        `;
    }
    
    /**
     * Display search result in answer display
     */
    displaySearchResult(answerDisplay, response) {
        const formattedAnswer = this.formatAnswer(response.answer);
        const metadata = `
            <div class="abqi-search-metadata">
                <small>AI Answer • ${response.word_count} words • ${Math.round(response.processing_time_ms)}ms</small>
            </div>
        `;
        
        answerDisplay.innerHTML = formattedAnswer + metadata;
        
        // Add visual indicator that this is a search result
        answerDisplay.classList.add('abqi-search-result');
    }
    
    /**
     * Show search unavailable message in answer display
     */
    showSearchUnavailable(answerDisplay) {
        answerDisplay.innerHTML = `
            <div class="abqi-unavailable">
                <div class="abqi-unavailable-icon">⚠️</div>
                <div class="abqi-unavailable-title">AI Service Unavailable</div>
                <div class="abqi-unavailable-message">The AI search feature is not available at the moment. Please try again later.</div>
            </div>
        `;
        
        // Add visual indicator that this is an unavailable state
        answerDisplay.classList.add('abqi-unavailable-state');
    }
    
    /**
     * Show search error message
     */
    showSearchError(message) {
        // Create temporary error message
        const errorDiv = document.createElement('div');
        errorDiv.className = 'abqi-search-error';
        errorDiv.textContent = message;
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ff4444;
            color: white;
            padding: 12px 16px;
            border-radius: 4px;
            font-size: 14px;
            z-index: 10001;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        `;
        
        document.body.appendChild(errorDiv);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (errorDiv.parentNode) {
                errorDiv.parentNode.removeChild(errorDiv);
            }
        }, 3000);
    }
    
    /**
     * Close the current drawer
     */
    closeDrawer() {
        if (!this.currentDrawer) return;
        
        this.currentDrawer.classList.remove('abqi-drawer-open');
        
        setTimeout(() => {
            if (this.currentDrawer && this.currentDrawer.parentNode) {
                this.currentDrawer.parentNode.removeChild(this.currentDrawer);
            }
            this.currentDrawer = null;
        }, 300);
        
        // Remove active state from questions
        document.querySelectorAll('.abqi-question-box.abqi-active').forEach(box => {
            box.classList.remove('abqi-active');
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
     * Setup event listeners
     */
    setupEventListeners() {
        document.addEventListener('keydown', this.handleEscapeKey);
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
        // Responsive adjustments if needed
    }
    
    /**
     * Inject CSS styles
     */
    injectStyles() {
        if (document.getElementById('abqi-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'abqi-styles';
        style.textContent = this.getCSS();
        document.head.appendChild(style);
    }
    
    /**
     * Get CSS styles
     */
    getCSS() {
        return `
            /* Auto Blog Question Injector Styles */
            /* Questions Grid Container */
            .abqi-questions-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                margin: 8px 0 40px 0;
                max-width: 100%;
            }
            
            .abqi-question-container {
                max-width: 320px;
                opacity: 0;
                transform: translateY(15px);
                transition: all 0.4s ease;
            }
            
            .abqi-question-container.abqi-visible {
                opacity: 1;
                transform: translateY(0);
            }
            
            /* Section Header with Curvy Decorative Line */
            .abqi-section-header {
                font-size: 20px;
                font-weight: 700;
                color: #1a1a1a;
                margin: 32px 0 12px 0;
                display: inline-block;
                position: relative;
                padding-bottom: 12px;
            }
            
            .abqi-section-header::after {
                content: '';
                position: absolute;
                bottom: 0;
                left: 50%;
                transform: translateX(-50%);
                width: 80px;
                height: 6px;
                background: linear-gradient(90deg, 
                    #ff6b6b 0%, 
                    #feca57 25%, 
                    #48dbfb 50%, 
                    #ff9ff3 75%, 
                    #54a0ff 100%
                );
                border-radius: 50% 50% 50% 50% / 60% 60% 40% 40%;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }
            
            /* Question Box - Card Design with White Border */
            .abqi-question-box {
                background: transparent;
                border: 2px solid #ffffff;
                border-radius: 16px;
                cursor: pointer;
                transition: all 0.3s ease;
                position: relative;
                box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
                display: flex;
                flex-direction: column;
                height: 100%;
                min-height: 220px;
                overflow: hidden;
            }
            
            .abqi-question-box:hover {
                transform: translateY(-4px);
                box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
            }
            
            .abqi-question-box.abqi-active {
                transform: translateY(-4px);
                box-shadow: 0 10px 24px rgba(0, 0, 0, 0.15);
            }
            
            /* Question Content - Colored Area */
            .abqi-question-content {
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: flex-start;
                justify-content: flex-start;
                padding: 20px;
                background: #f5f0e8;
            }
            
            /* Pastel Color Variants for Content Area */
            .abqi-question-box.abqi-color-beige .abqi-question-content {
                background: #f5f0e8;
            }
            
            .abqi-question-box.abqi-color-purple .abqi-question-content {
                background: #e8e4f3;
            }
            
            .abqi-question-box.abqi-color-coral .abqi-question-content {
                background: #fce8e6;
            }
            
            .abqi-question-box.abqi-color-mint .abqi-question-content {
                background: #e8f5f0;
            }
            
            .abqi-question-box.abqi-color-lavender .abqi-question-content {
                background: #f0e8f5;
            }
            
            .abqi-question-box.abqi-color-peach .abqi-question-content {
                background: #ffe8e0;
            }
            
            .abqi-question-box.abqi-color-sky .abqi-question-content {
                background: #e0f0ff;
            }
            
            .abqi-question-box.abqi-color-lemon .abqi-question-content {
                background: #fff8e0;
            }
            
            /* Circular Icon Container */
            .abqi-question-icon {
                flex-shrink: 0;
                width: 48px;
                height: 48px;
                border-radius: 50%;
                background: #ffffff;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                margin-bottom: 14px;
                align-self: flex-start;
            }
            
            .abqi-question-text {
                font-size: 14px;
                font-weight: 600;
                line-height: 1.4;
                color: #2c3e50;
                text-align: left;
                width: 100%;
            }
            
            /* White Footer Area */
            .abqi-question-footer {
                background: #ffffff;
                padding: 16px 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-top: 1px solid rgba(0, 0, 0, 0.05);
            }
            
            /* Explore Button */
            .abqi-explore-btn {
                padding: 0;
                background: transparent;
                border: none;
                color: #666;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.8px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 6px;
                transition: all 0.2s ease;
            }
            
            .abqi-explore-btn:hover {
                color: #333;
            }
            
            .abqi-explore-btn .abqi-arrow {
                font-size: 14px;
                font-weight: 700;
                background: linear-gradient(90deg, 
                    #ff6b6b 0%, 
                    #feca57 33%, 
                    #48dbfb 66%, 
                    #ff9ff3 100%
                );
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                transition: transform 0.2s ease;
            }
            
            .abqi-question-box:hover .abqi-arrow {
                transform: translateX(3px);
            }
            
            /* Drawer Styles */
            .abqi-drawer-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0);
                z-index: 10000;
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
                overflow: visible;
            }
            
            .abqi-drawer-overlay.abqi-drawer-open {
                opacity: 1;
                visibility: visible;
                background: rgba(0, 0, 0, 0.6);
            }
            
            .abqi-drawer {
                position: absolute;
                right: 0;
                top: 50px;
                width: 700px;
                max-width: 90vw;
                height: calc(100% - 50px);
                background: white;
                box-shadow: -5px 0 25px rgba(0, 0, 0, 0.15);
                transform: translateX(100%);
                transition: transform 0.3s ease;
                display: flex;
                flex-direction: column;
                overflow: visible;
                border-radius: 30px 0 0 0;
            }
            
            .abqi-drawer-overlay.abqi-drawer-open .abqi-drawer {
                transform: translateX(0);
            }
            
            .abqi-drawer-header {
                padding: 0;
                border-bottom: none;
                display: flex;
                justify-content: center;
                align-items: flex-start;
                background: transparent;
                position: absolute;
                top: -28px;
                left: 0;
                right: 0;
                z-index: 1001;
                pointer-events: none;
            }
            
            .abqi-drawer-close {
                background: #000000;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: #ffffff;
                padding: 0;
                width: 56px;
                height: 56px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: all 0.3s ease;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
                pointer-events: auto;
                line-height: 1;
                font-weight: 300;
            }
            
            .abqi-drawer-close:hover {
                background: #1a1a1a;
                transform: scale(1.05);
                box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
            }
            
            .abqi-drawer-content {
                flex: 1;
                overflow-y: auto;
                overflow-x: hidden;
                padding: 0;
                margin-top: 0;
            }
            
            /* Drawer sections */
            .abqi-drawer-search,
            .abqi-drawer-ai-response-wrapper,
            .abqi-drawer-sponsored,
            .abqi-drawer-questions,
            .abqi-drawer-related {
                padding: 20px 30px;
                border-bottom: none !important;
                background: #ffffff;
            }
            
            /* Search section at top - with SUBTLE gradient background */
            .abqi-drawer-search {
                padding: 20px 30px 25px 30px;
                border-bottom: none;
                border-radius: 30px 0 0 0;
                background: linear-gradient(180deg, #F8F4FF 0%, #FFF5FB 100%);
            }
            
            /* AI Response section wrapper - with SUBTLE gradient background (same as search) */
            .abqi-drawer-ai-response-wrapper {
                padding: 25px 0 0 0;
                border-bottom: none !important;
                background: linear-gradient(180deg, #F8F4FF 0%, #FFF5FB 100%);
            }
            
            /* Questions section */
            .abqi-drawer-questions {
                padding: 20px 30px 25px 30px;
                border-bottom: none !important;
            }
            
            /* AI Response section */
            .abqi-drawer-ai-response {
                background: #1a0d28;
                color: #ffffff;
                padding: 30px;
                border-radius: 20px;
                margin: 0 30px 0 30px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            }
            
            .abqi-ai-response-content {
                position: relative;
            }
            
            .abqi-ai-response-text {
                font-size: 16px;
                line-height: 1.75;
                color: #ffffff !important;
                max-height: none;
                overflow: visible;
                transition: max-height 0.3s ease;
                font-weight: 300;
                background: transparent !important;
                background-color: transparent !important;
                text-decoration: none !important;
            }
            
            .abqi-ai-response-text * {
                background: transparent !important;
                background-color: transparent !important;
                color: #ffffff !important;
                text-decoration: none !important;
            }
            
            .abqi-ai-response-text p {
                margin: 0 0 16px 0 !important;
                padding: 0 !important;
                background: transparent !important;
                background-color: transparent !important;
                color: #ffffff !important;
                display: block !important;
                text-decoration: none !important;
            }
            
            .abqi-ai-response-text p:last-child {
                margin-bottom: 0 !important;
            }
            
            .abqi-ai-response-text strong {
                font-weight: 600 !important;
                color: #ffffff !important;
                background: transparent !important;
                background-color: transparent !important;
                text-decoration: none !important;
            }
            
            .abqi-ai-response-text em {
                font-style: italic !important;
                color: #ffffff !important;
                background: transparent !important;
                background-color: transparent !important;
                text-decoration: none !important;
            }
            
            .abqi-ai-response-text br {
                display: block !important;
                margin: 8px 0 !important;
                content: "" !important;
                background: transparent !important;
                text-decoration: none !important;
            }
            
            /* Extra specificity for collapsed state */
            .abqi-ai-response-text.collapsed * {
                background: transparent !important;
                background-color: transparent !important;
                color: #ffffff !important;
                text-decoration: none !important;
            }
            
            .abqi-ai-response-text.collapsed p {
                background: transparent !important;
                background-color: transparent !important;
                text-decoration: none !important;
            }
            
            .abqi-ai-response-text.collapsed {
                max-height: 252px;
                overflow: hidden;
                position: relative;
            }
            
            .abqi-ai-response-text.collapsed::after {
                content: '';
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                height: 60px;
                background: linear-gradient(to bottom, rgba(26, 13, 40, 0) 0%, rgba(26, 13, 40, 0.6) 40%, #1a0d28 100%);
                pointer-events: none;
            }
            
            .abqi-read-more-btn {
                background: #5a5065;
                border: none;
                color: #ffffff;
                font-size: 16px;
                font-weight: 500;
                font-style: italic;
                margin-top: 20px;
                cursor: pointer;
                padding: 12px 28px;
                border-radius: 8px;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                transition: all 0.2s ease;
                text-transform: capitalize;
            }
            
            .abqi-read-more-btn:hover {
                background: #6a607a;
                transform: translateY(-1px);
            }
            
            .abqi-ai-disclaimer {
                margin: 15px 30px 0 30px;
                padding: 0 0 30px 0;
                border-top: none;
                font-size: 13px;
                color: #666;
                font-style: italic;
                font-weight: 300;
                opacity: 0.8;
                background: transparent;
            }
            
            .abqi-search-metadata {
                margin-top: 12px;
                padding-top: 12px;
                border-top: 1px solid rgba(255, 255, 255, 0.15);
                font-size: 11px;
                color: #66b3ff;
            }
            
            .abqi-search-metadata small {
                color: #66b3ff;
                font-weight: 500;
            }
            
            .abqi-section-label {
                font-size: 14px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
                color: #6c757d;
                margin-bottom: 12px;
            }
            
            .abqi-section-heading {
                font-size: 18px;
                font-weight: 600;
                color: #000000;
                margin-bottom: 18px;
            }
            
            /* Sponsored Ads section */
            .abqi-sponsored-grid {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 18px;
            }
            
            .abqi-sponsored-item {
                display: flex;
                flex-direction: column;
                gap: 14px;
            }
            
            .abqi-sponsored-card {
                height: 114px;
                border-radius: 14px;
                border: none;
                background: #f8f8f8;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
                cursor: pointer;
                box-shadow: 0 0 28px rgba(227, 216, 235, 0.2);
            }
            
            .abqi-sponsored-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 32px rgba(227, 216, 235, 0.35);
            }
            
            .abqi-sponsored-card.abqi-placeholder-beige {
                background: #FFF4DF;
            }
            
            .abqi-sponsored-card.abqi-placeholder-blue {
                background: #DFF0FF;
            }
            
            .abqi-sponsored-card.abqi-placeholder-green {
                background: #E7F4DF;
            }
            
            .abqi-sponsored-info {
                display: flex;
                flex-direction: column;
                gap: 6px;
            }
            
            .abqi-sponsored-name {
                font-size: 14px;
                font-weight: 400;
                color: #552e96;
                line-height: 1.4;
                opacity: 0.9;
            }
            
            .abqi-sponsored-price {
                display: flex;
                align-items: center;
                gap: 8px;
                flex-wrap: wrap;
            }
            
            .abqi-price-current {
                font-size: 15px;
                font-weight: 600;
                color: #000000;
                opacity: 0.9;
            }
            
            .abqi-price-discount {
                font-size: 12px;
                font-weight: 400;
                color: #000000;
                opacity: 0.5;
            }
            
            .abqi-price-original {
                font-size: 12px;
                color: #000000;
                opacity: 0.4;
                text-decoration: line-through;
            }
            
            /* Some Questions in Mind section - HORIZONTAL SCROLL with circular badges (Figma exact) */
            .abqi-questions-scroll-container {
                position: relative;
                width: 100%;
                overflow: hidden;
            }
            
            .abqi-questions-bubbles {
                display: flex;
                gap: 10px;
                overflow-x: auto;
                overflow-y: hidden;
                padding-bottom: 10px;
                scroll-behavior: smooth;
                -webkit-overflow-scrolling: touch;
                scrollbar-width: thin;
                scrollbar-color: rgba(134, 63, 250, 0.1) #f5f5f5;
            }
            
            .abqi-question-bubble {
                background: #fff;
                border: 1px solid rgba(134,63,250,0.06);
                border-radius: 390px;
                padding: 13px 20px;
                cursor: pointer;
                transition: box-shadow 0.2s, border 0.2s;
                display: flex;
                align-items: center;
                justify-content: space-between;
                text-align: left;
                font-size: 16px;
                font-weight: 400;
                color: #231f20;
                box-shadow: 0 4px 24px rgba(134,63,250,0.08);
                min-width: 230px;
                max-width: 290px;
                flex-shrink: 0;
            }
            .abqi-question-bubble:hover {
                background: #f7f1fe;
                border-color: #be93fc;
                box-shadow: 0 8px 32px rgba(134, 63, 250, 0.17);
            }
            .abqi-bubble-text {
                flex: 1;
                font-size: 16px;
                font-weight: 400;
                line-height: 1.38;
                margin-right: 12px;
                color: #231f20;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: pre-line;
            }
            .abqi-bubble-badge {
                margin-left: 12px;
                width: 51px;
                height: 51px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 2px 6px rgba(134,63,250,0.07);
            }
            .abqi-bubble-badge svg {
                width: 24px;
                height: 24px;
                color: #231f20;
                opacity: 0.7;
                display: block;
            }
            .abqi-questions-gradient-fade {
                position: absolute;
                left: 0;
                top: 0;
                bottom: 10px;
                width: 44px;
                background: linear-gradient(to right, #fff 0%, rgba(255,255,255,0.85) 38%, rgba(255,255,255,0.04) 90%, rgba(255,255,255,0.01) 100%);
                pointer-events: none;
                z-index: 1;
            }
            
            /* Related Articles section */
            .abqi-related-articles-list {
                display: flex;
                flex-direction: column;
                gap: 18px;
            }
            
            .abqi-related-article-item {
                display: flex;
                align-items: flex-start;
                gap: 14px;
                padding: 0;
                background: transparent;
                border-radius: 0;
                border: none;
                transition: all 0.3s ease;
            }
            
            .abqi-related-article-item:hover {
                transform: translateX(4px);
            }
            
            .abqi-article-icon {
                flex-shrink: 0;
                width: 54px;
                height: 54px;
                background: rgba(221, 184, 233, 0.1);
                border-radius: 15px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
                box-shadow: 0 0 20px rgba(227, 216, 235, 0.2);
            }
            
            .abqi-article-content {
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 6px;
            }
            
            .abqi-article-title {
                font-size: 16px;
                font-weight: 400;
                color: #000000;
                text-decoration: none;
                line-height: 1.4;
                display: block;
                transition: color 0.2s ease;
                opacity: 0.9;
            }
            
            .abqi-article-title:hover {
                color: #863ffa;
                text-decoration: none;
            }
            
            .abqi-article-title strong {
                font-weight: 600;
            }
            
            .abqi-article-link {
                font-size: 14px;
                font-weight: 300;
                color: #552e96;
                display: block;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            
            .abqi-related-articles-empty,
            .abqi-related-articles-error {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
                padding: 30px 20px;
                color: #6c757d;
                text-align: center;
            }
            
            /* Search container styles - Figma design with single border */
            .abqi-search-container {
                display: flex;
                align-items: center;
                border: 1px solid #863ffa;
                border-radius: 300px;
                padding: 0;
                background: transparent;
                transition: border-color 0.3s ease;
            }
            
            .abqi-search-container:focus-within {
                border: 2px solid #863ffa;
                box-shadow: none;
            }
            
            .abqi-search-inner {
                display: flex;
                align-items: center;
                background: transparent;
                border-radius: 300px;
                flex: 1;
                padding: 6px 8px;
            }
            
            .abqi-search-icon-wrapper {
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 6px 12px;
                flex-shrink: 0;
            }
            
            .abqi-search-icon {
                display: block;
                flex-shrink: 0;
            }
            
            .abqi-search-divider {
                width: 1px;
                height: 24px;
                background: transparent;
                margin: 0;
                flex-shrink: 0;
            }
            
            .abqi-search-input {
                flex: 1;
                padding: 10px 18px;
                border: none;
                background: transparent;
                font-size: 12px;
                font-family: inherit;
                color: #736786;
                outline: none;
            }
            
            .abqi-search-input::placeholder {
                color: #736786;
                font-size: 12px;
                font-weight: 400;
                opacity: 0.6;
            }
            
            .abqi-question-display {
                font-size: 18px;
                font-weight: 600;
                line-height: 1.5;
                color: #2c3e50;
                padding: 20px;
                background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
                border-radius: 10px;
                border-left: 5px solid #2196f3;
            }
            
            .abqi-answer-display {
                font-size: 16px;
                line-height: 1.7;
                color: #495057;
                padding: 20px;
                background: linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%);
                border-radius: 10px;
                border-left: 5px solid #4caf50;
            }
            
            .abqi-answer-display p {
                margin: 0 0 15px 0;
            }
            
            .abqi-answer-display p:last-child {
                margin-bottom: 0;
            }
            
            
            /* Tablet responsiveness (768px - 1024px) */
            @media (max-width: 1024px) and (min-width: 769px) {
                .abqi-questions-grid {
                    grid-template-columns: repeat(2, 1fr);
                    gap: 16px;
                }
                
                .abqi-question-container {
                    max-width: none;
                }
                
                .abqi-question-box {
                    min-height: 200px;
                    border-width: 2px;
                }
                
                .abqi-question-content {
                    padding: 18px;
                }
                
                .abqi-question-icon {
                    width: 44px;
                    height: 44px;
                    font-size: 22px;
                    margin-bottom: 12px;
                }
                
                .abqi-question-text {
                    font-size: 13px;
                }
                
                .abqi-question-footer {
                    padding: 14px 18px;
                }
                
                .abqi-explore-btn {
                    font-size: 10px;
                }
                
                .abqi-drawer {
                    width: 420px;
                }
            }
            
            /* Mobile responsiveness (max 768px) */
            @media (max-width: 768px) {
                /* Section Header */
                .abqi-section-header {
                    font-size: 18px;
                    margin: 24px 0 10px 0;
                    padding-bottom: 12px;
                }
                
                .abqi-section-header::after {
                    width: 65px;
                    height: 5px;
                }
                
                .abqi-questions-grid {
                    grid-template-columns: 1fr;
                    gap: 14px;
                    margin: 8px 0 32px 0;
                }
                
                /* Question Cards - Optimized for mobile */
                .abqi-question-box {
                    border-radius: 14px;
                    min-height: 200px;
                    border-width: 2px;
                }
                
                .abqi-question-content {
                    padding: 16px;
                }
                
                .abqi-question-icon {
                    width: 42px;
                    height: 42px;
                    font-size: 20px;
                    margin-bottom: 10px;
                }
                
                .abqi-question-text {
                    font-size: 13px;
                    line-height: 1.4;
                }
                
                .abqi-question-footer {
                    padding: 14px 16px;
                }
                
                .abqi-explore-btn {
                    font-size: 10px;
                }
                
                .abqi-explore-btn .abqi-arrow {
                    font-size: 12px;
                }
                
                /* Drawer - Full screen on mobile */
                .abqi-drawer {
                    width: 100%;
                    max-width: 100%;
                    border-radius: 20px 0 0 0;
                }
                
                .abqi-drawer-header {
                    padding: 0;
                    top: -24px;
                }
                
                .abqi-drawer-close {
                    width: 48px;
                    height: 48px;
                    font-size: 22px;
                }
                
                .abqi-drawer-content {
                    padding: 0;
                }
                
                .abqi-drawer-search {
                    padding: 16px 20px 20px 20px;
                    border-radius: 20px 0 0 0;
                }
                
                .abqi-drawer-ai-response {
                    padding: 24px 20px;
                    margin: 0 20px;
                }
                
                .abqi-ai-disclaimer {
                    margin: 12px 20px 0 20px;
                    padding: 0 0 24px 0;
                }
                
                .abqi-drawer-sponsored,
                .abqi-drawer-questions,
                .abqi-drawer-related {
                    padding: 18px 20px;
                }
                
                .abqi-sponsored-grid {
                    grid-template-columns: 1fr;
                    gap: 16px;
                }
                
                .abqi-section-heading {
                    font-size: 17px;
                    margin-bottom: 16px;
                }
                
                .abqi-search-input {
                    font-size: 12px;
                    padding: 10px 16px;
                }
                
                .abqi-answer-display {
                    font-size: 15px;
                    padding: 14px;
                    line-height: 1.6;
                }
                
                .abqi-question-bubble {
                    font-size: 14px;
                    padding: 14px 28px;
                    max-width: 320px;
                }
                
                .abqi-bubble-text {
                    max-width: 200px;
                }
                
                .abqi-bubble-badge {
                    width: 48px;
                    height: 48px;
                }
                
                .abqi-questions-gradient-fade {
                    width: 80px;
                }
                
                .abqi-article-title {
                    font-size: 15px;
                }
                
                .abqi-article-link {
                    font-size: 13px;
                }
            }
            
            /* Small mobile devices (max 480px) */
            @media (max-width: 480px) {
                .abqi-section-header {
                    font-size: 15px;
                    margin: 20px 0 8px 0;
                }
                
                .abqi-question-box {
                    padding: 10px 14px;
                    border-radius: 35px;
                }
                
                .abqi-question-icon {
                    width: 42px;
                    height: 42px;
                    font-size: 20px;
                }
                
                .abqi-question-content {
                    gap: 12px;
                }
                
                .abqi-question-text {
                    font-size: 13px;
                }
                
                .abqi-drawer-header {
                    padding: 14px;
                }
                
                .abqi-drawer-title {
                    font-size: 16px;
                }
                
                .abqi-drawer-content {
                    padding: 14px;
                }
                
                .abqi-answer-display {
                    font-size: 14px;
                    padding: 12px;
                }
            }
            
            /* Touch device optimizations */
            @media (hover: none) and (pointer: coarse) {
                /* Larger touch targets for mobile */
                .abqi-question-box {
                    min-height: 56px;
                    cursor: pointer;
                    -webkit-tap-highlight-color: transparent;
                }
                
                .abqi-question-box:active {
                    transform: scale(0.98);
                }
                
                .abqi-search-button,
                .abqi-drawer-close {
                    min-width: 48px;
                    min-height: 48px;
                }
                
                /* Prevent text selection on mobile */
                .abqi-question-text {
                    -webkit-user-select: none;
                    user-select: none;
                }
            }
            
            /* Dark theme support */
            @media (prefers-color-scheme: dark) {
                .abqi-section-header {
                    color: #e0e0e0;
                }
                
                .abqi-question-box.abqi-color-green {
                    background: #5a6b52;
                }
                
                .abqi-question-box.abqi-color-purple {
                    background: #63526b;
                }
                
                .abqi-question-box.abqi-color-blue {
                    background: #526b6b;
                }
                
                .abqi-question-box.abqi-color-green:hover {
                    background: #677a5e;
                }
                
                .abqi-question-box.abqi-color-purple:hover {
                    background: #725e7a;
                }
                
                .abqi-question-box.abqi-color-blue:hover {
                    background: #5e7a7a;
                }
                
                .abqi-question-icon {
                    background: rgba(255, 255, 255, 0.15);
                }
                
                .abqi-question-text {
                    color: #e0e0e0;
                }
                
                .abqi-drawer {
                    background: #212529;
                }
                
                .abqi-drawer-header {
                    background: linear-gradient(135deg, #343a40 0%, #495057 100%);
                    border-bottom-color: #495057;
                }
                
                .abqi-drawer-title {
                    color: #f8f9fa;
                }
                
                .abqi-drawer-close {
                    color: #adb5bd;
                }
                
                .abqi-drawer-close:hover {
                    background: #495057;
                    color: #f8f9fa;
                }
                
                .abqi-section-label {
                    color: #adb5bd;
                }
                
                .abqi-question-display {
                    background: linear-gradient(135deg, #1a365d 0%, #2c5282 100%);
                    color: #e2e8f0;
                    border-left-color: #3182ce;
                }
                
                .abqi-answer-display {
                    background: linear-gradient(135deg, #1a2e1a 0%, #2d5a2d 100%);
                    color: #e2e8f0;
                    border-left-color: #38a169;
                }
            }
            
            /* Smooth scrolling for drawer content */
            .abqi-drawer-content {
                scroll-behavior: smooth;
            }
            
            /* Loading state */
            .abqi-loading {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 12px;
                padding: 20px;
                color: #6c757d;
            }
            
            .abqi-loading-spinner {
                width: 24px;
                height: 24px;
                border: 3px solid rgba(33, 150, 243, 0.3);
                border-radius: 50%;
                border-top-color: #2196f3;
                animation: abqi-spin 1s ease-in-out infinite;
            }
            
            .abqi-loading-text {
                font-size: 14px;
                font-weight: 500;
            }
            
            /* Search result styles */
            .abqi-search-result {
                background: linear-gradient(135deg, #f8f9ff 0%, #e8f4fd 100%);
                border-left: 4px solid #2196f3;
                border-radius: 0 8px 8px 0;
                margin: -10px;
                padding: 20px;
            }
            
            .abqi-search-metadata {
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid rgba(33, 150, 243, 0.2);
            }
            
            .abqi-search-metadata small {
                color: #2196f3;
                font-weight: 500;
            }
            
            /* Unavailable state styles */
            .abqi-unavailable {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 12px;
                padding: 30px 20px;
                text-align: center;
                color: #6c757d;
            }
            
            .abqi-unavailable-icon {
                font-size: 32px;
                opacity: 0.7;
            }
            
            .abqi-unavailable-title {
                font-size: 18px;
                font-weight: 600;
                color: #495057;
            }
            
            .abqi-unavailable-message {
                font-size: 14px;
                line-height: 1.5;
                max-width: 300px;
            }
            
            .abqi-unavailable-state {
                background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
                border-left: 4px solid #ffc107;
                border-radius: 0 8px 8px 0;
                margin: -10px;
                padding: 20px;
            }
            
            /* Similar blogs styles */
            .abqi-similar-blogs-loading {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 12px;
                padding: 20px;
                color: #6c757d;
            }
            
            .abqi-similar-blogs-list {
                display: flex;
                flex-direction: column;
                gap: 16px;
            }
            
            .abqi-similar-blog-item {
                margin-bottom: 8px;
            }
            
            .abqi-similar-blog-title {
                color: #2196f3;
                text-decoration: none;
                font-weight: 500;
                font-size: 14px;
                line-height: 1.4;
                display: block;
                padding: 8px 0;
                border-bottom: 1px solid #f0f0f0;
                transition: color 0.2s ease;
            }
            
            .abqi-similar-blog-title:hover {
                color: #1976d2;
                text-decoration: underline;
            }
            
            .abqi-similar-blog-item:last-child .abqi-similar-blog-title {
                border-bottom: none;
            }
            
            .abqi-similar-blogs-empty,
            .abqi-similar-blogs-error {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 8px;
                padding: 20px;
                color: #6c757d;
                text-align: center;
            }
            
            .abqi-empty-icon,
            .abqi-error-icon {
                font-size: 24px;
                opacity: 0.7;
            }
            
            .abqi-empty-message,
            .abqi-error-message {
                font-size: 14px;
            }
            
            @keyframes abqi-spin {
                to { transform: rotate(360deg); }
            }
            
            /* CSS additions: */
            .abqi-questions-heading-wrap {
              display: flex;
              flex-direction: column;
              width: 100%;
              margin-bottom: 10px;
            }
            .abqi-section-heading {
              text-align: left;
              margin: 0;
              font-weight: bold;
              font-size: 20px;
            }
            .abqi-questions-underline {
              width: 90px;
              height: 12px;
              margin-top: 4px;
              margin-bottom: 8px;
              display: block;
            }
            .abqi-questions-underline img {
              display: block;
              width: 90px;
              height: 8px;
              pointer-events: none;
              user-select: none;
              margin-left: 0;
            }
            .abqi-divider-svg {
              display: block;
              width: 100%;
              margin: 0 0 14px 0;
              height: 1px;
              background: none;
              border: none;
              pointer-events: none;
              user-select: none;
            }
            .abqi-divider-svg svg {
              display: block;
              width: 100%;
              height: 1px;
            }
            .abqi-divider-svg {
              margin: 0 0 14px 0;
              padding: 0;
              background: none;
              border: none;
              pointer-events: none;
              user-select: none;
            }
        `;
    }
    
    /**
     * Clean up injected questions
     */
    cleanup() {
        // Close any open drawer
        if (this.currentDrawer) {
            this.closeDrawer();
        }
        
        // Remove injected elements from tracking array
        this.injectedElements.forEach(element => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
        });
        this.injectedElements = [];
        
        // Also do a comprehensive DOM cleanup to catch any orphaned elements
        const selectorsToClean = [
            '.abqi-question-container',
            '.abqi-question-box',
            '.abqi-drawer-overlay',
            '.abqi-section-header',
            '.abqi-answer-drawer'
        ];
        
        selectorsToClean.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                if (el.parentNode) {
                    el.parentNode.removeChild(el);
                }
            });
        });
        
        // Remove event listeners
        document.removeEventListener('keydown', this.handleEscapeKey);
        window.removeEventListener('resize', this.handleResize);
        
        this.isInitialized = false;
        this.log('Cleaned up injected questions');
    }
    
    /**
     * Destroy the injector
     */
    destroy() {
        this.cleanup();
        
        // Remove styles
        const styleElement = document.getElementById('abqi-styles');
        if (styleElement) {
            styleElement.remove();
        }
        
        this.log('AutoBlogQuestionInjector destroyed');
    }
    
    /**
     * Get statistics
     */
    getStatistics() {
        return {
            blogUrl: window.location.href,
            blogTitle: this.blogInfo?.title || 'Unknown',
            totalQuestions: this.questions.length,
            injectedQuestions: this.injectedElements.length,
            averageConfidence: this.questions.reduce((sum, q) => sum + (q.confidence_score || 0), 0) / this.questions.length,
            questionTypes: [...new Set(this.questions.map(q => q.question_type))],
            apiBaseUrl: this.options.apiBaseUrl
        };
    }
    
    /**
     * Utility function for delays
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Shuffle array using Fisher-Yates algorithm
     * @param {Array} array - Array to shuffle
     * @returns {Array} - Shuffled array (modifies original)
     */
    shuffleArray(array) {
        for (let i = array.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [array[i], array[j]] = [array[j], array[i]];
        }
        return array;
    }
    
    /**
     * Debug logging
     */
    /**
     * Fisher-Yates shuffle algorithm for randomizing arrays
     */
    shuffleArray(array) {
        const shuffled = [...array];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
    }
    
    log(...args) {
        if (this.options.debugMode) {
            console.log('[AutoBlogQuestionInjector]', ...args);
        }
    }
    
    createDividerSVG() {
        const divider = document.createElement('div');
        divider.className = 'abqi-divider-svg';
        divider.innerHTML = `<svg width="100%" height="1" viewBox="0 0 640 1" fill="none" xmlns="http://www.w3.org/2000/svg"><line x1="0" y1="0.5" x2="640" y2="0.5" stroke="#EAE6F7" stroke-width="1"/></svg>`;
        return divider;
    }
    
    // Add formatFigmaQuestion for bold style:
    formatFigmaQuestion(text) {
        if (!text) return '';
        // Fake bold for demo; replace <strong> substrings by <strong> markup
        let q = this.escapeHtml(text);
        // Basic bolding for words: quick breakfast, eating breakfast, etc.
        q = q.replace(/(quick breakfast|eating breakfast|breakfast)/gi,'<strong>$1</strong>');
        return q;
    }
}

// Make it globally available
window.AutoBlogQuestionInjector = AutoBlogQuestionInjector;

// Auto-initialize on page load (can be disabled by setting window.ABQI_AUTO_INIT = false)
if (typeof window !== 'undefined' && window.ABQI_AUTO_INIT !== false) {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            AutoBlogQuestionInjector.autoInit({ debugMode: false }).catch(error => {
                // Silently handle errors - keep blog untouched if API fails
                console.log('[AutoBlogQuestionInjector] Auto-init failed, blog kept untouched:', error?.message || error);
            });
        });
    } else {
        // DOM is already ready
        AutoBlogQuestionInjector.autoInit({ debugMode: false }).catch(error => {
            // Silently handle errors - keep blog untouched if API fails
            console.log('[AutoBlogQuestionInjector] Auto-init failed, blog kept untouched:', error?.message || error);
        });
    }
}

/**
 * USAGE EXAMPLES
 * 
 * 1. Auto-initialization (default behavior):
 *    // Just include the script - it will auto-detect and initialize
 *    <script src="auto-blog-question-injector.js"></script>
 * 
 * 2. Disable auto-initialization:
 *    <script>window.ABQI_AUTO_INIT = false;</script>
 *    <script src="auto-blog-question-injector.js"></script>
 * 
 * 3. Manual initialization:
 *    AutoBlogQuestionInjector.autoInit({ debugMode: true });
 * 
 * 4. Initialize with specific URL:
 *    AutoBlogQuestionInjector.init('https://medium.com/@user/blog-post');
 * 
 * 5. Custom API configuration:
 *    AutoBlogQuestionInjector.autoInit({
 *        apiBaseUrl: 'https://your-api.com/api/v1',
 *        debugMode: true,
 *        theme: 'dark'
 *    });
 */

// ===== Card CSS injection code (add once if not already present) =====
if (!document.getElementById('figma-question-card-styles')) {
  const style = document.createElement('style');
  style.id = 'figma-question-card-styles';
  style.textContent = `
    .figma-question-card {
      width: 320px;
      height: 230px;
      border-radius: 24px;
      background: #fff;
      box-shadow: 0 8px 40px rgba(134, 63, 250, 0.15);
      margin: 0 20px 34px 0;
      display: flex;
      flex-direction: column;
      position: relative;
      border: 2px solid #fff !important;
      overflow: hidden;
      transition: box-shadow 0.16s;
    }
    .figma-question-card:hover {
      box-shadow: 0 14px 52px rgba(134, 63, 250, 0.21);
    }
    .figma-qcard-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      align-items: flex-start;
      padding: 24px 24px 0 24px;
      background: transparent;
      min-height: 46px;
      height: 100%;
    }
    .figma-qcard-question {
      font-family: 'Inter','Sora',sans-serif;
      font-size: 22px;
      line-height: 32px;
      color: #131316;
      font-weight: 400;
      text-align: left;
      word-break: break-word;
      letter-spacing: 0px;
      margin-top: 0;
    }
    .figma-qcard-question strong {
      font-weight: 800;
      color: #131316;
      letter-spacing: 0.04em;
    }
    .figma-qcard-footer {
      background: #fff;
      border-bottom-left-radius: 24px;
      border-bottom-right-radius: 24px;
      border-top: 1.5px solid #efeef3;
      min-height: 68px;
      display: flex;
      align-items: center;
      padding: 0 24px 0 24px;
      gap: 10px;
      font-size: 16px;
      font-weight: 800;
      font-family: 'Inter','Sora',sans-serif;
      margin-top: auto;
    }
    .figma-qcard-explore {
      font-size: 18px;
      font-family: 'Inter','Sora',sans-serif;
      text-transform: uppercase;
      font-weight: 800;
      color: #131316;
      margin-right: 12px;
      letter-spacing: .02em;
      line-height: 68px;
      position: relative;
      padding-top: 2px;
    }
    .figma-qcard-arrow {
      display: flex;
      align-items: flex-end;
      height: 38px;
      position: relative;
      top: 4px;
    }
    .figma-qcard-arrow svg {
      display: block;
      width: 32px;
      height: 20px;
      margin-bottom: 0;
    }
    @media (max-width: 850px) {
      .figma-question-card { width: 96vw; min-width:220px; }
      .figma-qcard-content { padding-left:14px; padding-right:14px; }
      .figma-qcard-footer { padding-left:14px; padding-right:14px; min-height:50px; font-size: 15px; }
      .figma-qcard-explore { font-size: 16px; }
      .figma-qcard-arrow svg { width: 20px; height: 12px; }
    }
  `;
  document.head.appendChild(style);
}
// =============== END CSS INJECTION ===============

// ======= Replace main grid rendering with Figma card design =======

function renderQuestionsRow(questions) {
  const colors = ['#fef4e3', '#f9f6fe', '#fee3e3'];
  let rowHtml = '<div class="figma-questions-row">';
  questions.forEach((q, idx) => {
    // You might want to bold certain words dynamically for your question content.
    rowHtml += `
    <div class="figma-question-card">
      <div class="figma-qcard-topbar" style="background: ${colors[idx % colors.length]}"></div>
      <div class="figma-qcard-content">
        <div class="figma-qcard-question">
          <span>${escapeHtml(q.question || q.text)}</span>
        </div>
        <div class="figma-qcard-action-wrap">
          <span class="figma-qcard-explore">Explore</span>
          <span class="figma-qcard-arrow">
            <svg width="23" height="10" viewBox="0 0 23 10" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M2 5H20" stroke="#903FC0" stroke-width="2" stroke-linecap="round"/>
              <path d="M17 2L20 5L17 8" stroke="#903FC0" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </div>
      </div>
    </div>
    `;
  });
  rowHtml += '</div>';
  return rowHtml;
}

// Utility to escape for HTML
function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, function(m) {
    return {
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
    }[m];
  });
}

// ======= Replace the old rendering call/place with this: (pseudo-code example) =======
// document.querySelector('.your-questions-root').innerHTML = renderQuestionsRow(questionsFromAPI);
// ======= END RENDERING SNIPPET =======

// (You may need to wire this into your plugin/app if you do dynamic updates or filtering/scroll)

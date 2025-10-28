/**
 * Auto Blog Question Injector - Content Script
 * 
 * This script runs on all web pages and provides the interface
 * between the extension popup and the auto blog question injector.
 * 
 * Features:
 * - Auto-detects blog URLs and calls Blog Manager API
 * - Provides manual controls via extension popup
 * - Supports both API-driven and fallback question injection
 */

(function() {
    'use strict';
    
    // Global reference to the current injector instance
    window.currentAutoInjector = null;
    
    // Extension communication
    class ExtensionContentScript {
        constructor() {
            this.init();
        }
        
        init() {
            // Listen for messages from popup
            chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
                this.handleMessage(request, sender, sendResponse);
                return true; // Keep message channel open for async responses
            });
            
            // Add extension indicator (subtle)
            this.addExtensionIndicator();
        }
        
        async handleMessage(request, sender, sendResponse) {
            try {
                switch (request.action) {
                    case 'checkStatus':
                        sendResponse(await this.checkStatus());
                        break;
                        
                    case 'injectDefault':
                        sendResponse(await this.injectDefaultQuestions(request.settings));
                        break;
                        
                    case 'injectFallback':
                        sendResponse(await this.injectFallbackQuestions(request.settings));
                        break;
                        
                    case 'injectCustom':
                        sendResponse(await this.injectCustomQuestions(request.questionData, request.settings));
                        break;
                        
                    case 'removeQuestions':
                        sendResponse(await this.removeQuestions());
                        break;
                        
                    case 'getStats':
                        sendResponse(await this.getStats());
                        break;
                        
                    default:
                        sendResponse({ success: false, error: 'Unknown action' });
                }
            } catch (error) {
                console.error('Content script error:', error);
                sendResponse({ success: false, error: error.message });
            }
        }
        
        async checkStatus() {
            return {
                success: true,
                hasAutoInjector: typeof window.AutoBlogQuestionInjector !== 'undefined',
                hasQuestions: document.querySelectorAll('[data-question-id]').length > 0,
                questionCount: document.querySelectorAll('[data-question-id]').length,
                currentUrl: window.location.href,
                isAutoDetected: window.currentAutoInjector !== null,
                apiStatus: await this.checkAPIStatus()
            };
        }
        
        async checkAPIStatus() {
            try {
                // Updated to use Content Processing Service (2-service architecture)
                const response = await fetch('http://localhost:8005/health', { 
                    method: 'GET',
                    timeout: 3000 
                });
                return response.ok ? 'available' : 'error';
            } catch (error) {
                return 'unavailable';
            }
        }
        
        async injectDefaultQuestions(settings = {}) {
            try {
                // First try auto-detection with API
                const autoResult = await this.tryAutoDetection(settings);
                if (autoResult.success) {
                    return autoResult;
                }
                
                // If API fails (404 or other errors), keep blog untouched
                // Only inject fallback questions if explicitly requested via popup
                return {
                    success: false,
                    message: 'No questions available for this blog, keeping untouched',
                    source: 'none'
                };
                
            } catch (error) {
                console.error('Failed to inject questions:', error);
                return { success: false, error: error.message };
            }
        }
        
        async tryAutoDetection(settings = {}) {
            try {
                // Ensure AutoBlogQuestionInjector is available
                if (typeof window.AutoBlogQuestionInjector === 'undefined') {
                    throw new Error('AutoBlogQuestionInjector not loaded');
                }
                
                // Remove existing questions first
                await this.removeQuestions();
                
                // Try auto-initialization
                window.currentAutoInjector = await window.AutoBlogQuestionInjector.autoInit({
                    apiBaseUrl: settings.apiBaseUrl || 'http://localhost:8005/api/v1',
                    debugMode: settings.debugMode || false,
                    theme: settings.theme || 'default'
                });
                
                if (window.currentAutoInjector && window.currentAutoInjector.questions.length > 0) {
                    return {
                        success: true,
                        message: 'Questions loaded from API successfully',
                        questionCount: window.currentAutoInjector.questions.length,
                        source: 'api'
                    };
                } else {
                    throw new Error('No questions found via API');
                }
                
            } catch (error) {
                console.log('Auto-detection failed, will try fallback:', error.message);
                return { success: false, error: error.message };
            }
        }
        
        async injectFallbackQuestions(settings = {}) {
            try {
                // Ensure AutoBlogQuestionInjector is available
                if (typeof window.AutoBlogQuestionInjector === 'undefined') {
                    throw new Error('AutoBlogQuestionInjector not loaded');
                }
                
                // Create fallback questions suitable for any webpage
                const fallbackQuestions = this.generateFallbackQuestions(settings);
                
                // Create injector with fallback data
                window.currentAutoInjector = new window.AutoBlogQuestionInjector({
                    debugMode: settings.debugMode || false,
                    theme: settings.theme || 'default',
                    autoDetectUrl: false
                });
                
                // Manually set questions and inject
                window.currentAutoInjector.questions = fallbackQuestions.questions;
                window.currentAutoInjector.blogInfo = fallbackQuestions.blog_info;
                
                // Set up UI and inject
                window.currentAutoInjector.injectStyles();
                window.currentAutoInjector.setupEventListeners();
                await window.currentAutoInjector.injectAllQuestions();
                window.currentAutoInjector.isInitialized = true;
                
                return {
                    success: true,
                    message: 'Fallback questions injected successfully',
                    questionCount: fallbackQuestions.questions.length,
                    source: 'fallback'
                };
                
            } catch (error) {
                console.error('Failed to inject fallback questions:', error);
                return { success: false, error: error.message };
            }
        }
        
        async injectCustomQuestions(questionData, settings = {}) {
            try {
                // Ensure AutoBlogQuestionInjector is available
                if (typeof window.AutoBlogQuestionInjector === 'undefined') {
                    throw new Error('AutoBlogQuestionInjector not loaded');
                }
                
                // Validate and adapt question data to new format
                const adaptedData = this.adaptQuestionData(questionData);
                
                // Remove existing questions first
                await this.removeQuestions();
                
                // Create injector with custom data
                window.currentAutoInjector = new window.AutoBlogQuestionInjector({
                    debugMode: settings.debugMode || false,
                    theme: settings.theme || 'default',
                    autoDetectUrl: false
                });
                
                // Manually set questions and inject
                window.currentAutoInjector.questions = adaptedData.questions;
                window.currentAutoInjector.blogInfo = adaptedData.blog_info;
                
                // Set up UI and inject
                window.currentAutoInjector.injectStyles();
                window.currentAutoInjector.setupEventListeners();
                await window.currentAutoInjector.injectAllQuestions();
                window.currentAutoInjector.isInitialized = true;
                
                return {
                    success: true,
                    message: 'Custom questions injected successfully',
                    questionCount: adaptedData.questions.length,
                    source: 'custom'
                };
                
            } catch (error) {
                console.error('Failed to inject custom questions:', error);
                return { success: false, error: error.message };
            }
        }
        
        adaptQuestionData(oldData) {
            // Adapt old question format to new API format
            if (!oldData || !oldData.questions || !Array.isArray(oldData.questions)) {
                throw new Error('Invalid question data structure');
            }
            
            return {
                blog_info: {
                    blog_id: oldData.content_id || 'custom',
                    title: oldData.content_title || document.title,
                    url: oldData.content_url || window.location.href,
                    author: null,
                    published_date: null,
                    word_count: null,
                    source_domain: window.location.hostname
                },
                questions: oldData.questions.map((q, index) => ({
                    id: q.id || `custom_${index}`,
                    question: q.question,
                    answer: q.answer,
                    question_type: q.question_type || 'exploratory',
                    difficulty_level: q.metadata?.difficulty_level || 'intermediate',
                    question_order: index + 1,
                    confidence_score: q.confidence_score || 0.8,
                    estimated_answer_time: 30,
                    topic_area: 'general',
                    bloom_taxonomy_level: 'comprehension',
                    learning_objective: `Understanding concepts from question ${index + 1}`
                }))
            };
        }
        
        async removeQuestions() {
            try {
                // Destroy current auto injector
                if (window.currentAutoInjector && typeof window.currentAutoInjector.destroy === 'function') {
                    window.currentAutoInjector.destroy();
                    window.currentAutoInjector = null;
                }
                
                // Manual cleanup as fallback
                document.querySelectorAll('[data-question-id]').forEach(el => el.remove());
                document.querySelectorAll('.abqi-question-container').forEach(el => el.remove());
                document.querySelectorAll('.abqi-drawer-overlay').forEach(el => el.remove());
                document.querySelectorAll('.bqi-sidebar').forEach(el => el.remove());
                document.querySelectorAll('.bqi-drawer').forEach(el => el.remove());
                
                // Remove styles
                const styles = document.getElementById('abqi-styles');
                if (styles) styles.remove();
                const oldStyles = document.getElementById('bqi-styles');
                if (oldStyles) oldStyles.remove();
                
                return {
                    success: true,
                    message: 'Questions removed successfully'
                };
                
            } catch (error) {
                console.error('Failed to remove questions:', error);
                return { success: false, error: error.message };
            }
        }
        
        async getStats() {
            try {
                const questionElements = document.querySelectorAll('[data-question-id]');
                
                let stats = {
                    questionCount: questionElements.length,
                    averageConfidence: 0.85, // Default
                    contentTopic: document.title || 'Current Page',
                    placementStrategies: ['after_paragraphs'],
                    apiStatus: await this.checkAPIStatus(),
                    currentUrl: window.location.href,
                    source: 'unknown'
                };
                
                // Try to get stats from auto injector if available
                if (window.currentAutoInjector && typeof window.currentAutoInjector.getStatistics === 'function') {
                    const injectorStats = window.currentAutoInjector.getStatistics();
                    stats = { ...stats, ...injectorStats };
                    stats.source = 'api';
                } else if (questionElements.length > 0) {
                    stats.source = 'fallback';
                }
                
                return { success: true, stats };
                
            } catch (error) {
                console.error('Failed to get stats:', error);
                return { success: false, error: error.message };
            }
        }
        
        generateFallbackQuestions(settings = {}) {
            // Analyze the current page to generate contextual questions
            const pageTitle = document.title || 'Untitled Page';
            const pageContent = this.extractPageContent();
            const paragraphs = this.findParagraphs();
            
            return {
                blog_info: {
                    blog_id: `extension_${Date.now()}`,
                    title: pageTitle,
                    url: window.location.href,
                    author: null,
                    published_date: null,
                    word_count: pageContent.split(' ').length,
                    source_domain: window.location.hostname
                },
                questions: [
                    {
                        id: "ext_q1",
                        question: "What is the main purpose or message of this content?",
                        answer: "This question encourages readers to identify and articulate the core message or purpose of the content they're reading. It helps with comprehension and ensures readers understand the fundamental concepts being presented.",
                        question_type: "clarification",
                        difficulty_level: "intermediate",
                        question_order: 1,
                        confidence_score: 0.9,
                        estimated_answer_time: 30,
                        topic_area: "general",
                        bloom_taxonomy_level: "comprehension",
                        learning_objective: "Understanding the main purpose of content"
                    },
                    {
                        id: "ext_q2",
                        question: "How does this information relate to your existing knowledge or experience?",
                        answer: "This question helps readers make connections between new information and their prior knowledge or personal experiences. Making these connections enhances understanding, retention, and makes the content more personally relevant and meaningful.",
                        question_type: "practical",
                        difficulty_level: "intermediate",
                        question_order: 2,
                        confidence_score: 0.85,
                        estimated_answer_time: 45,
                        topic_area: "general",
                        bloom_taxonomy_level: "application",
                        learning_objective: "Connecting new information to existing knowledge"
                    },
                    {
                        id: "ext_q3",
                        question: "What questions or areas for further exploration does this content raise?",
                        answer: "This meta-cognitive question encourages readers to think beyond the current content and identify areas where they'd like to learn more. It promotes curiosity, critical thinking, and helps readers recognize the boundaries of their current understanding.",
                        question_type: "deeper_dive",
                        difficulty_level: "advanced",
                        question_order: 3,
                        confidence_score: 0.8,
                        estimated_answer_time: 60,
                        topic_area: "general",
                        bloom_taxonomy_level: "evaluation",
                        learning_objective: "Identifying areas for further exploration"
                    }
                ]
            };
        }
        
        extractPageContent() {
            // Try to get main content from common selectors
            const contentSelectors = [
                'article',
                'main',
                '.content',
                '.post-content',
                '.entry-content',
                '.article-content',
                '#content',
                '.main-content'
            ];
            
            for (const selector of contentSelectors) {
                const element = document.querySelector(selector);
                if (element) {
                    return element.textContent.trim();
                }
            }
            
            // Fallback to body content
            return document.body.textContent.trim();
        }
        
        findParagraphs() {
            // Find paragraphs in the main content area
            const contentSelectors = [
                'article p',
                'main p',
                '.content p',
                '.post-content p',
                '.entry-content p',
                '.article-content p',
                '#content p',
                '.main-content p',
                'p' // Fallback
            ];
            
            for (const selector of contentSelectors) {
                const paragraphs = document.querySelectorAll(selector);
                if (paragraphs.length > 0) {
                    return Array.from(paragraphs).filter(p => 
                        p.textContent.trim().length > 50 // Only substantial paragraphs
                    );
                }
            }
            
            return [];
        }
        
        extractKeywords(text) {
            // Simple keyword extraction
            const words = text.toLowerCase()
                .replace(/[^\w\s]/g, ' ')
                .split(/\s+/)
                .filter(word => word.length > 3);
            
            const wordCount = {};
            words.forEach(word => {
                wordCount[word] = (wordCount[word] || 0) + 1;
            });
            
            return Object.entries(wordCount)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10)
                .map(([word]) => word);
        }
        
        addExtensionIndicator() {
            // Add a subtle indicator that the extension is active
            if (document.getElementById('bqi-extension-indicator')) return;
            
            const indicator = document.createElement('div');
            indicator.id = 'bqi-extension-indicator';
            indicator.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                width: 8px;
                height: 8px;
                background: #007bff;
                border-radius: 50%;
                z-index: 999999;
                opacity: 0.3;
                transition: opacity 0.2s ease;
                pointer-events: none;
            `;
            
            // Show indicator briefly when extension is active
            document.body.appendChild(indicator);
            
            setTimeout(() => {
                if (indicator.parentNode) {
                    indicator.style.opacity = '0';
                    setTimeout(() => {
                        if (indicator.parentNode) {
                            indicator.parentNode.removeChild(indicator);
                        }
                    }, 2000);
                }
            }, 3000);
        }
    }
    
    // Initialize content script
    const contentScript = new ExtensionContentScript();
    
    // Add a global flag to indicate extension is loaded
    window.blogQuestionInjectorExtensionLoaded = true;
    
    // Auto-initialize on page load for supported blogs (only once)
    if (typeof window.AutoBlogQuestionInjector !== 'undefined' && !window._autoInitCalled) {
        window._autoInitCalled = true;
        
        // Wait for page to be fully loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                window.AutoBlogQuestionInjector.autoInit();
            });
        } else {
            // Page already loaded
            window.AutoBlogQuestionInjector.autoInit();
        }
    }
    
})();

/**
 * Blog Question Injector - Content Script
 * 
 * This script runs on all web pages and provides the interface
 * between the extension popup and the question injector.
 */

(function() {
    'use strict';
    
    // Global reference to the current injector instance
    window.currentBlogQuestionInjector = null;
    
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
                hasInjector: typeof window.BlogQuestionInjector !== 'undefined',
                hasQuestions: document.querySelectorAll('[data-question-id]').length > 0,
                questionCount: document.querySelectorAll('[data-question-id]').length
            };
        }
        
        async injectDefaultQuestions(settings = {}) {
            try {
                // Ensure BlogQuestionInjector is available
                if (typeof window.BlogQuestionInjector === 'undefined') {
                    throw new Error('BlogQuestionInjector not loaded');
                }
                
                // Remove existing questions first
                await this.removeQuestions();
                
                // Create default questions suitable for any webpage
                const defaultQuestions = this.generateDefaultQuestions(settings);
                
                // Inject questions
                window.currentBlogQuestionInjector = await window.BlogQuestionInjector.loadFromData(defaultQuestions, {
                    theme: settings.theme || 'default',
                    debugMode: settings.debugMode || false
                });
                
                return { 
                    success: true, 
                    message: 'Default questions injected successfully',
                    questionCount: defaultQuestions.questions.length
                };
                
            } catch (error) {
                console.error('Failed to inject default questions:', error);
                return { success: false, error: error.message };
            }
        }
        
        async injectCustomQuestions(questionData, settings = {}) {
            try {
                // Ensure BlogQuestionInjector is available
                if (typeof window.BlogQuestionInjector === 'undefined') {
                    throw new Error('BlogQuestionInjector not loaded');
                }
                
                // Validate question data
                if (!questionData || !questionData.questions || !Array.isArray(questionData.questions)) {
                    throw new Error('Invalid question data structure');
                }
                
                // Remove existing questions first
                await this.removeQuestions();
                
                // Inject custom questions
                window.currentBlogQuestionInjector = await window.BlogQuestionInjector.loadFromData(questionData, {
                    theme: settings.theme || 'default',
                    debugMode: settings.debugMode || false
                });
                
                return { 
                    success: true, 
                    message: 'Custom questions injected successfully',
                    questionCount: questionData.questions.length
                };
                
            } catch (error) {
                console.error('Failed to inject custom questions:', error);
                return { success: false, error: error.message };
            }
        }
        
        async removeQuestions() {
            try {
                // Destroy current injector
                if (window.currentBlogQuestionInjector && typeof window.currentBlogQuestionInjector.destroy === 'function') {
                    window.currentBlogQuestionInjector.destroy();
                    window.currentBlogQuestionInjector = null;
                }
                
                // Manual cleanup as fallback
                document.querySelectorAll('[data-question-id]').forEach(el => el.remove());
                document.querySelectorAll('.bqi-sidebar').forEach(el => el.remove());
                document.querySelectorAll('.bqi-drawer').forEach(el => el.remove());
                
                // Remove styles
                const styles = document.getElementById('bqi-styles');
                if (styles) styles.remove();
                
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
                    placementStrategies: []
                };
                
                // Try to get stats from injector if available
                if (window.currentBlogQuestionInjector && typeof window.currentBlogQuestionInjector.getStatistics === 'function') {
                    const injectorStats = window.currentBlogQuestionInjector.getStatistics();
                    stats = { ...stats, ...injectorStats };
                }
                
                // Analyze placement strategies from DOM
                const strategies = new Set();
                questionElements.forEach(el => {
                    if (el.classList.contains('bqi-question')) strategies.add('after_paragraph');
                    if (el.classList.contains('bqi-sidebar-question')) strategies.add('sidebar');
                    if (el.classList.contains('bqi-floating-question')) strategies.add('floating');
                    if (el.classList.contains('bqi-inline-highlight')) strategies.add('inline_highlight');
                });
                stats.placementStrategies = Array.from(strategies);
                
                return { success: true, stats };
                
            } catch (error) {
                console.error('Failed to get stats:', error);
                return { success: false, error: error.message };
            }
        }
        
        generateDefaultQuestions(settings = {}) {
            // Analyze the current page to generate contextual questions
            const pageTitle = document.title || 'Untitled Page';
            const pageContent = this.extractPageContent();
            const paragraphs = this.findParagraphs();
            
            return {
                "content_id": `extension_${Date.now()}`,
                "content_title": pageTitle,
                "content_url": window.location.href,
                "content_context": {
                    "topic": pageTitle,
                    "keywords": this.extractKeywords(pageContent),
                    "difficulty_level": "intermediate",
                    "content_type": "web_article",
                    "estimated_reading_time": Math.max(1, Math.floor(pageContent.split(' ').length / 200))
                },
                "questions": [
                    {
                        "id": "ext_q1",
                        "question": "What is the main purpose or message of this content?",
                        "answer": "This question encourages readers to identify and articulate the core message or purpose of the content they're reading. It helps with comprehension and ensures readers understand the fundamental concepts being presented.",
                        "question_type": "clarification",
                        "context": "Main content understanding",
                        "metadata": {
                            "placement_strategy": "after_paragraph",
                            "target_paragraph": {
                                "paragraph_index": 0,
                                "text_snippet": paragraphs[0]?.textContent.substring(0, 50) || "content",
                                "section_title": "Introduction"
                            },
                            "priority": 9,
                            "trigger_event": "scroll",
                            "animation": "fade_in",
                            "theme": settings.theme || "default"
                        },
                        "confidence_score": 0.9
                    },
                    {
                        "id": "ext_q2",
                        "question": "How does this information relate to your existing knowledge or experience?",
                        "answer": "This question helps readers make connections between new information and their prior knowledge or personal experiences. Making these connections enhances understanding, retention, and makes the content more personally relevant and meaningful.",
                        "question_type": "practical",
                        "context": "Personal connection",
                        "metadata": {
                            "placement_strategy": "sidebar",
                            "target_paragraph": {
                                "paragraph_index": Math.min(1, paragraphs.length - 1),
                                "text_snippet": paragraphs[1]?.textContent.substring(0, 50) || "content",
                                "section_title": "Content"
                            },
                            "priority": 8,
                            "trigger_event": "scroll",
                            "animation": "slide_up",
                            "theme": settings.theme || "default"
                        },
                        "confidence_score": 0.85
                    },
                    {
                        "id": "ext_q3",
                        "question": "What questions or areas for further exploration does this content raise?",
                        "answer": "This meta-cognitive question encourages readers to think beyond the current content and identify areas where they'd like to learn more. It promotes curiosity, critical thinking, and helps readers recognize the boundaries of their current understanding.",
                        "question_type": "deeper_dive",
                        "context": "Further exploration",
                        "metadata": {
                            "placement_strategy": "floating",
                            "target_paragraph": {
                                "paragraph_index": Math.min(2, paragraphs.length - 1),
                                "text_snippet": "exploration",
                                "section_title": "Exploration"
                            },
                            "priority": 7,
                            "trigger_event": "time",
                            "animation": "bounce",
                            "theme": settings.theme || "default"
                        },
                        "confidence_score": 0.8
                    }
                ],
                "total_questions": 3,
                "average_confidence": 0.85,
                "generation_timestamp": new Date().toISOString(),
                "llm_model": "extension_generated"
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
    new ExtensionContentScript();
    
    // Add a global flag to indicate extension is loaded
    window.blogQuestionInjectorExtensionLoaded = true;
    
})();

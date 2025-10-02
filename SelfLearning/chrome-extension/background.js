/**
 * Blog Question Injector - Background Script
 * 
 * Handles extension lifecycle, context menus, and cross-tab communication
 */

class ExtensionBackground {
    constructor() {
        this.init();
    }
    
    init() {
        // Set up extension event listeners
        chrome.runtime.onInstalled.addListener((details) => {
            this.handleInstalled(details);
        });
        
        chrome.action.onClicked.addListener((tab) => {
            this.handleActionClick(tab);
        });
        
        // Set up context menus
        this.setupContextMenus();
        
        // Handle context menu clicks (only if contextMenus API is available)
        if (chrome.contextMenus) {
            chrome.contextMenus.onClicked.addListener((info, tab) => {
                this.handleContextMenuClick(info, tab);
            });
        }
        
        // Handle messages from content scripts and popup
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            this.handleMessage(request, sender, sendResponse);
            return true; // Keep message channel open
        });
        
        // Handle tab updates
        chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
            this.handleTabUpdate(tabId, changeInfo, tab);
        });
    }
    
    handleInstalled(details) {
        console.log('Blog Question Injector installed:', details.reason);
        
        if (details.reason === 'install') {
            // First time installation
            this.showWelcomeNotification();
            this.openWelcomePage();
        } else if (details.reason === 'update') {
            // Extension updated
            console.log('Extension updated to version:', chrome.runtime.getManifest().version);
        }
    }
    
    handleActionClick(tab) {
        // This is called when the extension icon is clicked
        // The popup should open automatically, but we can handle fallbacks here
        console.log('Extension icon clicked for tab:', tab.id);
    }
    
    setupContextMenus() {
        // Check if contextMenus API is available
        if (!chrome.contextMenus) {
            console.log('Context menus not available');
            return;
        }

        try {
            // Remove existing menus first
            chrome.contextMenus.removeAll(() => {
                // Add context menu for quick injection
                chrome.contextMenus.create({
                    id: 'inject-questions',
                    title: 'Inject Questions Here',
                    contexts: ['page', 'selection'],
                    documentUrlPatterns: ['http://*/*', 'https://*/*']
                });
                
                chrome.contextMenus.create({
                    id: 'inject-questions-selection',
                    title: 'Generate Questions for Selection',
                    contexts: ['selection'],
                    documentUrlPatterns: ['http://*/*', 'https://*/*']
                });
                
                chrome.contextMenus.create({
                    id: 'separator1',
                    type: 'separator',
                    contexts: ['page', 'selection']
                });
                
                chrome.contextMenus.create({
                    id: 'remove-questions',
                    title: 'Remove All Questions',
                    contexts: ['page'],
                    documentUrlPatterns: ['http://*/*', 'https://*/*']
                });
            });
        } catch (error) {
            console.error('Failed to setup context menus:', error);
        }
    }
    
    async handleContextMenuClick(info, tab) {
        try {
            switch (info.menuItemId) {
                case 'inject-questions':
                    await this.injectQuestionsViaContext(tab);
                    break;
                    
                case 'inject-questions-selection':
                    await this.injectQuestionsForSelection(tab, info.selectionText);
                    break;
                    
                case 'remove-questions':
                    await this.removeQuestionsViaContext(tab);
                    break;
            }
        } catch (error) {
            console.error('Context menu action failed:', error);
            this.showNotification('Error', 'Failed to execute action: ' + error.message);
        }
    }
    
    async injectQuestionsViaContext(tab) {
        try {
            // First inject the question injector script
            await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                files: ['question-injector.js']
            });
            
            // Then inject default questions
            await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                func: () => {
                    // Generate default questions for the current page
                    const defaultQuestions = {
                        "content_id": `context_${Date.now()}`,
                        "content_title": document.title || 'Current Page',
                        "questions": [
                            {
                                "id": "ctx_q1",
                                "question": "What is the key takeaway from this content?",
                                "answer": "This question helps readers identify and summarize the most important information or insights from the content they're reading.",
                                "question_type": "clarification",
                                "context": "Key insights",
                                "metadata": {
                                    "placement_strategy": "after_paragraph",
                                    "target_paragraph": {
                                        "paragraph_index": 0,
                                        "text_snippet": "content",
                                        "section_title": "Main Content"
                                    },
                                    "priority": 9,
                                    "trigger_event": "scroll",
                                    "animation": "fade_in",
                                    "theme": "default"
                                },
                                "confidence_score": 0.9
                            }
                        ],
                        "total_questions": 1,
                        "average_confidence": 0.9
                    };
                    
                    return BlogQuestionInjector.loadFromData(defaultQuestions);
                }
            });
            
            this.showNotification('Success', 'Questions injected successfully!');
            
        } catch (error) {
            console.error('Failed to inject questions via context menu:', error);
            this.showNotification('Error', 'Failed to inject questions');
        }
    }
    
    async injectQuestionsForSelection(tab, selectionText) {
        if (!selectionText || selectionText.trim().length < 10) {
            this.showNotification('Error', 'Please select more text to generate questions');
            return;
        }
        
        try {
            // First inject the question injector script
            await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                files: ['question-injector.js']
            });
            
            // Generate questions based on selected text
            await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                func: (selectedText) => {
                    const selectionQuestions = {
                        "content_id": `selection_${Date.now()}`,
                        "content_title": `Selected Text: ${selectedText.substring(0, 50)}...`,
                        "questions": [
                            {
                                "id": "sel_q1",
                                "question": `What does this selected text mean: "${selectedText.substring(0, 100)}..."?`,
                                "answer": "This question encourages deeper analysis of the selected text, helping readers understand its meaning, context, and significance within the larger content.",
                                "question_type": "clarification",
                                "context": "Selected text analysis",
                                "metadata": {
                                    "placement_strategy": "floating",
                                    "target_paragraph": {
                                        "paragraph_index": 0,
                                        "text_snippet": selectedText.substring(0, 50),
                                        "section_title": "Selected Content"
                                    },
                                    "priority": 10,
                                    "trigger_event": "immediate",
                                    "animation": "bounce",
                                    "theme": "default"
                                },
                                "confidence_score": 0.95
                            }
                        ],
                        "total_questions": 1,
                        "average_confidence": 0.95
                    };
                    
                    return BlogQuestionInjector.loadFromData(selectionQuestions);
                },
                args: [selectionText]
            });
            
            this.showNotification('Success', 'Question generated for selected text!');
            
        } catch (error) {
            console.error('Failed to generate questions for selection:', error);
            this.showNotification('Error', 'Failed to generate questions for selection');
        }
    }
    
    async removeQuestionsViaContext(tab) {
        try {
            await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                func: () => {
                    // Remove all question elements
                    document.querySelectorAll('[data-question-id]').forEach(el => el.remove());
                    document.querySelectorAll('.bqi-sidebar').forEach(el => el.remove());
                    document.querySelectorAll('.bqi-drawer').forEach(el => el.remove());
                    
                    // Remove styles
                    const styles = document.getElementById('bqi-styles');
                    if (styles) styles.remove();
                    
                    return true;
                }
            });
            
            this.showNotification('Success', 'All questions removed!');
            
        } catch (error) {
            console.error('Failed to remove questions via context menu:', error);
            this.showNotification('Error', 'Failed to remove questions');
        }
    }
    
    handleMessage(request, sender, sendResponse) {
        // Handle messages from content scripts and popup
        switch (request.action) {
            case 'showNotification':
                this.showNotification(request.title, request.message);
                sendResponse({ success: true });
                break;
                
            case 'getExtensionInfo':
                sendResponse({
                    success: true,
                    info: {
                        version: chrome.runtime.getManifest().version,
                        name: chrome.runtime.getManifest().name
                    }
                });
                break;
                
            default:
                sendResponse({ success: false, error: 'Unknown action' });
        }
    }
    
    handleTabUpdate(tabId, changeInfo, tab) {
        // Handle tab navigation - could be used to persist questions across page loads
        if (changeInfo.status === 'complete' && tab.url) {
            // Page fully loaded
            console.log('Page loaded:', tab.url);
        }
    }
    
    showNotification(title, message) {
        // Show browser notification (simplified)
        console.log(`Notification: ${title} - ${message}`);
        // Note: Notifications require additional permissions
        // For now, we'll just log to console
    }
    
    showWelcomeNotification() {
        this.showNotification(
            'Blog Question Injector Installed!',
            'Click the extension icon to start injecting questions into any webpage.'
        );
    }
    
    openWelcomePage() {
        // Could open a welcome/onboarding page
        // chrome.tabs.create({ url: 'welcome.html' });
    }
}

// Initialize background script
new ExtensionBackground();

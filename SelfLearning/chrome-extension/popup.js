/**
 * Blog Question Injector - Chrome Extension Popup
 * 
 * Handles the popup interface for injecting questions into websites
 */

class ExtensionPopup {
    constructor() {
        this.currentTab = null;
        this.injectorActive = false;
        this.customQuestionData = null;
        
        this.init();
    }
    
    async init() {
        // Get current tab
        await this.getCurrentTab();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Check if injector is already active
        await this.checkInjectorStatus();
        
        // Load saved settings
        await this.loadSettings();
    }
    
    async getCurrentTab() {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            this.currentTab = tab;
            
            if (!tab) {
                console.error('No active tab found');
                return;
            }
            
            console.log('Current tab:', tab.url);
        } catch (error) {
            console.error('Failed to get current tab:', error);
            this.currentTab = null;
        }
    }
    
    setupEventListeners() {
        // Inject default questions
        document.getElementById('injectDefault').addEventListener('click', () => {
            this.injectDefaultQuestions();
        });
        
        // Remove questions
        document.getElementById('removeQuestions').addEventListener('click', () => {
            this.removeQuestions();
        });
        
        // File upload
        document.getElementById('jsonFile').addEventListener('change', (e) => {
            this.handleFileUpload(e);
        });
        
        // Inject custom questions
        document.getElementById('injectCustom').addEventListener('click', () => {
            this.injectCustomQuestions();
        });
        
        // Settings changes
        document.getElementById('theme').addEventListener('change', () => {
            this.saveSettings();
        });
        
        document.getElementById('debugMode').addEventListener('change', () => {
            this.saveSettings();
        });
    }
    
    async checkInjectorStatus() {
        try {
            // Check if we have a valid tab
            if (!this.currentTab || !this.currentTab.id) {
                this.updateStatus(false, false, 'No active tab found');
                return;
            }

            // Check if the URL is supported (not chrome:// or extension pages)
            if (this.currentTab.url && (
                this.currentTab.url.startsWith('chrome://') ||
                this.currentTab.url.startsWith('chrome-extension://') ||
                this.currentTab.url.startsWith('moz-extension://') ||
                this.currentTab.url.startsWith('edge://') ||
                this.currentTab.url.startsWith('about:')
            )) {
                this.updateStatus(false, false, 'Cannot inject on this page type');
                return;
            }

            const results = await chrome.scripting.executeScript({
                target: { tabId: this.currentTab.id },
                func: () => {
                    try {
                        return {
                            hasInjector: typeof window.SimpleBlogQuestionInjector !== 'undefined',
                            hasQuestions: document.querySelectorAll('[data-question-id]').length > 0,
                            questionCount: document.querySelectorAll('[data-question-id]').length,
                            url: window.location.href
                        };
                    } catch (e) {
                        return {
                            hasInjector: false,
                            hasQuestions: false,
                            questionCount: 0,
                            error: e.message
                        };
                    }
                }
            });
            
            const status = results[0].result;
            
            if (status.error) {
                this.updateStatus(false, false, `Script error: ${status.error}`);
            } else {
                this.updateStatus(status.hasInjector, status.hasQuestions);
            }
            
        } catch (error) {
            console.error('Failed to check injector status:', error);
            
            // Provide more specific error messages
            let errorMessage = 'Error checking status';
            if (error.message.includes('Cannot access')) {
                errorMessage = 'Cannot access this page (try a regular website)';
            } else if (error.message.includes('activeTab')) {
                errorMessage = 'Permission denied (try refreshing the page)';
            } else if (error.message.includes('Tabs cannot be edited')) {
                errorMessage = 'Cannot modify this type of page';
            }
            
            this.updateStatus(false, false, errorMessage);
        }
    }
    
    updateStatus(hasInjector, hasQuestions, errorMessage = null) {
        const statusEl = document.getElementById('status');
        const removeBtn = document.getElementById('removeQuestions');
        const statsSection = document.getElementById('statsSection');
        
        if (errorMessage) {
            statusEl.className = 'status error';
            statusEl.textContent = errorMessage;
            removeBtn.disabled = true;
            statsSection.style.display = 'none';
            
            // Add debug info for troubleshooting
            if (this.currentTab) {
                console.log('Debug info - Tab URL:', this.currentTab.url);
                console.log('Debug info - Tab ID:', this.currentTab.id);
            }
        } else if (hasQuestions) {
            statusEl.className = 'status active';
            statusEl.textContent = '✅ Questions active on this page';
            removeBtn.disabled = false;
            statsSection.style.display = 'block';
            this.injectorActive = true;
            this.updateStats();
        } else if (hasInjector) {
            statusEl.className = 'status inactive';
            statusEl.textContent = '⚡ Injector loaded, ready to add questions';
            removeBtn.disabled = true;
            statsSection.style.display = 'none';
            this.injectorActive = false;
        } else {
            statusEl.className = 'status inactive';
            statusEl.textContent = '📋 Ready to inject questions';
            removeBtn.disabled = true;
            statsSection.style.display = 'none';
            this.injectorActive = false;
        }
    }
    
    async injectDefaultQuestions() {
        const button = document.getElementById('injectDefault');
        const originalText = button.innerHTML;
        
        try {
            button.innerHTML = '<div class="loading"></div> Injecting...';
            button.disabled = true;
            
            // First, inject the question injector script
            await this.injectQuestionInjectorScript();
            
            // Clean up any existing questions
            await this.cleanupExistingQuestions();
            
            // Then inject default questions
            const settingsString = JSON.stringify(this.getSettings());
            
            const results = await chrome.scripting.executeScript({
                target: { tabId: this.currentTab.id },
                func: (settingsStr) => {
                    return new Promise((resolve) => {
                        try {
                            // Parse settings
                            const settings = JSON.parse(settingsStr);
                            
                            // Check if SimpleBlogQuestionInjector is available
                            if (typeof window.SimpleBlogQuestionInjector === 'undefined') {
                                resolve({ success: false, error: 'SimpleBlogQuestionInjector not loaded' });
                                return;
                            }

                            // Default sample questions for testing
                            const defaultQuestions = {
                                "content_id": "demo_content",
                                "content_title": "Demo Content",
                                "questions": [
                                    {
                                        "id": "demo_q1",
                                        "question": "What is the main topic of this content?",
                                        "answer": "This is a demonstration question that helps readers engage with the content by encouraging them to think about the main themes and concepts presented. It's designed to enhance comprehension and retention.",
                                        "question_type": "clarification",
                                        "context": "Main content area",
                                        "metadata": {
                                            "placement_strategy": "after_paragraph",
                                            "target_paragraph": {
                                                "paragraph_index": 0,
                                                "text_snippet": "first paragraph",
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
                                        "id": "demo_q2",
                                        "question": "How can you apply this information in practice?",
                                        "answer": "This practical question encourages readers to think about real-world applications of the content. It helps bridge the gap between theoretical knowledge and practical implementation, making the learning experience more meaningful and actionable.",
                                        "question_type": "practical",
                                        "context": "Content application",
                                        "metadata": {
                                            "placement_strategy": "sidebar",
                                            "target_paragraph": {
                                                "paragraph_index": 1,
                                                "text_snippet": "second paragraph",
                                                "section_title": "Content"
                                            },
                                            "priority": 8,
                                            "trigger_event": "scroll",
                                            "animation": "slide_up",
                                            "theme": settings.theme || "default"
                                        },
                                        "confidence_score": 0.85
                                    }
                                ],
                                "total_questions": 2,
                                "average_confidence": 0.875
                            };
                            
                            // Initialize with default questions
                            window.SimpleBlogQuestionInjector.loadFromData(defaultQuestions, {
                                theme: settings.theme || 'default',
                                debugMode: settings.debugMode || false
                            }).then(() => {
                                resolve({ success: true });
                            }).catch(error => {
                                resolve({ success: false, error: error.message });
                            });
                            
                        } catch (error) {
                            resolve({ success: false, error: error.message });
                        }
                    });
                },
                args: [settingsString]
            });
            
            const result = results[0].result;
            
            // Handle null or undefined results
            if (!result) {
                throw new Error('Script execution returned no result');
            }
            
            if (result.success) {
                this.updateStatus(true, true);
                this.showMessage('✅ Default questions injected successfully!');
            } else {
                throw new Error(result.error || 'Unknown error occurred');
            }
            
        } catch (error) {
            console.error('Failed to inject default questions:', error);
            this.showMessage('❌ Failed to inject questions: ' + error.message, 'error');
        } finally {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }
    
    async injectCustomQuestions() {
        if (!this.customQuestionData) {
            this.showMessage('❌ Please upload a JSON file first', 'error');
            return;
        }
        
        const button = document.getElementById('injectCustom');
        const originalText = button.innerHTML;
        
        try {
            button.innerHTML = '<div class="loading"></div> Injecting...';
            button.disabled = true;
            
            // First, inject the question injector script
            await this.injectQuestionInjectorScript();
            
            // Clean up any existing questions
            await this.cleanupExistingQuestions();
            
            // Then inject custom questions
            const questionDataString = JSON.stringify(this.customQuestionData);
            const settingsString = JSON.stringify(this.getSettings());
            
            const results = await chrome.scripting.executeScript({
                target: { tabId: this.currentTab.id },
                func: (questionDataStr, settingsStr) => {
                    return new Promise((resolve) => {
                        try {
                            // Parse the data strings
                            const questionData = JSON.parse(questionDataStr);
                            const settings = JSON.parse(settingsStr);
                            
                            // Validate inputs first
                            if (!questionData) {
                                resolve({ success: false, error: 'No question data provided' });
                                return;
                            }

                            if (!settings) {
                                resolve({ success: false, error: 'No settings provided' });
                                return;
                            }

                            // Check if SimpleBlogQuestionInjector is available
                            if (typeof window.SimpleBlogQuestionInjector === 'undefined') {
                                resolve({ success: false, error: 'SimpleBlogQuestionInjector not loaded' });
                                return;
                            }

                            // Validate question data structure
                            if (!questionData.questions || !Array.isArray(questionData.questions)) {
                                resolve({ success: false, error: 'Invalid question data: missing questions array' });
                                return;
                            }

                            if (questionData.questions.length === 0) {
                                resolve({ success: false, error: 'No questions found in data' });
                                return;
                            }

                            // Ensure we have a clean data object and fix placement issues
                            const cleanData = {
                                content_id: questionData.content_id || 'custom_content',
                                content_title: questionData.content_title || 'Custom Content',
                                content_url: questionData.content_url || null,
                                content_context: questionData.content_context || {},
                                questions: questionData.questions.map((q, index) => {
                                    // Fix common placement issues
                                    const normalizedQuestion = { ...q };
                                    
                                    // If all questions target paragraph 0, spread them out
                                    if (q.metadata && q.metadata.target_paragraph && q.metadata.target_paragraph.paragraph_index === 0) {
                                        normalizedQuestion.metadata = {
                                            ...q.metadata,
                                            target_paragraph: {
                                                ...q.metadata.target_paragraph,
                                                paragraph_index: Math.min(index + 1, 10) // Spread questions across first 10 paragraphs
                                            }
                                        };
                                    }
                                    
                                    // Ensure we have fallback placement strategies
                                    if (!normalizedQuestion.metadata || !normalizedQuestion.metadata.placement_strategy) {
                                        normalizedQuestion.metadata = {
                                            ...normalizedQuestion.metadata,
                                            placement_strategy: index % 2 === 0 ? 'after_paragraph' : 'floating',
                                            target_paragraph: {
                                                paragraph_index: index + 1,
                                                paragraph_id: null,
                                                paragraph_class: null
                                            }
                                        };
                                    }
                                    
                                    return normalizedQuestion;
                                }),
                                total_questions: questionData.total_questions || questionData.questions.length,
                                average_confidence: questionData.average_confidence || 0.5
                            };

                            // Load the questions
                            window.SimpleBlogQuestionInjector.loadFromData(cleanData, {
                                theme: settings.theme || 'default',
                                debugMode: true // Always enable debug for troubleshooting
                            }).then(() => {
                                // Check if questions were actually injected
                                setTimeout(() => {
                                    const injectedQuestions = document.querySelectorAll('[data-question-id]');
                                    console.log('Questions found in DOM after injection:', injectedQuestions.length);
                                    
                                    if (injectedQuestions.length === 0) {
                                        console.warn('No questions found in DOM. Checking page structure...');
                                        const paragraphs = document.querySelectorAll('p');
                                        console.log('Total paragraphs found on page:', paragraphs.length);
                                        
                                        if (paragraphs.length > 0) {
                                            console.log('First few paragraphs:', Array.from(paragraphs).slice(0, 3).map(p => p.textContent.substring(0, 100)));
                                        }
                                        
                                        // Try to force floating questions if no paragraphs worked
                                        if (paragraphs.length === 0 || injectedQuestions.length === 0) {
                                            console.log('Trying to force floating questions...');
                                            const floatingData = {
                                                ...cleanData,
                                                questions: cleanData.questions.slice(0, 3).map((q, index) => ({
                                                    ...q,
                                                    metadata: {
                                                        ...q.metadata,
                                                        placement_strategy: 'floating',
                                                        target_paragraph: null
                                                    }
                                                }))
                                            };
                                            
                                            window.SimpleBlogQuestionInjector.loadFromData(floatingData, {
                                                theme: settings.theme || 'default',
                                                debugMode: true
                                            });
                                        }
                                    }
                                }, 1000);
                                
                                resolve({ 
                                    success: true, 
                                    message: `Loaded ${cleanData.questions.length} questions`,
                                    questionsData: cleanData.questions.map(q => ({
                                        id: q.id,
                                        placement: q.metadata.placement_strategy,
                                        paragraphIndex: q.metadata.target_paragraph.paragraph_index
                                    }))
                                });
                            }).catch(error => {
                                resolve({ success: false, error: `Failed to load questions: ${error.message}` });
                            });
                            
                        } catch (error) {
                            resolve({ success: false, error: `Script error: ${error.message}` });
                        }
                    });
                },
                args: [questionDataString, settingsString]
            });
            
            const result = results[0].result;
            
            // Handle null or undefined results
            if (!result) {
                throw new Error('Script execution returned no result');
            }
            
            if (result.success) {
                this.updateStatus(true, true);
                this.showMessage('✅ Custom questions injected successfully!');
            } else {
                throw new Error(result.error || 'Unknown error occurred');
            }
            
        } catch (error) {
            console.error('Failed to inject custom questions:', error);
            this.showMessage('❌ Failed to inject questions: ' + error.message, 'error');
        } finally {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }
    
    async removeQuestions() {
        const button = document.getElementById('removeQuestions');
        const originalText = button.innerHTML;
        
        try {
            button.innerHTML = '<div class="loading"></div> Removing...';
            button.disabled = true;
            
            await chrome.scripting.executeScript({
                target: { tabId: this.currentTab.id },
                func: () => {
                    // Remove all question elements
                    document.querySelectorAll('[data-question-id]').forEach(el => el.remove());
                    document.querySelectorAll('.bqi-sidebar').forEach(el => el.remove());
                    document.querySelectorAll('.bqi-drawer').forEach(el => el.remove());
                    
                    // Remove styles
                    const styles = document.getElementById('bqi-styles');
                    if (styles) styles.remove();
                    
                    return { success: true };
                }
            });
            
            this.updateStatus(false, false);
            this.showMessage('✅ Questions removed successfully!');
            
        } catch (error) {
            console.error('Failed to remove questions:', error);
            this.showMessage('❌ Failed to remove questions: ' + error.message, 'error');
        } finally {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    }
    
    async injectQuestionInjectorScript() {
        // Check if the script is already loaded to avoid re-injection
        const results = await chrome.scripting.executeScript({
            target: { tabId: this.currentTab.id },
            func: () => {
                return typeof window.SimpleBlogQuestionInjector !== 'undefined';
            }
        });
        
        const isAlreadyLoaded = results[0].result;
        
        if (!isAlreadyLoaded) {
            // Inject the question injector script only if not already present
            await chrome.scripting.executeScript({
                target: { tabId: this.currentTab.id },
                files: ['simple-question-injector.js']
            });
        }
    }
    
    async cleanupExistingQuestions() {
        // Remove any existing questions and injector instances
        await chrome.scripting.executeScript({
            target: { tabId: this.currentTab.id },
            func: () => {
                // Destroy existing injector if it exists
                if (window.currentSimpleBlogQuestionInjector && typeof window.currentSimpleBlogQuestionInjector.destroy === 'function') {
                    window.currentSimpleBlogQuestionInjector.destroy();
                    window.currentSimpleBlogQuestionInjector = null;
                }
                
                // Manual cleanup as fallback
                document.querySelectorAll('[data-question-id]').forEach(el => el.remove());
                document.querySelectorAll('.bqi-sidebar').forEach(el => el.remove());
                document.querySelectorAll('.bqi-drawer').forEach(el => el.remove());
                
                // Remove styles (but keep them if we're going to inject new questions)
                // const styles = document.getElementById('bqi-styles');
                // if (styles) styles.remove();
                
                return true;
            }
        });
    }
    
    // Script functions to run in the content context
    injectDefaultQuestionsScript(settings) {
        return new Promise((resolve) => {
            try {
                // Check if SimpleBlogQuestionInjector is available
                if (typeof window.SimpleBlogQuestionInjector === 'undefined') {
                    resolve({ success: false, error: 'SimpleBlogQuestionInjector not loaded' });
                    return;
                }

                // Default sample questions for testing
                const defaultQuestions = {
                    "content_id": "demo_content",
                    "content_title": "Demo Content",
                    "questions": [
                        {
                            "id": "demo_q1",
                            "question": "What is the main topic of this content?",
                            "answer": "This is a demonstration question that helps readers engage with the content by encouraging them to think about the main themes and concepts presented. It's designed to enhance comprehension and retention.",
                            "question_type": "clarification",
                            "context": "Main content area",
                            "metadata": {
                                "placement_strategy": "after_paragraph",
                                "target_paragraph": {
                                    "paragraph_index": 0,
                                    "text_snippet": "first paragraph",
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
                            "id": "demo_q2",
                            "question": "How can you apply this information in practice?",
                            "answer": "This practical question encourages readers to think about real-world applications of the content. It helps bridge the gap between theoretical knowledge and practical implementation, making the learning experience more meaningful and actionable.",
                            "question_type": "practical",
                            "context": "Content application",
                            "metadata": {
                                "placement_strategy": "sidebar",
                                "target_paragraph": {
                                    "paragraph_index": 1,
                                    "text_snippet": "second paragraph",
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
                            "id": "demo_q3",
                            "question": "What questions does this raise for further exploration?",
                            "answer": "This meta-cognitive question helps readers identify areas for deeper investigation. It promotes critical thinking and encourages continuous learning by helping readers recognize what they don't yet know or understand fully.",
                            "question_type": "deeper_dive",
                            "context": "Further exploration",
                            "metadata": {
                                "placement_strategy": "floating",
                                "target_paragraph": {
                                    "paragraph_index": 2,
                                    "text_snippet": "content",
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
                    "average_confidence": 0.85
                };
                
                // Initialize with default questions
                window.SimpleBlogQuestionInjector.loadFromData(defaultQuestions, {
                    theme: settings.theme || 'default',
                    debugMode: settings.debugMode || false
                }).then(() => {
                    resolve({ success: true });
                }).catch(error => {
                    resolve({ success: false, error: error.message });
                });
                
            } catch (error) {
                resolve({ success: false, error: error.message });
            }
        });
    }
    
    injectCustomQuestionsScript(questionData, settings) {
        return new Promise((resolve) => {
            try {
                // Validate inputs first
                if (!questionData) {
                    resolve({ success: false, error: 'No question data provided' });
                    return;
                }

                if (!settings) {
                    resolve({ success: false, error: 'No settings provided' });
                    return;
                }

                // Check if SimpleBlogQuestionInjector is available
                if (typeof window.SimpleBlogQuestionInjector === 'undefined') {
                    resolve({ success: false, error: 'SimpleBlogQuestionInjector not loaded' });
                    return;
                }

                // Validate question data structure
                if (!questionData.questions || !Array.isArray(questionData.questions)) {
                    resolve({ success: false, error: 'Invalid question data: missing questions array' });
                    return;
                }

                if (questionData.questions.length === 0) {
                    resolve({ success: false, error: 'No questions found in data' });
                    return;
                }

                // Ensure we have a clean data object
                const cleanData = {
                    content_id: questionData.content_id || 'custom_content',
                    content_title: questionData.content_title || 'Custom Content',
                    content_url: questionData.content_url || null,
                    content_context: questionData.content_context || {},
                    questions: questionData.questions,
                    total_questions: questionData.total_questions || questionData.questions.length,
                    average_confidence: questionData.average_confidence || 0.5
                };

                // Load the questions
                window.SimpleBlogQuestionInjector.loadFromData(cleanData, {
                    theme: settings.theme || 'default',
                    debugMode: settings.debugMode || false
                }).then(() => {
                    resolve({ success: true, message: `Loaded ${cleanData.questions.length} questions` });
                }).catch(error => {
                    resolve({ success: false, error: `Failed to load questions: ${error.message}` });
                });
                
            } catch (error) {
                resolve({ success: false, error: `Script error: ${error.message}` });
            }
        });
    }
    
    async updateStats() {
        try {
            const results = await chrome.scripting.executeScript({
                target: { tabId: this.currentTab.id },
                func: () => {
                    const questions = document.querySelectorAll('[data-question-id]');
                    return {
                        count: questions.length,
                        // Try to get stats from injector if available
                        hasStats: typeof window.currentSimpleBlogQuestionInjector !== 'undefined'
                    };
                }
            });
            
            const stats = results[0].result;
            
            document.getElementById('questionsCount').textContent = stats.count;
            document.getElementById('avgConfidence').textContent = '85%'; // Default
            document.getElementById('contentTopic').textContent = 'Current Page';
            
        } catch (error) {
            console.error('Failed to update stats:', error);
        }
    }
    
    handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        if (!file.name.endsWith('.json')) {
            this.showMessage('❌ Please select a JSON file', 'error');
            return;
        }
        
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const rawData = e.target.result;
                
                // Validate that we have content
                if (!rawData || rawData.trim().length === 0) {
                    throw new Error('File is empty');
                }
                
                // Parse JSON
                let parsedData;
                try {
                    parsedData = JSON.parse(rawData);
                } catch (parseError) {
                    throw new Error('Invalid JSON format: ' + parseError.message);
                }
                
                // Validate the JSON structure
                if (!parsedData || typeof parsedData !== 'object') {
                    throw new Error('JSON must be an object');
                }
                
                if (!parsedData.questions || !Array.isArray(parsedData.questions)) {
                    throw new Error('Invalid JSON structure: missing questions array');
                }
                
                if (parsedData.questions.length === 0) {
                    throw new Error('No questions found in file');
                }
                
                // Normalize the JSON structure to match what the injector expects
                this.customQuestionData = this.normalizeQuestionData(parsedData);
                
                // Validate normalized data
                if (!this.customQuestionData || !this.customQuestionData.questions) {
                    throw new Error('Failed to normalize question data');
                }
                
                document.getElementById('injectCustom').disabled = false;
                this.showMessage(`✅ Loaded ${this.customQuestionData.questions.length} questions from ${file.name}`);
                
            } catch (error) {
                console.error('Failed to process JSON file:', error);
                this.showMessage('❌ Failed to load file: ' + error.message, 'error');
                this.customQuestionData = null;
                document.getElementById('injectCustom').disabled = true;
            }
        };
        
        reader.readAsText(file);
    }
    
    getSettings() {
        return {
            theme: document.getElementById('theme').value,
            debugMode: document.getElementById('debugMode').checked
        };
    }
    
    async loadSettings() {
        try {
            const result = await chrome.storage.sync.get(['theme', 'debugMode']);
            
            if (result.theme) {
                document.getElementById('theme').value = result.theme;
            }
            
            if (result.debugMode !== undefined) {
                document.getElementById('debugMode').checked = result.debugMode;
            }
            
        } catch (error) {
            console.error('Failed to load settings:', error);
        }
    }
    
    async saveSettings() {
        try {
            const settings = this.getSettings();
            await chrome.storage.sync.set(settings);
            
        } catch (error) {
            console.error('Failed to save settings:', error);
        }
    }
    
    normalizeQuestionData(data) {
        // Create a normalized version that matches what the injector expects
        const normalized = {
            content_id: data.content_id || `content_${Date.now()}`,
            content_title: data.content_title || 'Imported Content',
            content_url: data.content_url || null,
            content_context: {
                topic: data.content_context?.topic || data.content_title || 'Imported Content',
                keywords: data.content_context?.keywords || [],
                difficulty_level: data.content_context?.difficulty_level || 'intermediate',
                content_type: data.content_context?.content_type || 'article',
                estimated_reading_time: data.content_context?.estimated_reading_time || 5
            },
            questions: data.questions.map((q, index) => ({
                id: q.id || `q${index + 1}`,
                question: q.question,
                answer: q.answer,
                question_type: q.question_type || 'clarification',
                context: q.context || '',
                metadata: {
                    placement_strategy: q.metadata?.placement_strategy || 'after_paragraph',
                    target_paragraph: {
                        paragraph_index: q.metadata?.target_paragraph?.paragraph_index || 0,
                        text_snippet: q.metadata?.target_paragraph?.text_snippet || 'content',
                        section_title: q.metadata?.target_paragraph?.section_title || null
                    },
                    priority: q.metadata?.priority || 5,
                    trigger_event: q.metadata?.trigger_event || 'scroll',
                    animation: q.metadata?.animation || 'fade_in',
                    theme: q.metadata?.theme || 'default'
                },
                confidence_score: q.confidence_score || 0.5
            })),
            total_questions: data.total_questions || data.questions.length,
            average_confidence: data.average_confidence || 0.5,
            generation_timestamp: data.generation_timestamp || new Date().toISOString(),
            llm_model: data.llm_model || 'unknown'
        };
        
        console.log('Normalized question data:', normalized);
        return normalized;
    }

    showMessage(message, type = 'success') {
        const statusEl = document.getElementById('status');
        const originalClass = statusEl.className;
        const originalText = statusEl.textContent;
        
        statusEl.className = `status ${type === 'error' ? 'error' : 'active'}`;
        statusEl.textContent = message;
        
        setTimeout(() => {
            statusEl.className = originalClass;
            statusEl.textContent = originalText;
        }, 3000);
    }
}

// Initialize popup when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ExtensionPopup();
});

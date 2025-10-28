// Configuration for Chrome Extension
const EXTENSION_CONFIG = {
    apiBaseUrl: 'http://localhost:8005/api/v1',  // Updated to Content Service!
    fallbackUrl: 'http://localhost:8001/api/v1',
    timeout: 10000,
    debugMode: true
};

console.log('📡 Extension configured to use:', EXTENSION_CONFIG.apiBaseUrl);

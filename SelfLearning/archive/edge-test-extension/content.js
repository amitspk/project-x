console.log('🧪 Edge Test Extension Loaded Successfully!');

// Create visual indicator
const indicator = document.createElement('div');
indicator.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: #00ff00;
    color: black;
    padding: 15px;
    border-radius: 8px;
    z-index: 999999;
    font-family: Arial, sans-serif;
    font-weight: bold;
    box-shadow: 0 4px 8px rgba(0,0,0,0.3);
`;
indicator.textContent = '✅ EDGE EXTENSION WORKING!';
document.body.appendChild(indicator);

// Remove after 10 seconds
setTimeout(() => {
    if (indicator.parentNode) {
        indicator.parentNode.removeChild(indicator);
    }
}, 10000);

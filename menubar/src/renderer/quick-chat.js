// Quick Chat UI Logic
const chatContainer = document.getElementById('chatContainer');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const closeBtn = document.getElementById('closeBtn');
const statusIndicator = document.getElementById('status');

// Connect to main process
const { ipcRenderer } = require('electron');

// Handle close button
closeBtn.addEventListener('click', () => {
  window.close();
});

// Auto-resize textarea
messageInput.addEventListener('input', () => {
  messageInput.style.height = 'auto';
  messageInput.style.height = messageInput.scrollHeight + 'px';
});

// Send message on Enter (Shift+Enter for new line)
messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

// Send message on button click
sendBtn.addEventListener('click', sendMessage);

function sendMessage() {
  const message = messageInput.value.trim();
  if (!message) return;
  
  // Add user message to chat
  addMessage(message, 'user');
  
  // Clear input
  messageInput.value = '';
  messageInput.style.height = 'auto';
  
  // Send to main process
  ipcRenderer.send('send-message', message);
  
  // Show typing indicator
  showTypingIndicator();
}

function addMessage(text, sender) {
  // Remove welcome message if present
  const welcome = chatContainer.querySelector('.welcome-message');
  if (welcome) {
    welcome.remove();
  }
  
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${sender}`;
  
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  bubble.textContent = text;
  
  messageDiv.appendChild(bubble);
  chatContainer.appendChild(messageDiv);
  
  // Scroll to bottom
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showTypingIndicator() {
  const indicator = document.createElement('div');
  indicator.className = 'message jarvis typing-indicator';
  indicator.id = 'typing';
  indicator.innerHTML = '<div class="message-bubble">JARVIS is thinking...</div>';
  chatContainer.appendChild(indicator);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeTypingIndicator() {
  const indicator = document.getElementById('typing');
  if (indicator) {
    indicator.remove();
  }
}

// Listen for responses from JARVIS
ipcRenderer.on('jarvis-response', (event, data) => {
  removeTypingIndicator();
  addMessage(data.text, 'jarvis');
});

// Listen for connection status updates
ipcRenderer.on('connection-status', (event, status) => {
  if (status.connected) {
    statusIndicator.style.backgroundColor = '#4ade80';
  } else {
    statusIndicator.style.backgroundColor = '#ef4444';
  }
});

console.log('[Quick Chat] Initialized');

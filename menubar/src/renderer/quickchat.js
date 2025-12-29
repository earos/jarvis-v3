// Quick Chat UI Logic
const chatContainer = document.getElementById('chat-container');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const connectionStatus = document.getElementById('connection-status');

let isProcessing = false;
let currentAssistantMessage = null;

// Auto-resize textarea
messageInput.addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});

// Send message on Enter (Shift+Enter for new line)
messageInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener('click', sendMessage);

// Listen for chat chunks from main process
window.jarvisAPI.onChatChunk((chunk) => {
  if (!currentAssistantMessage) {
    currentAssistantMessage = addMessage('', 'assistant');
  }
  currentAssistantMessage.textContent += chunk;
  scrollToBottom();
});

// Listen for connection status
window.jarvisAPI.onConnectionStatus((connected) => {
  updateConnectionStatus(connected);
});

// Initialize connection status
window.jarvisAPI.getConnectionStatus().then(updateConnectionStatus);

function updateConnectionStatus(connected) {
  if (connected) {
    connectionStatus.classList.add('connected');
  } else {
    connectionStatus.classList.remove('connected');
  }
}

function addMessage(text, type = 'user') {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${type}`;
  messageDiv.textContent = text;
  chatContainer.appendChild(messageDiv);
  scrollToBottom();
  return messageDiv;
}

function scrollToBottom() {
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function sendMessage() {
  const message = messageInput.value.trim();
  if (!message || isProcessing) return;

  // Add user message
  addMessage(message, 'user');
  messageInput.value = '';
  messageInput.style.height = 'auto';

  // Disable input
  isProcessing = true;
  sendBtn.disabled = true;
  messageInput.disabled = true;

  // Reset current assistant message
  currentAssistantMessage = null;

  try {
    const result = await window.jarvisAPI.sendChat(message);

    if (!result.success) {
      throw new Error(result.error || 'Failed to send message');
    }

    // If we didn't receive chunks, show the full response
    if (!currentAssistantMessage && result.response) {
      addMessage(result.response, 'assistant');
    }
  } catch (error) {
    console.error('Chat error:', error);
    addMessage(`Error: ${error.message}`, 'system');
  } finally {
    isProcessing = false;
    sendBtn.disabled = false;
    messageInput.disabled = false;
    messageInput.focus();
    currentAssistantMessage = null;
  }
}

// Focus input on load
window.addEventListener('load', () => {
  messageInput.focus();
});

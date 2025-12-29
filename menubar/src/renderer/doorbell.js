// Doorbell Alert UI Logic
const cameraStream = document.getElementById('cameraStream');
const loading = document.getElementById('loading');
const timestamp = document.getElementById('timestamp');
const answerBtn = document.getElementById('answerBtn');
const dismissBtn = document.getElementById('dismissBtn');

const { ipcRenderer } = require('electron');

// Listen for doorbell data
ipcRenderer.on('doorbell-data', (event, data) => {
  console.log('[Doorbell] Received data:', data);
  
  // Set camera feed
  if (data.cameraUrl) {
    cameraStream.src = data.cameraUrl;
    cameraStream.onload = () => {
      loading.style.display = 'none';
    };
    cameraStream.onerror = () => {
      loading.textContent = 'Camera feed unavailable';
    };
  }
  
  // Set timestamp
  const now = new Date();
  timestamp.textContent = now.toLocaleTimeString();
});

// Handle answer button
answerBtn.addEventListener('click', () => {
  console.log('[Doorbell] Answer clicked');
  
  // Send answer event to main process
  ipcRenderer.send('doorbell-answer');
  
  // TODO: Open video call or intercom
  alert('Opening intercom...');
  
  window.close();
});

// Handle dismiss button
dismissBtn.addEventListener('click', () => {
  console.log('[Doorbell] Dismissed');
  ipcRenderer.send('doorbell-dismiss');
  window.close();
});

console.log('[Doorbell] Initialized');

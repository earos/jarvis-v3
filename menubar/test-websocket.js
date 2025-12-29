#!/usr/bin/env node

/**
 * WebSocket Test Script for JARVIS Menu Bar App
 * 
 * This script simulates the JARVIS backend and sends test messages
 * to verify the menu bar app is working correctly.
 */

const WebSocket = require('ws');

const PORT = 8000;
const wss = new WebSocket.Server({ port: PORT });

console.log(`WebSocket test server listening on ws://localhost:${PORT}/ws`);
console.log('Waiting for JARVIS Menu Bar App to connect...');
console.log('');

wss.on('connection', (ws) => {
  console.log('✓ Client connected!');
  console.log('');
  
  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data);
      console.log('Received:', JSON.stringify(message, null, 2));
      console.log('');
      
      // Handle different message types
      switch (message.type) {
        case 'status':
          console.log(`✓ Status received from ${message.data.client} v${message.data.version}`);
          break;
          
        case 'chat':
          console.log(`💬 Chat message: "${message.data.message}"`);
          
          // Send a response back
          setTimeout(() => {
            const response = {
              type: 'response',
              data: {
                text: `I received your message: "${message.data.message}". This is a test response from the mock backend.`
              }
            };
            ws.send(JSON.stringify(response));
            console.log('Sent response back to client');
            console.log('');
          }, 1000);
          break;
          
        case 'doorbell_action':
          console.log(`🔔 Doorbell action: ${message.data.action}`);
          break;
          
        default:
          console.log('Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('Error parsing message:', error);
    }
  });
  
  ws.on('close', () => {
    console.log('✗ Client disconnected');
  });
  
  ws.on('error', (error) => {
    console.error('WebSocket error:', error);
  });
  
  // Send test messages after connection
  console.log('Sending test messages in 5 seconds...');
  console.log('');
  
  setTimeout(() => {
    // Test 1: Alert notification
    console.log('Test 1: Sending alert notification...');
    ws.send(JSON.stringify({
      type: 'alert',
      data: {
        title: 'Test Alert',
        message: 'This is a test notification from the JARVIS backend',
        severity: 'info'
      }
    }));
    console.log('');
  }, 5000);
  
  setTimeout(() => {
    // Test 2: Doorbell alert
    console.log('Test 2: Sending doorbell alert...');
    ws.send(JSON.stringify({
      type: 'doorbell',
      data: {
        camera: 'https://placekitten.com/500/400',
        timestamp: new Date().toISOString()
      }
    }));
    console.log('');
  }, 10000);
  
  setTimeout(() => {
    // Test 3: Chat response
    console.log('Test 3: Sending chat response...');
    ws.send(JSON.stringify({
      type: 'response',
      data: {
        text: 'Hello! This is an unsolicited message from JARVIS to test the chat UI.'
      }
    }));
    console.log('');
  }, 15000);
});

// Handle server errors
wss.on('error', (error) => {
  console.error('Server error:', error);
});

console.log('Instructions:');
console.log('1. Start the JARVIS Menu Bar App');
console.log('2. The app should connect to this test server');
console.log('3. Test messages will be sent automatically');
console.log('4. Try sending messages from Quick Chat');
console.log('');
console.log('Press Ctrl+C to stop the test server');
console.log('');

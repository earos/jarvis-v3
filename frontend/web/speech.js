// Speech Manager - handles recognition, TTS, and wake word detection
// OPTIMIZED VERSION with streaming TTS
class SpeechManager {
  constructor(options = {}) {
    // Callbacks
    this.onResult = options.onResult || (() => {});
    this.onWakeWord = options.onWakeWord || (() => {});
    this.onSpeakStart = options.onSpeakStart || (() => {});
    this.onSpeakEnd = options.onSpeakEnd || (() => {});
    this.onListeningStart = options.onListeningStart || (() => {});
    this.onListeningEnd = options.onListeningEnd || (() => {});
    this.onError = options.onError || ((err) => console.error("Speech error:", err));
    
    // State
    this.speechEnabled = true;
    this.isListening = false;
    this.isSpeaking = false;
    this.wakeWordEnabled = false;
    
    // Recognition instances
    this.recognition = null;
    this.wakeWordRecognition = null;
    
    // Audio queue for sentence streaming
    this.audioQueue = [];
    this.currentAudio = null;
    this.isProcessingQueue = false;
    
    // Configuration
    this.config = window.JARVIS_CONFIG || {
      WAKE_WORDS: ["jarvis", "hey jarvis", "ok jarvis", "hello jarvis"],
      API: { TTS: "/api/tts", TTS_SENTENCE: "/api/tts/sentence" }
    };
    
    this.initRecognition();
  }
  
  initRecognition() {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
      console.warn("Speech recognition not supported in this browser");
      return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    // Main recognition for manual voice input
    this.recognition = new SpeechRecognition();
    this.recognition.continuous = false;
    this.recognition.interimResults = false;
    this.recognition.lang = "en-GB";
    
    this.recognition.onstart = () => {
      this.isListening = true;
      this.onListeningStart();
    };
    
    this.recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      this.onResult(transcript);
    };
    
    this.recognition.onend = () => {
      this.isListening = false;
      this.onListeningEnd();
    };
    
    this.recognition.onerror = (event) => {
      this.onError(event.error);
      this.isListening = false;
      this.onListeningEnd();
    };
    
    // Wake word recognition
    this.wakeWordRecognition = new SpeechRecognition();
    this.wakeWordRecognition.continuous = true;
    this.wakeWordRecognition.interimResults = true;
    this.wakeWordRecognition.lang = "en-GB";
    
    this.wakeWordRecognition.onresult = (event) => {
      const lastResult = event.results[event.results.length - 1];
      const transcript = lastResult[0].transcript.toLowerCase().trim();
      
      const hasWakeWord = this.config.WAKE_WORDS.some(w => transcript.includes(w));
      
      if (hasWakeWord && lastResult.isFinal) {
        let command = transcript;
        this.config.WAKE_WORDS.forEach(w => {
          command = command.replace(w, "").trim();
        });
        
        command = command.replace(/^(please|can you|could you|would you)\s*/i, "").trim();
        
        if (command.length > 2) {
          console.log("Wake word detected, command:", command);
          this.onWakeWord(command, false);
        } else if (transcript.includes("jarvis") && command.length <= 2) {
          console.log("Wake word acknowledged");
          this.onWakeWord("", true);
        }
      }
    };
    
    this.wakeWordRecognition.onend = () => {
      if (this.wakeWordEnabled && !this.isSpeaking) {
        setTimeout(() => {
          if (this.wakeWordEnabled) {
            try {
              this.wakeWordRecognition.start();
            } catch (e) {
              console.log("Wake word restart delayed");
            }
          }
        }, 100);
      }
    };
    
    this.wakeWordRecognition.onerror = (event) => {
      if (event.error !== "no-speech" && event.error !== "aborted") {
        console.error("Wake word error:", event.error);
      }
      if (this.wakeWordEnabled && event.error !== "not-allowed") {
        setTimeout(() => {
          if (this.wakeWordEnabled) {
            try {
              this.wakeWordRecognition.start();
            } catch (e) {}
          }
        }, 1000);
      }
    };
  }
  
  startListening() {
    if (!this.recognition) {
      this.onError("Speech recognition not available");
      return;
    }
    
    if (this.isListening) {
      this.stopListening();
      return;
    }
    
    if (this.wakeWordEnabled) {
      try { 
        this.wakeWordRecognition.stop(); 
      } catch (e) {}
    }
    
    try {
      this.recognition.start();
    } catch (e) {
      this.onError(e.message);
    }
  }
  
  stopListening() {
    if (this.recognition && this.isListening) {
      try {
        this.recognition.stop();
      } catch (e) {}
    }
  }
  
  // Split text into sentences for streaming
  splitIntoSentences(text) {
    // Clean text first
    const cleanText = text
      .replace(/```[\s\S]*?```/g, "code block")
      .replace(/`[^`]+`/g, "")
      .replace(/\*\*/g, "")
      .replace(/\|/g, "")
      .replace(/-{2,}/g, "")
      .trim();
    
    // Split on sentence boundaries
    const sentences = cleanText.match(/[^.!?]+[.!?]+/g) || [cleanText];
    
    // Filter out very short sentences and clean up
    return sentences
      .map(s => s.trim())
      .filter(s => s.length > 10);  // Minimum sentence length
  }
  
  async speak(text) {
    // Stop any current speech first
    this.stopSpeaking();
    
    if (!this.speechEnabled) {
      return;
    }
    
    // Pause wake word during speech
    if (this.wakeWordEnabled) {
      try { 
        this.wakeWordRecognition.stop(); 
      } catch (e) {}
    }
    
    // Split into sentences and queue them
    const sentences = this.splitIntoSentences(text);
    
    if (sentences.length === 0) {
      return;
    }
    
    console.log(`Speaking ${sentences.length} sentences with streaming TTS`);
    
    // Queue all sentences
    this.audioQueue = sentences.map(sentence => ({
      text: sentence,
      audio: null,
      status: "pending"
    }));
    
    // Start processing queue
    this.processAudioQueue();
  }
  
  async processAudioQueue() {
    if (this.isProcessingQueue || this.audioQueue.length === 0) {
      return;
    }
    
    this.isProcessingQueue = true;
    this.isSpeaking = true;
    this.onSpeakStart();
    
    // Process sentences sequentially
    for (let i = 0; i < this.audioQueue.length; i++) {
      const item = this.audioQueue[i];
      
      if (item.status === "pending") {
        try {
          // Fetch audio for this sentence
          item.status = "loading";
          const audioUrl = await this.fetchSentenceAudio(item.text);
          item.audio = new Audio(audioUrl);
          item.status = "ready";
          
          // Play this sentence
          await this.playSentence(item.audio, audioUrl);
          item.status = "played";
          
        } catch (error) {
          console.error("Error processing sentence:", error);
          item.status = "error";
          // Continue to next sentence on error
        }
      }
    }
    
    // All sentences played
    this.audioQueue = [];
    this.isProcessingQueue = false;
    this.isSpeaking = false;
    this.currentAudio = null;
    this.onSpeakEnd();
    this.resumeWakeWord();
  }
  
  async fetchSentenceAudio(text) {
    const response = await fetch(this.config.API.TTS_SENTENCE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });
    
    if (!response.ok) {
      throw new Error("TTS request failed");
    }
    
    const audioBlob = await response.blob();
    return URL.createObjectURL(audioBlob);
  }
  
  playSentence(audio, url) {
    return new Promise((resolve, reject) => {
      this.currentAudio = audio;
      
      audio.onended = () => {
        URL.revokeObjectURL(url);
        resolve();
      };
      
      audio.onerror = (e) => {
        URL.revokeObjectURL(url);
        reject(e);
      };
      
      audio.play().catch(reject);
    });
  }
  
  async speakWithTTS(text) {
    // Legacy method - now uses streaming
    await this.speak(text);
  }
  
  speakWithBrowser(text) {
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;
    
    const voices = speechSynthesis.getVoices();
    const preferredVoice = voices.find(v =>
      v.name.includes("Daniel") ||
      v.name.includes("Google UK English Male")
    );
    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }
    
    utterance.onstart = () => {
      this.isSpeaking = true;
      this.onSpeakStart();
    };
    
    utterance.onend = () => {
      this.isSpeaking = false;
      this.onSpeakEnd();
      this.resumeWakeWord();
    };
    
    utterance.onerror = () => {
      this.isSpeaking = false;
      this.onSpeakEnd();
      this.resumeWakeWord();
    };
    
    speechSynthesis.speak(utterance);
  }
  
  stopSpeaking() {
    // Stop all queued audio
    this.audioQueue = [];
    this.isProcessingQueue = false;
    
    // Stop current audio
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
    }
    
    // Stop browser speech
    speechSynthesis.cancel();
    
    if (this.isSpeaking) {
      this.isSpeaking = false;
      this.onSpeakEnd();
    }
    
    this.resumeWakeWord();
  }
  
  enableWakeWord() {
    if (!this.wakeWordRecognition) {
      this.onError("Wake word detection not supported in this browser");
      return false;
    }
    
    if (this.wakeWordEnabled) {
      return true;
    }
    
    this.wakeWordEnabled = true;
    
    try {
      this.wakeWordRecognition.start();
      console.log("Wake word mode enabled - say \"Hey JARVIS\"");
      return true;
    } catch (e) {
      console.error("Failed to start wake word:", e);
      this.wakeWordEnabled = false;
      return false;
    }
  }
  
  disableWakeWord() {
    if (!this.wakeWordEnabled) {
      return;
    }
    
    this.wakeWordEnabled = false;
    
    try {
      this.wakeWordRecognition.stop();
    } catch (e) {}
    
    console.log("Wake word mode disabled");
  }
  
  toggleWakeWord() {
    if (this.wakeWordEnabled) {
      this.disableWakeWord();
      return false;
    } else {
      return this.enableWakeWord();
    }
  }
  
  resumeWakeWord() {
    if (this.wakeWordEnabled) {
      setTimeout(() => {
        if (this.wakeWordEnabled && !this.isSpeaking) {
          try { 
            this.wakeWordRecognition.start(); 
          } catch (e) {}
        }
      }, 500);
    }
  }
  
  toggleTTS(enabled) {
    this.speechEnabled = enabled;
    if (!enabled) {
      this.stopSpeaking();
    }
  }
  
  cleanup() {
    this.stopSpeaking();
    this.stopListening();
    this.disableWakeWord();
    
    if (this.recognition) {
      this.recognition.abort();
      this.recognition = null;
    }
    
    if (this.wakeWordRecognition) {
      this.wakeWordRecognition.abort();
      this.wakeWordRecognition = null;
    }
  }
}

// Make globally available
window.SpeechManager = SpeechManager;

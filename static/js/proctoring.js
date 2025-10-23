/**
 * MRI Training Platform - Proctoring System
 * Includes: Webcam snapshots, browser lockdown, tab monitoring, IP tracking
 */

class ProctoringSystem {
    constructor(attemptId, snapshotIntervalSeconds = 180, csrfToken) {
        this.attemptId = attemptId;
        this.snapshotIntervalSeconds = snapshotIntervalSeconds;
        this.csrfToken = csrfToken;
        this.videoStream = null;
        this.snapshotTimer = null;
        this.warningCount = 0;
        this.maxWarnings = 3;
        this.isFullscreen = false;
        
        // URLs
        this.snapshotUploadUrl = `/proctoring/snapshot/${attemptId}/`;
        this.eventLogUrl = `/proctoring/event/${attemptId}/`;
    }
    
    /**
     * Initialize all proctoring features
     */
    async initialize() {
        try {
            // 1. Request webcam access
            await this.requestWebcamAccess();
            
            // 2. Setup browser lockdown
            this.setupBrowserLockdown();
            
            // 3. Force fullscreen
            this.enterFullscreen();
            
            // 4. Start snapshot timer
            this.startSnapshotTimer();
            
            // 5. Log IP address
            await this.logIPAddress();
            
            console.log('Proctoring system initialized successfully');
            return true;
        } catch (error) {
            console.error('Proctoring initialization failed:', error);
            alert('Unable to initialize proctoring. Please check your webcam permissions and try again.');
            return false;
        }
    }
    
    /**
     * Request webcam access
     */
    async requestWebcamAccess() {
        try {
            this.videoStream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                },
                audio: false
            });
            
            console.log('Webcam access granted');
            return true;
        } catch (error) {
            console.error('Webcam access denied:', error);
            throw new Error('Webcam access is required for this test');
        }
    }
    
    /**
     * Capture and upload webcam snapshot
     */
    async captureWebcamSnapshot() {
        if (!this.videoStream) {
            console.warn('Video stream not available');
            return;
        }
        
        try {
            // Create hidden video element
            const video = document.createElement('video');
            video.srcObject = this.videoStream;
            video.play();
            
            // Wait for video to be ready
            await new Promise(resolve => {
                video.onloadedmetadata = resolve;
            });
            
            // Create canvas and capture frame
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0);
            
            // Convert to compressed blob
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/jpeg', 0.6); // 60% quality for compression
            });
            
            // Upload snapshot
            await this.uploadSnapshot(blob, 'webcam');
            
            console.log('Webcam snapshot captured and uploaded');
        } catch (error) {
            console.error('Failed to capture webcam snapshot:', error);
        }
    }
    
    /**
     * Capture and upload screen snapshot
     */
    async captureScreenSnapshot() {
        try {
            // Capture screen
            const canvas = await html2canvas(document.body, {
                scale: 0.5, // Reduce resolution for compression
                logging: false
            });
            
            // Convert to compressed blob
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/jpeg', 0.6);
            });
            
            // Upload snapshot
            await this.uploadSnapshot(blob, 'screen');
            
            console.log('Screen snapshot captured and uploaded');
        } catch (error) {
            console.error('Failed to capture screen snapshot:', error);
        }
    }
    
    /**
     * Upload snapshot to server
     */
    async uploadSnapshot(blob, type) {
        const formData = new FormData();
        formData.append('image', blob, `${type}_${Date.now()}.jpg`);
        formData.append('event_type', type);
        
        try {
            const response = await fetch(this.snapshotUploadUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken
                },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Upload failed');
            }
        } catch (error) {
            console.error('Failed to upload snapshot:', error);
        }
    }
    
    /**
     * Start periodic snapshot capture
     */
    startSnapshotTimer() {
        // Randomize interval slightly to prevent prediction
        const variation = Math.random() * 60000; // ±30 seconds
        const interval = (this.snapshotIntervalSeconds * 1000) + variation;
        
        this.snapshotTimer = setInterval(async () => {
            await this.captureWebcamSnapshot();
            await this.captureScreenSnapshot();
        }, interval);
        
        // Take first snapshot immediately
        setTimeout(() => {
            this.captureWebcamSnapshot();
            this.captureScreenSnapshot();
        }, 5000); // Wait 5 seconds after test starts
    }
    
    /**
     * Setup browser lockdown features
     */
    setupBrowserLockdown() {
        // Disable right-click
        document.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this.logEvent('right_click', { x: e.clientX, y: e.clientY });
            this.showWarning('Right-click is disabled during the test');
        });
        
        // Disable F12, Ctrl+Shift+I, Ctrl+U, etc.
        document.addEventListener('keydown', (e) => {
            // F12
            if (e.key === 'F12') {
                e.preventDefault();
                this.logEvent('devtools_attempt');
                this.showWarning('Developer tools are not allowed');
                return false;
            }
            
            // Ctrl+Shift+I (DevTools)
            if (e.ctrlKey && e.shiftKey && e.key === 'I') {
                e.preventDefault();
                this.logEvent('devtools_attempt');
                this.showWarning('Developer tools are not allowed');
                return false;
            }
            
            // Ctrl+U (View Source)
            if (e.ctrlKey && e.key === 'u') {
                e.preventDefault();
                this.logEvent('view_source_attempt');
                return false;
            }
            
            // Ctrl+C (Copy)
            if (e.ctrlKey && e.key === 'c') {
                e.preventDefault();
                this.logEvent('copy_paste', { action: 'copy' });
                this.showWarning('Copying is disabled during the test');
                return false;
            }
            
            // Ctrl+V (Paste)
            if (e.ctrlKey && e.key === 'v') {
                e.preventDefault();
                this.logEvent('copy_paste', { action: 'paste' });
                this.showWarning('Pasting is disabled during the test');
                return false;
            }
        });
        
        // Detect tab switch / window blur
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.logEvent('tab_switch');
                this.warningCount++;
                
                if (this.warningCount >= this.maxWarnings) {
                    this.forceSubmitTest('Too many tab switches detected');
                } else {
                    this.showWarning(`Tab switching detected! Warning ${this.warningCount}/${this.maxWarnings}`);
                }
            }
        });
        
        window.addEventListener('blur', () => {
            this.logEvent('window_blur');
        });
        
        // Detect fullscreen exit
        document.addEventListener('fullscreenchange', () => {
            if (!document.fullscreenElement) {
                this.isFullscreen = false;
                this.logEvent('fullscreen_exit');
                this.warningCount++;
                
                if (this.warningCount >= this.maxWarnings) {
                    this.forceSubmitTest('Exited fullscreen too many times');
                } else {
                    this.showWarning(`Please return to fullscreen! Warning ${this.warningCount}/${this.maxWarnings}`);
                    setTimeout(() => this.enterFullscreen(), 2000);
                }
            } else {
                this.isFullscreen = true;
            }
        });
        
        // Warn before leaving page
        window.addEventListener('beforeunload', (e) => {
            e.preventDefault();
            e.returnValue = 'Are you sure you want to leave the test? Your progress will be lost.';
            return e.returnValue;
        });
    }
    
    /**
     * Enter fullscreen mode
     */
    enterFullscreen() {
        const elem = document.documentElement;
        
        if (elem.requestFullscreen) {
            elem.requestFullscreen().catch(err => {
                console.error('Failed to enter fullscreen:', err);
            });
        } else if (elem.webkitRequestFullscreen) {
            elem.webkitRequestFullscreen();
        } else if (elem.msRequestFullscreen) {
            elem.msRequestFullscreen();
        }
    }
    
    /**
     * Log proctoring event to server
     */
    async logEvent(eventType, metadata = {}) {
        try {
            await fetch(this.eventLogUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    event_type: eventType,
                    metadata: metadata,
                    timestamp: new Date().toISOString()
                })
            });
        } catch (error) {
            console.error('Failed to log event:', error);
        }
    }
    
    /**
     * Log IP address
     */
    async logIPAddress() {
        try {
            // Get IP from external service
            const response = await fetch('https://api.ipify.org?format=json');
            const data = await response.json();
            
            await this.logEvent('ip_address', { ip: data.ip });
        } catch (error) {
            console.error('Failed to log IP:', error);
        }
    }
    
    /**
     * Show warning to user
     */
    showWarning(message) {
        // Create warning overlay
        const warning = document.createElement('div');
        warning.className = 'proctoring-warning';
        warning.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: #ff9800;
                color: white;
                padding: 15px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                z-index: 10000;
                font-weight: bold;
                animation: slideIn 0.3s ease-out;
            ">
                ⚠️ ${message}
            </div>
        `;
        
        document.body.appendChild(warning);
        
        setTimeout(() => {
            warning.remove();
        }, 5000);
    }
    
    /**
     * Force submit test due to violation
     */
    forceSubmitTest(reason) {
        alert(`Test is being submitted due to: ${reason}`);
        
        // Log the violation
        this.logEvent('forced_submission', { reason });
        
        // Submit the test form
        const form = document.querySelector('form');
        if (form) {
            form.submit();
        } else {
            window.location.href = `/test/submit/${this.attemptId}/`;
        }
    }
    
    /**
     * Cleanup when test ends
     */
    cleanup() {
        // Stop snapshot timer
        if (this.snapshotTimer) {
            clearInterval(this.snapshotTimer);
        }
        
        // Stop video stream
        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => track.stop());
        }
        
        // Exit fullscreen
        if (document.fullscreenElement) {
            document.exitFullscreen();
        }
        
        console.log('Proctoring system cleaned up');
    }
}

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);

// Export for use in templates
window.ProctoringSystem = ProctoringSystem;
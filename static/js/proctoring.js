class ProctoringSystem {
    constructor(attemptId, snapshotIntervalSeconds = 180, csrfToken) {
        this.attemptId = attemptId;
        this.snapshotIntervalSeconds = snapshotIntervalSeconds;
        this.csrfToken = csrfToken;
        this.videoStream = null;
        this.snapshotTimer = null;
        this.streamMonitorTimer = null;
        this.warningCount = 0;
        this.maxWarnings = 3;
        this.isFullscreen = false;
        this.permissionsGranted = false;
        this.cameraDisabledWarningShown = false;
        
        // URLs
        this.snapshotUploadUrl = `/proctoring/snapshot/${attemptId}/`;
        this.eventLogUrl = `/proctoring/event/${attemptId}/`;
    }
    
    /**
     * Initialize all proctoring features
     * CRITICAL: Returns false if camera permission denied - exam should NOT start
     */
    async initialize() {
        try {
            // 1. Request webcam access (CAMERA ONLY - NO MICROPHONE)
            const permissionsGranted = await this.requestCameraAccess();
            
            if (!permissionsGranted) {
                console.error('Camera permission denied - cannot start exam');
                this.showPermissionError();
                return false;
            }
            
            this.permissionsGranted = true;
            
            // 2. Start continuous camera monitoring
            this.startCameraMonitoring();
            
            // 3. Setup browser lockdown
            this.setupBrowserLockdown();
            
            // 4. Force fullscreen
            this.enterFullscreen();
            
            // 5. Start snapshot timer
            this.startSnapshotTimer();
            
            // 6. Log IP address
            await this.logIPAddress();
            
            // 7. Log successful initialization
            await this.logEvent('proctoring_initialized', {
                severity: 'info',
                snapshot_interval: this.snapshotIntervalSeconds,
                features: ['camera_monitoring', 'browser_lockdown', 'fullscreen', 'screenshots']
            });
            
            console.log('✓ Proctoring system initialized successfully');
            return true;
        } catch (error) {
            console.error('✗ Proctoring initialization failed:', error);
            this.showPermissionError();
            return false;
        }
    }
    
    /**
     * Request camera access only (NO MICROPHONE)
     * REQUIRED for exam to start
     */
    async requestCameraAccess() {
        try {
            // Request video only - no audio
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                },
                audio: false  // NO MICROPHONE REQUIRED
            });
            
            // Store video stream
            this.videoStream = stream;
            
            // Verify video track is present and active
            const videoTrack = stream.getVideoTracks()[0];
            if (!videoTrack || !videoTrack.enabled) {
                console.error('Camera not available or disabled');
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                }
                return false;
            }
            
            // Log camera access granted
            await this.logEvent('camera_access_granted', {
                severity: 'info',
                video_width: videoTrack.getSettings().width,
                video_height: videoTrack.getSettings().height,
                device_id: videoTrack.getSettings().deviceId || 'unknown'
            });
            
            console.log('✓ Camera access granted');
            return true;
        } catch (error) {
            console.error('✗ Camera access denied:', error);
            
            // Log specific error types
            if (error.name === 'NotAllowedError') {
                console.error('User denied camera permission');
            } else if (error.name === 'NotFoundError') {
                console.error('No camera found on device');
            } else if (error.name === 'NotReadableError') {
                console.error('Camera is already in use');
            }
            
            return false;
        }
    }
    
    /**
     * Continuously monitor camera stream to detect if user turns it off
     * CRITICAL: This prevents users from disabling camera during exam
     */
    startCameraMonitoring() {
        // Check camera status every 2 seconds
        this.streamMonitorTimer = setInterval(() => {
            if (!this.videoStream) {
                this.handleCameraDisabled();
                return;
            }
            
            const videoTrack = this.videoStream.getVideoTracks()[0];
            
            // Check if track exists and is enabled
            if (!videoTrack) {
                this.handleCameraDisabled();
                return;
            }
            
            // Check if track is still live
            if (videoTrack.readyState === 'ended') {
                this.handleCameraDisabled();
                return;
            }
            
            // Check if track is enabled
            if (!videoTrack.enabled) {
                this.handleCameraDisabled();
                return;
            }
            
            // Track is active and enabled - all good
            console.log('✓ Camera monitoring: Active');
        }, 2000); // Check every 2 seconds
        
        // Also listen for track ended event
        const videoTrack = this.videoStream.getVideoTracks()[0];
        if (videoTrack) {
            videoTrack.addEventListener('ended', () => {
                this.handleCameraDisabled();
            });
        }
        
        console.log('✓ Camera monitoring started');
    }
    
    /**
     * Handle camera being disabled during exam
     * CRITICAL: This prevents cheating by disabling camera
     */
    handleCameraDisabled() {
        if (this.cameraDisabledWarningShown) {
            return; // Already shown warning
        }
        
        this.cameraDisabledWarningShown = true;
        
        // Log the event with CRITICAL severity
        this.logEvent('camera_disabled', {
            severity: 'critical',
            timestamp: new Date().toISOString(),
            note: 'Camera was disabled or disconnected during exam'
        });
        
        // Show critical warning
        this.showCameraDisabledWarning();
        
        console.error('❌ CRITICAL: Camera disabled during exam');
    }
    
    /**
     * Show critical warning when camera is disabled
     */
    showCameraDisabledWarning() {
        const warningDiv = document.createElement('div');
        warningDiv.id = 'camera-disabled-warning';
        warningDiv.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border: 4px solid #dc2626;
            border-radius: 8px;
            padding: 30px;
            max-width: 500px;
            z-index: 10001;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
        `;
        
        warningDiv.innerHTML = `
            <div style="text-align: center;">
                <div style="font-size: 64px; margin-bottom: 15px;">🚨</div>
                <h2 style="color: #dc2626; margin-bottom: 15px; font-size: 28px; font-weight: bold;">
                    CAMERA DISABLED!
                </h2>
                <p style="color: #374151; margin-bottom: 20px; line-height: 1.6; font-size: 16px;">
                    <strong>Your camera has been turned off during the exam.</strong>
                    <br><br>
                    This is a serious violation of exam proctoring rules.
                    <br><br>
                    <span style="color: #dc2626; font-weight: bold;">
                    This incident has been logged and your exam may be disqualified.
                    </span>
                </p>
                <div style="margin-top: 20px; padding: 15px; background: #fee2e2; border-radius: 6px;">
                    <p style="color: #991b1b; font-size: 14px; margin: 0; font-weight: bold;">
                        Please refresh the page immediately and restart the exam with your camera enabled.
                    </p>
                </div>
                <button onclick="location.reload()" style="
                    background: #dc2626;
                    color: white;
                    border: none;
                    padding: 15px 30px;
                    border-radius: 6px;
                    font-size: 18px;
                    font-weight: bold;
                    cursor: pointer;
                    margin-top: 20px;
                    width: 100%;
                ">
                    Refresh & Restart Exam
                </button>
            </div>
        `;
        
        // Add dark overlay
        const overlay = document.createElement('div');
        overlay.id = 'camera-warning-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.85);
            z-index: 10000;
        `;
        
        // Remove any existing warnings first
        const existingWarning = document.getElementById('camera-disabled-warning');
        const existingOverlay = document.getElementById('camera-warning-overlay');
        if (existingWarning) existingWarning.remove();
        if (existingOverlay) existingOverlay.remove();
        
        document.body.appendChild(overlay);
        document.body.appendChild(warningDiv);
    }
    
    /**
     * Show clear error message when camera permission is initially denied
     */
    showPermissionError() {
        // Log permission denied event
        this.logEvent('camera_permission_denied', {
            severity: 'critical',
            timestamp: new Date().toISOString(),
            note: 'User denied camera permission - exam cannot start'
        }).catch(err => console.error('Failed to log permission denied:', err));
        
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border: 3px solid #dc2626;
            border-radius: 8px;
            padding: 30px;
            max-width: 500px;
            z-index: 10000;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        `;
        
        errorDiv.innerHTML = `
            <div style="text-align: center;">
                <div style="font-size: 48px; margin-bottom: 15px;">📷</div>
                <h2 style="color: #dc2626; margin-bottom: 15px; font-size: 24px;">
                    Camera Access Required
                </h2>
                <p style="color: #374151; margin-bottom: 20px; line-height: 1.6;">
                    This exam requires <strong>camera access</strong> for proctoring purposes.
                    <br><br>
                    Please enable camera permissions and refresh the page to start the exam.
                </p>
                <button onclick="location.reload()" style="
                    background: #2563eb;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 6px;
                    font-size: 16px;
                    cursor: pointer;
                    margin-right: 10px;
                ">
                    Refresh & Retry
                </button>
                <button onclick="window.location.href='/dashboard/'" style="
                    background: #6b7280;
                    color: white;
                    border: none;
                    padding: 12px 24px;
                    border-radius: 6px;
                    font-size: 16px;
                    cursor: pointer;
                ">
                    Back to Dashboard
                </button>
                <div style="margin-top: 20px; padding: 15px; background: #fef3c7; border-radius: 6px;">
                    <p style="color: #92400e; font-size: 14px; margin: 0;">
                        <strong>Troubleshooting:</strong><br>
                        1. Check browser camera permission settings<br>
                        2. Ensure camera is not in use by another app<br>
                        3. Try a different browser (Chrome recommended)<br>
                        4. Make sure your device has a working camera
                    </p>
                </div>
            </div>
        `;
        
        // Add overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            z-index: 9999;
        `;
        
        document.body.appendChild(overlay);
        document.body.appendChild(errorDiv);
    }
    
    /**
     * Capture and upload webcam snapshot
     */
    async captureWebcamSnapshot() {
        if (!this.videoStream || !this.permissionsGranted) {
            console.warn('Video stream not available or permissions not granted');
            return;
        }
        
        // Verify camera is still active
        const videoTrack = this.videoStream.getVideoTracks()[0];
        if (!videoTrack || videoTrack.readyState === 'ended' || !videoTrack.enabled) {
            console.warn('Camera is not active - skipping snapshot');
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
            
            // Convert to blob with compression (60% quality)
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/jpeg', 0.6);
            });
            
            // Upload snapshot
            await this.uploadSnapshot(blob);
            
            console.log('✓ Webcam snapshot captured and uploaded');
        } catch (error) {
            console.error('✗ Failed to capture snapshot:', error);
        }
    }
    
    /**
     * Capture and upload screen screenshot
     */
    async captureScreenshot() {
        try {
            const canvas = await html2canvas(document.body, {
                allowTaint: true,
                useCORS: true,
                logging: false,
                scale: 0.5 // Reduce size for faster upload
            });
            
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/jpeg', 0.6);
            });
            
            await this.uploadSnapshot(blob, 'screen');
            
            console.log('✓ Screenshot captured and uploaded');
        } catch (error) {
            console.error('✗ Failed to capture screenshot:', error);
        }
    }
    
    /**
     * Upload snapshot to server
     */
    async uploadSnapshot(blob, type = 'webcam') {
        const formData = new FormData();
        formData.append('snapshot', blob, `${type}_snapshot.jpg`);
        formData.append('snapshot_type', type);
        formData.append('csrfmiddlewaretoken', this.csrfToken);
        
        try {
            const response = await fetch(this.snapshotUploadUrl, {
                method: 'POST',
                body: formData,
            });
            
            if (!response.ok) {
                throw new Error(`Upload failed: ${response.status}`);
            }
        } catch (error) {
            console.error('Snapshot upload error:', error);
        }
    }
    
    /**
     * Start periodic snapshot timer
     */
    startSnapshotTimer() {
        // Take first snapshots immediately
        this.captureWebcamSnapshot();
        this.captureScreenshot();
        
        // Then take snapshots at intervals
        this.snapshotTimer = setInterval(() => {
            this.captureWebcamSnapshot();
            this.captureScreenshot();
        }, this.snapshotIntervalSeconds * 1000);
    }
    
    /**
     * Setup browser lockdown features
     */
    setupBrowserLockdown() {
        // Disable right-click
        document.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this.logEvent('right_click_blocked');
        });
        
        // Disable common keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+U
            if (e.key === 'F12' || 
                (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'J')) ||
                (e.ctrlKey && e.key === 'U')) {
                e.preventDefault();
                this.logEvent('devtools_blocked');
            }
            
            // Ctrl+C, Ctrl+V
            if (e.ctrlKey && (e.key === 'c' || e.key === 'v')) {
                e.preventDefault();
                this.logEvent('copy_paste_blocked');
            }
        });
        
        // Tab visibility detection
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.warningCount++;
                this.logEvent('tab_switched', { warning_count: this.warningCount });
                
                if (this.warningCount >= this.maxWarnings) {
                    alert(`Warning ${this.warningCount}/${this.maxWarnings}: Tab switching is not allowed! Your test may be flagged.`);
                }
            }
        });
        
        // Window blur detection
        window.addEventListener('blur', () => {
            this.logEvent('window_blur');
        });
        
        console.log('✓ Browser lockdown enabled');
    }
    
    /**
     * Force fullscreen mode
     */
    enterFullscreen() {
        const elem = document.documentElement;
        
        if (elem.requestFullscreen) {
            elem.requestFullscreen().catch(err => {
                console.error('Fullscreen request failed:', err);
            });
        }
        
        // Monitor fullscreen exits
        document.addEventListener('fullscreenchange', () => {
            if (!document.fullscreenElement) {
                this.logEvent('fullscreen_exit');
                // Try to re-enter fullscreen
                setTimeout(() => this.enterFullscreen(), 100);
            }
        });
    }
    
    /**
     * Log IP address to database
     * UPDATED: Properly saves IP to TestAttempt model
     */
    async logIPAddress() {
        try {
            const response = await fetch('https://api.ipify.org?format=json');
            const data = await response.json();
            
            // Log to database with special 'ip_logged' event type
            // Backend will save this to TestAttempt.ip_address field
            await this.logEvent('ip_logged', { 
                ip: data.ip,
                severity: 'info'
            });
            
            console.log('✓ IP address logged:', data.ip);
        } catch (error) {
            console.error('Failed to log IP:', error);
            // Try to log at least the server-side IP
            await this.logEvent('ip_logged', {
                ip: 'server_side',
                note: 'Failed to get client IP, using server detection',
                severity: 'info'
            });
        }
    }
    
    /**
     * Log proctoring event
     */
    async logEvent(eventType, extraData = {}) {
        const eventData = {
            event_type: eventType,
            timestamp: new Date().toISOString(),
            ...extraData
        };
        
        try {
            await fetch(this.eventLogUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                },
                body: JSON.stringify(eventData),
            });
        } catch (error) {
            console.error('Failed to log event:', error);
        }
    }
    
    /**
     * Cleanup resources
     */
    cleanup() {
        // Stop camera monitoring
        if (this.streamMonitorTimer) {
            clearInterval(this.streamMonitorTimer);
        }
        
        // Stop snapshot timer
        if (this.snapshotTimer) {
            clearInterval(this.snapshotTimer);
        }
        
        // Stop video stream
        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => track.stop());
        }
        
        console.log('✓ Proctoring system cleaned up');
    }
}
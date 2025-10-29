class ProctoringSystem {
    constructor(attemptId, snapshotIntervalSeconds = 180, csrfToken) {
        this.attemptId = attemptId;
        this.snapshotIntervalSeconds = snapshotIntervalSeconds;
        this.csrfToken = csrfToken;
        
        // Camera & monitoring
        this.videoStream = null;
        this.snapshotTimer = null;
        this.streamMonitorTimer = null;
        this.permissionsGranted = false;
        this.cameraDisabledWarningShown = false;
        
        // Warning system
        this.warningCount = 0;
        this.maxWarnings = 3;
        this.fullscreenExitCount = 0;
        this.maxFullscreenExits = 3;
        
        // Fullscreen
        this.isFullscreen = false;
        
        this.captureOnEvents = true;  // Enable/disable event-triggered screenshots
        this.eventScreenshotDelay = 100;  // Milliseconds to wait before capture
        this.lastEventScreenshotTime = 0;  // Prevent duplicate screenshots
        this.eventScreenshotCooldown = 2000;  // Min 2 seconds between event screenshots
        
        // Window focus tracking (NEW)
        this.windowHasFocus = true;
        this.windowBlurTime = null;
        this.windowFocusTime = null;

        // Library & capability checks
        this.html2canvasAvailable = false;
        this.screenshotCapable = false;
        this.adBlockerDetected = false;
        this.uploadEndpointBlocked = false;
        
        // URLs
        this.snapshotUploadUrl = `/proctoring/snapshot/${attemptId}/`;
        this.eventLogUrl = `/proctoring/event/${attemptId}/`;
    }
    
    /**
     * Verify html2canvas library is loaded
     */
    verifyHtml2Canvas() {
        console.log('🔍 Checking html2canvas availability...');
        
        if (typeof html2canvas !== 'undefined') {
            this.html2canvasAvailable = true;
            console.log('✅ html2canvas library loaded');
            return true;
        } else {
            this.html2canvasAvailable = false;
            console.error('❌ html2canvas NOT loaded - screenshots will FAIL!');
            return false;
        }
    }

    /**
     * Test screenshot capability
     */
    async testScreenshotCapability() {
        console.log('🧪 Testing screenshot capability...');
        
        if (!this.html2canvasAvailable) {
            console.error('❌ Cannot test - html2canvas not loaded');
            return false;
        }
        
        try {
            // Try to capture a tiny test screenshot
            const testDiv = document.createElement('div');
            testDiv.style.width = '10px';
            testDiv.style.height = '10px';
            testDiv.style.background = 'red';
            testDiv.style.position = 'absolute';
            testDiv.style.top = '-100px';
            document.body.appendChild(testDiv);
            
            const canvas = await html2canvas(testDiv, {
                logging: false,
                width: 10,
                height: 10
            });
            
            document.body.removeChild(testDiv);
            
            if (canvas && canvas.width > 0) {
                this.screenshotCapable = true;
                console.log('✅ Screenshot test PASSED');
                return true;
            } else {
                this.screenshotCapable = false;
                console.error('❌ Screenshot test FAILED - canvas empty');
                return false;
            }
            
        } catch (error) {
            this.screenshotCapable = false;
            console.error('❌ Screenshot test FAILED:', error.message);
            return false;
        }
    }

     /**
     * Detect ad blockers using multiple methods
     */
    async detectAdBlocker() {
        console.log('🔍 Checking for ad blockers...');
        
        let detected = false;
        
        // Method 1: Try to load a fake ad script
        try {
            const testScript = document.createElement('script');
            testScript.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js';
            testScript.onerror = () => {
                detected = true;
                console.warn('⚠️ Ad blocker detected (Method 1)');
            };
            document.head.appendChild(testScript);
            
            // Wait a bit
            await new Promise(resolve => setTimeout(resolve, 100));
            
            document.head.removeChild(testScript);
        } catch (error) {
            // Ignore errors
        }
        
        // Method 2: Check for common ad blocker properties
        if (window.canRunAds === false || 
            window.isAdBlockActive === true ||
            document.getElementById('ad-blocker-detected')) {
            detected = true;
            console.warn('⚠️ Ad blocker detected (Method 2)');
        }
        
        // Method 3: Check if fetch is being intercepted
        const originalFetch = window.fetch;
        if (originalFetch.toString().includes('native') === false) {
            detected = true;
            console.warn('⚠️ Fetch may be intercepted (Method 3)');
        }
        
        this.adBlockerDetected = detected;
        
        if (detected) {
            console.warn('⚠️ AD BLOCKER DETECTED - May interfere with proctoring');
        } else {
            console.log('✅ No ad blocker detected');
        }
        
        return detected;
    }
    
    /**
     * Detect if developer tools are already open
     * Uses timing and window size detection methods
     */
    async detectDevTools() {
        console.log('🔍 Checking if developer tools are open...');
        
        let devToolsOpen = false;
        
        // Method 1: Check window dimensions (devtools takes up space)
        const widthThreshold = window.outerWidth - window.innerWidth > 160;
        const heightThreshold = window.outerHeight - window.innerHeight > 160;
        
        if (widthThreshold || heightThreshold) {
            devToolsOpen = true;
            console.warn('⚠️ Developer tools detected (Method 1: Window size)');
        }
        
        // Method 2: debugger statement timing check
        const startTime = performance.now();
        // eslint-disable-next-line no-debugger
        debugger;
        const endTime = performance.now();
        
        // If debugger takes more than 100ms, devtools is likely open
        if (endTime - startTime > 100) {
            devToolsOpen = true;
            console.warn('⚠️ Developer tools detected (Method 2: Debugger timing)');
        }
        
        // Method 3: Firebug check
        if (window.Firebug && window.Firebug.chrome && window.Firebug.chrome.isInitialized) {
            devToolsOpen = true;
            console.warn('⚠️ Developer tools detected (Method 3: Firebug)');
        }
        
        // Method 4: Console detection
        let consoleOpen = false;
        const element = new Image();
        Object.defineProperty(element, 'id', {
            get: function() {
                consoleOpen = true;
            }
        });
        console.log(element);
        
        if (consoleOpen) {
            devToolsOpen = true;
            console.warn('⚠️ Developer tools detected (Method 4: Console)');
        }
        
        this.devToolsDetected = devToolsOpen;
        
        if (devToolsOpen) {
            console.error('❌ DEVELOPER TOOLS ARE OPEN - Exam cannot start');
        } else {
            console.log('✅ No developer tools detected');
        }
        
        return devToolsOpen;
    }

    /**
     * Test if upload endpoint is accessible
     */
    async testUploadEndpoint() {
        console.log('🔍 Testing upload endpoint...');
        
        try {
            // Send a tiny test request
            const formData = new FormData();
            formData.append('test', 'connection');
            formData.append('csrfmiddlewaretoken', this.csrfToken);
            
            const response = await fetch(this.snapshotUploadUrl, {
                method: 'POST',
                body: formData,
            });
            
            // We expect 400 (no snapshot) but NOT network error
            if (response.status === 0 || response.type === 'error') {
                this.uploadEndpointBlocked = true;
                console.error('❌ Upload endpoint BLOCKED');
                return false;
            }
            
            this.uploadEndpointBlocked = false;
            console.log('✅ Upload endpoint accessible');
            return true;
            
        } catch (error) {
            // Network error = blocked
            if (error.name === 'TypeError' || error.message.includes('network')) {
                this.uploadEndpointBlocked = true;
                console.error('❌ Upload endpoint BLOCKED:', error.message);
                return false;
            }
            
            // Other errors are OK (like 400)
            console.log('✅ Upload endpoint accessible (with error response)');
            return true;
        }
    }
    
    /**
     * Comprehensive system check before starting
     */
    async performSystemChecks() {
        console.log('=== PROCTORING SYSTEM CHECKS ===');
        
        const checks = {
            html2canvas: false,
            screenshotTest: false,
            adBlocker: false,
            uploadEndpoint: false,
            devTools: false
        };
        
        // Check 1: html2canvas loaded
        checks.html2canvas = this.verifyHtml2Canvas();
        
        // Check 2: Screenshot capability (only if html2canvas available)
        if (checks.html2canvas) {
            checks.screenshotTest = await this.testScreenshotCapability();
        }
        
        // Check 3: Ad blocker detection
        const adBlockerDetected = await this.detectAdBlocker();
        checks.adBlocker = !adBlockerDetected; // Invert: true = good (no blocker)
        
        // Check 4: Upload endpoint
        checks.uploadEndpoint = await this.testUploadEndpoint();

        // Check 5: Developer tools detection
        const devToolsOpen = await this.detectDevTools();
        checks.devTools = !devToolsOpen;
        
        // Log results
        console.log('=== CHECK RESULTS ===');
        console.log('html2canvas:', checks.html2canvas ? '✅' : '❌');
        console.log('Screenshot capability:', checks.screenshotTest ? '✅' : '❌');
        console.log('No ad blocker:', checks.adBlocker ? '✅' : '❌');
        console.log('Upload endpoint:', checks.uploadEndpoint ? '✅' : '❌');
        console.log('No developer tools:', checks.devTools ? '✅' : '❌');
        
        // Log to backend
        await this.logEvent('system_check_completed', {
            severity: 'info',
            checks: checks,
            html2canvas_available: checks.html2canvas,
            screenshot_capable: checks.screenshotTest,
            ad_blocker_detected: !checks.adBlocker,
            upload_endpoint_blocked: !checks.uploadEndpoint,
            dev_tools_detected: !checks.devTools
        });
        
        // Critical failures
        const criticalFailures = [];
        
        if (!checks.html2canvas) {
            criticalFailures.push('Screenshot library (html2canvas) failed to load');
        }
        if (!checks.screenshotTest) {
            criticalFailures.push('Screenshot capture test failed');
        }
        if (!checks.uploadEndpoint) {
            criticalFailures.push('Upload endpoint is blocked');
        }
        if (!checks.adBlocker) {
            criticalFailures.push('Ad blocker detected - must be disabled for proctoring to work');
        }
        if (!checks.devTools) {
            criticalFailures.push('Developer tools are open - must be closed to start exam');
        }
        
        // Show warnings for non-critical issues
        if (!checks.adBlocker) {
            this.showAdBlockerWarning();
        }
        
        // Block exam if critical failures
        if (criticalFailures.length > 0) {
            this.showSystemCheckError(criticalFailures);
            return false;
        }
        
        console.log('✅ All system checks passed');
        return true;
    }
    
    /**
     * Show ad blocker warning (non-blocking)
     */
    showAdBlockerWarning() {
        const warningDiv = document.createElement('div');
        warningDiv.id = 'adblocker-warning';
        warningDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #fbbf24;
            border: 3px solid #f59e0b;
            border-radius: 8px;
            padding: 20px;
            max-width: 350px;
            z-index: 9999;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        `;
        
        warningDiv.innerHTML = `
            <div style="display: flex; align-items-start;">
                <div style="font-size: 32px; margin-right: 12px;">⚠️</div>
                <div>
                    <h3 style="font-weight: bold; margin-bottom: 8px; color: #92400e;">
                        Ad Blocker Detected
                    </h3>
                    <p style="font-size: 14px; color: #78350f; margin-bottom: 10px;">
                        An ad blocker may interfere with proctoring features.
                    </p>
                    <p style="font-size: 13px; color: #78350f; margin-bottom: 12px;">
                        <strong>Recommendation:</strong> Disable ad blockers for this site.
                    </p>
                    <button onclick="this.parentElement.parentElement.parentElement.remove()" 
                            style="background: #92400e; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                        I Understand
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(warningDiv);
        
        // Log warning accepted after 30 seconds
        setTimeout(() => {
            if (document.getElementById('adblocker-warning')) {
                this.logEvent('adblocker_warning_shown', {
                    severity: 'warning',
                    action: 'warning_shown_for_30s'
                });
            }
        }, 30000);
    }
    
    /**
     * Show system check error (blocking)
     */
    showSystemCheckError(failures) {
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border: 4px solid #dc2626;
            border-radius: 8px;
            padding: 30px;
            max-width: 600px;
            z-index: 10001;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.5);
        `;
        
        errorDiv.innerHTML = `
            <div style="text-align: center;">
                <div style="font-size: 64px; margin-bottom: 15px;">🚨</div>
                <h2 style="color: #dc2626; margin-bottom: 15px; font-size: 28px; font-weight: bold;">
                    Proctoring System Error
                </h2>
                <p style="color: #374151; margin-bottom: 20px; line-height: 1.6; font-size: 16px;">
                    <strong>The exam cannot start due to the following issues:</strong>
                </p>
                <div style="background: #fee2e2; padding: 15px; border-radius: 6px; text-align: left; margin-bottom: 20px;">
                    <ul style="list-style: none; padding: 0; margin: 0;">
                        ${failures.map(f => `
                            <li style="color: #991b1b; font-size: 14px; margin-bottom: 8px;">
                                ❌ ${f}
                            </li>
                        `).join('')}
                    </ul>
                </div>
                <div style="margin-top: 20px; padding: 15px; background: #fef3c7; border-radius: 6px;">
                    <p style="color: #92400e; font-size: 14px; margin: 0; font-weight: bold;">
                        <strong>How to fix:</strong><br><br>
                        ${failures.some(f => f.includes('Ad blocker')) ? 
                            '• Disable all browser extensions (especially ad blockers)<br>' : ''}
                        ${failures.some(f => f.includes('Developer tools')) ? 
                            '• Close Developer Tools (F12) and all browser console windows<br>' : ''}
                        ${failures.some(f => f.includes('Upload')) ? 
                            '• Check your internet connection<br>' : ''}
                        • Refresh the page after making changes<br>
                        • Try using Chrome browser in incognito mode<br>
                        • Ensure no security software is blocking the connection
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
                    margin-top: 10px;
                    width: 100%;
                ">
                    Back to Dashboard
                </button>
            </div>
        `;
        
        // Add dark overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.85);
            z-index: 10000;
        `;
        
        document.body.appendChild(overlay);
        document.body.appendChild(errorDiv);
        
        // Log to backend
        this.logEvent('system_check_failed', {
            severity: 'critical',
            failures: failures,
            note: 'Exam BLOCKED - critical proctoring failures detected'
        });
    }

    /**
     * Initialize all proctoring features
     * CRITICAL: Returns false if camera permission denied - exam should NOT start
     */
    async initialize() {
        try {

            console.log('🔍 Running system checks before initialization...');
            const systemOK = await this.performSystemChecks();
            
            if (!systemOK) {
                console.error('❌ System checks FAILED - cannot start proctoring');
                return false;
            }
            
            console.log('✅ System checks passed - proceeding with initialization');

            // 1. Request webcam access (CAMERA ONLY - NO MICROPHONE)
            const permissionsGranted = await this.requestCameraAccess();
            
            if (!permissionsGranted) {
                console.error('Camera permission denied - cannot start exam');
                this.showPermissionError();
                return false;
            }
            
            this.permissionsGranted = true;
            
            //1.1 continuous devtools monitoring
            this.startDevToolsMonitoring();

            // 2. Start continuous camera monitoring
            this.startCameraMonitoring();
            
            // 3. Setup browser lockdown (with screenshot capture on violations)
            this.setupBrowserLockdown();
            
            // 4. Setup enhanced event tracking (NEW - with away time tracking)
            this.setupEnhancedEventTracking();
            
            // 5. Force fullscreen
            this.enterFullscreen();
            
            // 6. Start snapshot timer
            this.startSnapshotTimer();
            
            // 7. Log IP address
            await this.logIPAddress();
            
            // 8. Log successful initialization
            await this.logEvent('proctoring_initialized', {
                severity: 'info',
                snapshot_interval: this.snapshotIntervalSeconds,
                event_screenshots_enabled: this.captureOnEvents,
                system_checks_passed: true,
                html2canvas_available: this.html2canvasAvailable,
                screenshot_capable: this.screenshotCapable,
                ad_blocker_detected: this.adBlockerDetected,
                features: [
                    'camera_monitoring', 
                    'browser_lockdown', 
                    'fullscreen', 
                    'periodic_screenshots',
                    'event_triggered_screenshots',
                    'away_time_tracking',
                    'system_verification'
                ]
            });
            
            console.log('✅ Enhanced proctoring system initialized successfully');
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
            
            // Log permission denied
            await this.logEvent('camera_access_denied', {
                error: error.message,
                error_name: error.name,
                severity: 'critical'
            });
            
            return false;
        }
    }

    /**
     * Continuous monitoring for developer tools being opened during exam
     */
    startDevToolsMonitoring() {
        setInterval(async () => {
            const devToolsNowOpen = await this.detectDevTools();
            
            if (devToolsNowOpen && !this.devToolsWarningShown) {
                this.devToolsWarningShown = true;
                
                // Log critical event
                await this.logEvent('devtools_opened_during_exam', {
                    severity: 'critical',
                    note: 'Developer tools opened DURING exam - potential cheating'
                });
                
                // Capture screenshot
                await this.captureEventScreenshot('devtools_violation', {
                    severity: 'critical',
                    note: 'DevTools opened during exam'
                });
                
                // Show disqualification warning
                alert('⚠️ CRITICAL VIOLATION: Developer Tools Detected\n\n' +
                    'Developer tools have been detected during the exam.\n\n' +
                    'THIS CONSTITUTES EXAM DISQUALIFICATION!\n\n' +
                    'Close developer tools immediately and continue.\n\n' +
                    'This incident has been logged and reported.');
            }
        }, 5000); // Check every 5 seconds
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
     * NEW: Setup enhanced event tracking with screenshot capture
     * Includes away time calculation and detailed focus tracking
     */
    setupEnhancedEventTracking() {
        console.log('Setting up enhanced event tracking with screenshots...');
        
        // Track tab visibility changes (tab switching)
        document.addEventListener('visibilitychange', async () => {
            if (document.hidden) {
                // User switched away - capture IMMEDIATELY before they leave
                console.log('🚨 Tab switch detected - capturing screenshot');
                
                this.warningCount++;
                
                // Capture screenshot of current state
                await this.captureEventScreenshot('tab_switch', {
                    warning_count: this.warningCount,
                    severity: this.warningCount >= this.maxWarnings ? 'critical' : 'warning',
                    blur_timestamp: new Date().toISOString()
                });
                
                // Log the event
                await this.logEvent('tab_switched', { 
                    warning_count: this.warningCount,
                    severity: this.warningCount >= this.maxWarnings ? 'critical' : 'warning'
                });
                
                // Store blur time
                this.windowBlurTime = Date.now();
                this.windowHasFocus = false;
                
                if (this.warningCount >= this.maxWarnings) {
                    alert(`Warning ${this.warningCount}/${this.maxWarnings}: Tab switching not allowed!`);
                }
            } else {
                // User returned - calculate how long they were away
                this.windowHasFocus = true;
                this.windowFocusTime = Date.now();
                
                if (this.windowBlurTime) {
                    const awayTimeSeconds = Math.round((this.windowFocusTime - this.windowBlurTime) / 1000);
                    
                    await this.logEvent('tab_returned', {
                        away_time_seconds: awayTimeSeconds,
                        severity: awayTimeSeconds > 30 ? 'warning' : 'info'
                    });
                    
                    console.log(`User returned after ${awayTimeSeconds} seconds away`);
                }
            }
        });
        
        // Track window blur (losing focus - e.g., clicking outside browser)
        window.addEventListener('blur', async () => {
            console.log('🚨 Window lost focus - capturing screenshot');
            
            // Capture screenshot
            await this.captureEventScreenshot('window_blur', {
                severity: 'warning',
                blur_timestamp: new Date().toISOString()
            });
            
            // Log event
            await this.logEvent('window_blur', { severity: 'warning' });
            
            this.windowHasFocus = false;
            this.windowBlurTime = Date.now();
        });
        
        // Track window focus (regaining focus)
        window.addEventListener('focus', async () => {
            if (!this.windowHasFocus && this.windowBlurTime) {
                const awayTimeSeconds = Math.round((Date.now() - this.windowBlurTime) / 1000);
                
                await this.logEvent('window_focus_returned', {
                    away_time_seconds: awayTimeSeconds,
                    severity: awayTimeSeconds > 30 ? 'warning' : 'info'
                });
                
                console.log(`Window focus returned after ${awayTimeSeconds} seconds`);
            }
            
            this.windowHasFocus = true;
            this.windowFocusTime = Date.now();
        });
        
        // Track fullscreen exits
        document.addEventListener('fullscreenchange', async () => {
            if (!document.fullscreenElement) {
                this.fullscreenExitCount++;
                
                console.log(`🚨 Fullscreen exit detected (${this.fullscreenExitCount}/${this.maxFullscreenExits}) - capturing screenshot`);
                
                // Capture screenshot
                await this.captureEventScreenshot('fullscreen_exit', {
                    severity: this.fullscreenExitCount >= this.maxFullscreenExits ? 'critical' : 'warning',
                    exit_count: this.fullscreenExitCount,
                    exit_timestamp: new Date().toISOString()
                });
                
                // Log event
                await this.logEvent('fullscreen_exit', { 
                    severity: this.fullscreenExitCount >= this.maxFullscreenExits ? 'critical' : 'warning',
                    exit_count: this.fullscreenExitCount,
                    max_exits: this.maxFullscreenExits
                });
                
                // Show disqualification warning
                if (this.fullscreenExitCount >= this.maxFullscreenExits) {
                    alert(`⚠️ CRITICAL WARNING: Fullscreen Exit #${this.fullscreenExitCount}\n\n` +
                        `You have exited fullscreen mode ${this.fullscreenExitCount} times.\n\n` +
                        `THIS CONSTITUTES EXAM DISQUALIFICATION!\n\n` +
                        `This incident has been logged and your exam attempt may be invalidated.\n\n` +
                        `The exam will now attempt to return to fullscreen mode.`);
                } else {
                    alert(`⚠️ WARNING: Fullscreen Exit #${this.fullscreenExitCount}/${this.maxFullscreenExits}\n\n` +
                        `Exiting fullscreen mode is not allowed during the exam.\n\n` +
                        `After ${this.maxFullscreenExits} exits, you will be DISQUALIFIED.\n\n` +
                        `This incident has been logged.\n\n` +
                        `The exam will now return to fullscreen mode.`);
                }
                
                // Try to re-enter fullscreen after alert
                setTimeout(() => this.enterFullscreen(), 100);
            }
        });
        
        console.log('✓ Enhanced event tracking enabled');
    }
    
    /**
     * Setup browser lockdown features (with screenshot capture on violations)
     */
    setupBrowserLockdown() {
        // Right-click attempts with screenshot capture after multiple attempts
        let rightClickCount = 0;
        document.addEventListener('contextmenu', async (e) => {
            e.preventDefault();
            rightClickCount++;
            
            // Capture screenshot after multiple attempts
            if (rightClickCount >= 3) {
                console.log('🚨 Multiple right-click attempts - capturing screenshot');
                await this.captureEventScreenshot('right_click_violation', {
                    attempt_count: rightClickCount,
                    severity: 'warning'
                });
            }
            
            await this.logEvent('right_click_blocked', { 
                attempt_count: rightClickCount,
                severity: rightClickCount >= 3 ? 'warning' : 'info'
            });
        });
        
        // Keyboard shortcut attempts with screenshot capture
        let shortcutAttempts = 0;
        document.addEventListener('keydown', async (e) => {
            // Dev tools attempts
            if (e.key === 'F12' || 
                (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'J')) ||
                (e.ctrlKey && e.key === 'U')) {
                e.preventDefault();
                shortcutAttempts++;
                
                // Capture screenshot after multiple attempts
                if (shortcutAttempts >= 3) {
                    console.log('🚨 Multiple devtools attempts - capturing screenshot');
                    await this.captureEventScreenshot('devtools_violation', {
                        attempt_count: shortcutAttempts,
                        severity: 'warning'
                    });
                }
                
                await this.logEvent('devtools_blocked', { 
                    attempt_count: shortcutAttempts,
                    severity: shortcutAttempts >= 3 ? 'warning' : 'info'
                });
            }
            
            // Copy/paste attempts with immediate screenshot
            if (e.ctrlKey && (e.key === 'c' || e.key === 'v')) {
                e.preventDefault();
                
                console.log('🚨 Copy/paste attempt - capturing screenshot');
                await this.captureEventScreenshot('copy_paste_attempt', {
                    action: e.key === 'c' ? 'copy' : 'paste',
                    severity: 'warning'
                });
                
                await this.logEvent('copy_paste_blocked', { 
                    action: e.key === 'c' ? 'copy' : 'paste',
                    severity: 'warning'
                });
            }
        });
        
        console.log('✓ Browser lockdown enabled with screenshot capture');
    }
    
    /**
     * NEW: Capture screenshot triggered by specific event
     * These are saved separately from periodic snapshots
     */
    async captureEventScreenshot(eventType, metadata = {}) {
        if (!this.captureOnEvents) {
            console.log('Event screenshots disabled');
            return;
        }
        
        // Cooldown check - prevent duplicate screenshots
        const now = Date.now();
        if (now - this.lastEventScreenshotTime < this.eventScreenshotCooldown) {
            console.log('Event screenshot cooldown active, skipping');
            return;
        }
        
        this.lastEventScreenshotTime = now;
        
        try {
            // Small delay to capture the last state before user leaves
            await new Promise(resolve => setTimeout(resolve, this.eventScreenshotDelay));
            
            console.log(`📸 Capturing event-triggered screenshot: ${eventType}`);
            
            // Capture screenshot using html2canvas
            const canvas = await html2canvas(document.body, {
                allowTaint: true,
                useCORS: true,
                logging: false,
                scale: 0.5,  // Same as periodic screenshots
                backgroundColor: '#ffffff',
                removeContainer: true,
                imageTimeout: 5000,  // Faster timeout for event captures
                onclone: (clonedDoc) => {
                    // Remove problematic elements
                    const problematic = clonedDoc.querySelectorAll('video, iframe, embed');
                    problematic.forEach(el => el.remove());
                }
            });
            
            // Convert to blob
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/jpeg', 0.6);
            });
            
            if (!blob) {
                console.error('Failed to create blob from canvas');
                return;
            }
            
            // Upload with special event type marker
            await this.uploadEventSnapshot(blob, eventType, metadata);
            
            console.log(`✓ Event screenshot captured: ${eventType}`);
            
        } catch (error) {
            console.error(`✗ Failed to capture event screenshot (${eventType}):`, error);
            
            // Log the failure
            await this.logEvent('event_screenshot_failed', {
                event_type: eventType,
                error: error.message,
                severity: 'info'
            });
        }
    }
    
    /**
     * Upload event-triggered snapshot with special metadata
     */
    async uploadEventSnapshot(blob, eventType, metadata = {}) {
        const formData = new FormData();
        formData.append('snapshot', blob, `event_${eventType}_${Date.now()}.jpg`);
        formData.append('snapshot_type', `event_${eventType}`);  // Special type for events
        formData.append('event_metadata', JSON.stringify(metadata));
        formData.append('csrfmiddlewaretoken', this.csrfToken);
        
        try {
            const response = await fetch(this.snapshotUploadUrl, {
                method: 'POST',
                body: formData,
            });
            
            if (!response.ok) {
                throw new Error(`Upload failed: ${response.status}`);
            }
            
            console.log(`✓ Event snapshot uploaded: ${eventType}`);
            
        } catch (error) {
            console.error('Event snapshot upload error:', error);
        }
    }
    
    /**
     * Capture and upload webcam snapshot (periodic)
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
            await this.uploadSnapshot(blob, 'webcam');
            
            console.log('✓ Webcam snapshot captured and uploaded');
        } catch (error) {
            console.error('✗ Failed to capture webcam snapshot:', error);
        }
    }
    
    /**
     * Capture and upload screen screenshot (periodic)
     */
    async captureScreenshot() {
        // Check if capable
        if (!this.screenshotCapable || !this.html2canvasAvailable) {
            console.warn('⚠️ Screenshot skipped - not capable');
            await this.logEvent('screenshot_skipped', {
                severity: 'warning',
                reason: 'not_capable',
                html2canvas_available: this.html2canvasAvailable,
                screenshot_capable: this.screenshotCapable
            });
            return;
        }
        
        try {
            const canvas = await html2canvas(document.body, {
                allowTaint: true,
                useCORS: true,
                logging: false,
                scale: 0.5,
                backgroundColor: '#ffffff',
                removeContainer: true,
                imageTimeout: 15000
            });
            
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/jpeg', 0.6);
            });
            
            if (!blob) {
                throw new Error('Failed to create blob from canvas');
            }
            
            await this.uploadSnapshot(blob, 'screen');
            console.log('✓ Screen screenshot captured');
            
        } catch (error) {
            console.error('✗ Screenshot failed:', error);
            
            // Log failure to backend
            await this.logEvent('screenshot_failed', {
                severity: 'warning',
                error: error.message,
                timestamp: new Date().toISOString()
            });
        }
    }
    
    /**
     * Upload standard periodic snapshot
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
        
        console.log(`✓ Snapshot timer started (every ${this.snapshotIntervalSeconds} seconds)`);
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
    }
    
    /**
     * Log IP address to database with fallback
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
     * Log proctoring event to backend
     */
    async logEvent(eventType, extraData = {}) {
        const eventData = {
            event_type: eventType,
            timestamp: new Date().toISOString(),
            metadata: extraData,
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
     * Cleanup resources when exam ends
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
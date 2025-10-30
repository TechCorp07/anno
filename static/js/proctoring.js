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
        
        // NEW: Fullscreen restoration
        this.fullscreenRetryAttempts = 0;
        this.maxFullscreenRetries = 5;
        this.isDisqualified = false;
        
        // Fullscreen
        this.isFullscreen = false;
        
        // Event screenshots
        this.captureOnEvents = true;
        this.eventScreenshotDelay = 100;
        this.lastEventScreenshotTime = 0;
        this.eventScreenshotCooldown = 2000;
        
        // NEW: Individual event tracking for cooldown
        this.lastEventScreenshot = {};
        
        // Window focus tracking
        this.windowHasFocus = true;
        this.windowBlurTime = null;
        this.windowFocusTime = null;

        // Library & capability checks
        this.html2canvasAvailable = false;
        this.screenshotCapable = false;
        this.adBlockerDetected = false;
        this.uploadEndpointBlocked = false;
        this.devToolsDetected = false;
        this.devToolsWarningShown = false;
        
        // NEW: Copy/paste tracking
        this.copyAttempts = 0;
        this.pasteAttempts = 0;
        this.selectAllAttempts = 0;
        this.selectionAttempts = 0;
        
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
        
        try {
            const testScript = document.createElement('script');
            testScript.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js';
            testScript.onerror = () => {
                detected = true;
                console.warn('⚠️ Ad blocker detected (Method 1)');
            };
            document.head.appendChild(testScript);
            
            await new Promise(resolve => setTimeout(resolve, 100));
            document.head.removeChild(testScript);
        } catch (error) {
            // Ignore
        }
        
        if (window.canRunAds === false || 
            window.isAdBlockActive === true ||
            document.getElementById('ad-blocker-detected')) {
            detected = true;
            console.warn('⚠️ Ad blocker detected (Method 2)');
        }
        
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
     */
    async detectDevTools() {
        console.log('🔍 Checking if developer tools are open...');
        
        let devToolsOpen = false;
        
        const widthThreshold = window.outerWidth - window.innerWidth > 160;
        const heightThreshold = window.outerHeight - window.innerHeight > 160;
        
        if (widthThreshold || heightThreshold) {
            devToolsOpen = true;
            console.warn('⚠️ Developer tools detected (Method 1: Window size)');
        }
        
        const startTime = performance.now();
        // eslint-disable-next-line no-debugger
        debugger;
        const endTime = performance.now();
        
        if (endTime - startTime > 100) {
            devToolsOpen = true;
            console.warn('⚠️ Developer tools detected (Method 2: Debugger timing)');
        }
        
        if (window.Firebug && window.Firebug.chrome && window.Firebug.chrome.isInitialized) {
            devToolsOpen = true;
            console.warn('⚠️ Developer tools detected (Method 3: Firebug)');
        }
        
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
            const formData = new FormData();
            formData.append('test', 'connection');
            formData.append('csrfmiddlewaretoken', this.csrfToken);
            
            const response = await fetch(this.snapshotUploadUrl, {
                method: 'POST',
                body: formData,
            });
            
            if (response.status === 0 || response.type === 'error') {
                this.uploadEndpointBlocked = true;
                console.error('❌ Upload endpoint BLOCKED');
                return false;
            }
            
            this.uploadEndpointBlocked = false;
            console.log('✅ Upload endpoint accessible');
            return true;
            
        } catch (error) {
            if (error.name === 'TypeError' || error.message.includes('network')) {
                this.uploadEndpointBlocked = true;
                console.error('❌ Upload endpoint BLOCKED:', error.message);
                return false;
            }
            
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
        
        checks.html2canvas = this.verifyHtml2Canvas();
        
        if (checks.html2canvas) {
            checks.screenshotTest = await this.testScreenshotCapability();
        }
        
        const adBlockerDetected = await this.detectAdBlocker();
        checks.adBlocker = !adBlockerDetected;
        
        checks.uploadEndpoint = await this.testUploadEndpoint();

        const devToolsOpen = await this.detectDevTools();
        checks.devTools = !devToolsOpen;
        
        console.log('=== CHECK RESULTS ===');
        console.log('html2canvas:', checks.html2canvas ? '✅' : '❌');
        console.log('Screenshot capability:', checks.screenshotTest ? '✅' : '❌');
        console.log('No ad blocker:', checks.adBlocker ? '✅' : '❌');
        console.log('Upload endpoint:', checks.uploadEndpoint ? '✅' : '❌');
        console.log('No developer tools:', checks.devTools ? '✅' : '❌');
        
        await this.logEvent('system_check_completed', {
            severity: 'info',
            checks: checks,
            html2canvas_available: checks.html2canvas,
            screenshot_capable: checks.screenshotTest,
            ad_blocker_detected: !checks.adBlocker,
            upload_endpoint_blocked: !checks.uploadEndpoint,
            dev_tools_detected: !checks.devTools
        });
        
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
        
        if (!checks.adBlocker) {
            this.showAdBlockerWarning();
        }
        
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
            <div style="display: flex; align-items: start;">
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
        
        this.logEvent('system_check_failed', {
            severity: 'critical',
            failures: failures,
            note: 'Exam BLOCKED - critical proctoring failures detected'
        });
    }

    /**
     * Initialize all proctoring features
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

            const permissionsGranted = await this.requestCameraAccess();
            
            if (!permissionsGranted) {
                console.error('Camera permission denied - cannot start exam');
                this.showPermissionError();
                return false;
            }
            
            this.permissionsGranted = true;
            
            this.startDevToolsMonitoring();
            this.startCameraMonitoring();
            this.setupBrowserLockdown();
            this.setupEnhancedEventTracking();
            
            // NEW: Setup text selection blocking
            this.setupSelectionBlocking();
            
            this.enterFullscreen();
            this.startSnapshotTimer();
            
            await this.logIPAddress();
            
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
                    'system_verification',
                    'copy_paste_blocking',
                    'text_selection_blocking',
                    'auto_disqualification'
                ]
            });
            
            console.log('✅ Complete proctoring system initialized successfully');
            console.log('   ✓ Camera monitoring active');
            console.log('   ✓ Fullscreen enforcement active');
            console.log('   ✓ Browser lockdown active');
            console.log('   ✓ Text selection blocking active');
            console.log('   ✓ Copy/paste blocking active');
            console.log('   ✓ Auto-disqualification active');
            
            return true;
        } catch (error) {
            console.error('✗ Proctoring initialization failed:', error);
            this.showPermissionError();
            return false;
        }
    }
    
    /**
     * Request camera access only (NO MICROPHONE)
     */
    async requestCameraAccess() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 }
                },
                audio: false
            });
            
            this.videoStream = stream;
            
            const videoTrack = stream.getVideoTracks()[0];
            if (!videoTrack || !videoTrack.enabled) {
                console.error('Camera not available or disabled');
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                }
                return false;
            }
            
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
            
            if (error.name === 'NotAllowedError') {
                console.error('User denied camera permission');
            } else if (error.name === 'NotFoundError') {
                console.error('No camera found on device');
            } else if (error.name === 'NotReadableError') {
                console.error('Camera is already in use');
            }
            
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
                
                await this.logEvent('devtools_opened_during_exam', {
                    severity: 'critical',
                    note: 'Developer tools opened DURING exam - potential cheating'
                });
                
                await this.captureEventScreenshot('devtools_violation', {
                    severity: 'critical',
                    note: 'DevTools opened during exam'
                });
                
                alert('⚠️ CRITICAL VIOLATION: Developer Tools Detected\n\n' +
                    'Developer tools have been detected during the exam.\n\n' +
                    'THIS CONSTITUTES EXAM DISQUALIFICATION!\n\n' +
                    'Close developer tools immediately and continue.\n\n' +
                    'This incident has been logged and reported.');
            }
        }, 5000);
    }
    
    /**
     * Continuously monitor camera stream
     */
    startCameraMonitoring() {
        this.streamMonitorTimer = setInterval(() => {
            if (!this.videoStream) {
                this.handleCameraDisabled();
                return;
            }
            
            const videoTrack = this.videoStream.getVideoTracks()[0];
            
            if (!videoTrack) {
                this.handleCameraDisabled();
                return;
            }
            
            if (videoTrack.readyState === 'ended') {
                this.handleCameraDisabled();
                return;
            }
            
            if (!videoTrack.enabled) {
                this.handleCameraDisabled();
                return;
            }
            
            console.log('✓ Camera monitoring: Active');
        }, 2000);
        
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
     */
    handleCameraDisabled() {
        if (this.cameraDisabledWarningShown) {
            return;
        }
        
        this.cameraDisabledWarningShown = true;
        
        this.logEvent('camera_disabled', {
            severity: 'critical',
            timestamp: new Date().toISOString(),
            note: 'Camera was disabled or disconnected during exam'
        });
        
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
     * Setup enhanced event tracking with screenshot capture
     */
    setupEnhancedEventTracking() {
        console.log('Setting up enhanced event tracking with screenshots...');
        
        document.addEventListener('visibilitychange', async () => {
            if (document.hidden) {
                console.log('🚨 Tab switch detected - capturing screenshot');
                
                this.warningCount++;
                
                await this.captureEventScreenshot('tab_switch', {
                    warning_count: this.warningCount,
                    severity: this.warningCount >= this.maxWarnings ? 'critical' : 'warning',
                    blur_timestamp: new Date().toISOString()
                });
                
                await this.logEvent('tab_switched', { 
                    warning_count: this.warningCount,
                    severity: this.warningCount >= this.maxWarnings ? 'critical' : 'warning'
                });
                
                this.windowBlurTime = Date.now();
                this.windowHasFocus = false;
                
                if (this.warningCount >= this.maxWarnings) {
                    alert(`Warning ${this.warningCount}/${this.maxWarnings}: Tab switching not allowed!`);
                }
            } else {
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
        
        window.addEventListener('blur', async () => {
            console.log('🚨 Window lost focus - capturing screenshot');
            
            await this.captureEventScreenshot('window_blur', {
                severity: 'warning',
                blur_timestamp: new Date().toISOString()
            });
            
            await this.logEvent('window_blur', { severity: 'warning' });
            
            this.windowHasFocus = false;
            this.windowBlurTime = Date.now();
        });
        
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
        
        const fullscreenChangeHandler = async () => {
            // Check fullscreen state across ALL browsers
            const isFullscreen = !!(
                document.fullscreenElement ||
                document.mozFullScreenElement ||
                document.webkitFullscreenElement ||
                document.msFullscreenElement
            );
            
            console.log('🔍 Fullscreen state:', {
                isFullscreen: isFullscreen,
                exitCount: this.fullscreenExitCount,
                maxExits: this.maxFullscreenExits,
                isDisqualified: this.isDisqualified
            });
            
            // Only process if exiting fullscreen and not already disqualified
            if (!isFullscreen && !this.isDisqualified) {
                this.fullscreenExitCount++;
                this.fullscreenRetryAttempts = 0;
                
                console.log(`🚨 Fullscreen exit detected (${this.fullscreenExitCount}/${this.maxFullscreenExits})`);
                
                await this.captureEventScreenshot('fullscreen_exit', {
                    severity: this.fullscreenExitCount >= this.maxFullscreenExits ? 'critical' : 'warning',
                    exit_count: this.fullscreenExitCount,
                    exit_timestamp: new Date().toISOString()
                });
                
                await this.logEvent('fullscreen_exit', { 
                    severity: this.fullscreenExitCount >= this.maxFullscreenExits ? 'critical' : 'warning',
                    exit_count: this.fullscreenExitCount,
                    max_exits: this.maxFullscreenExits
                });
                
                // Check if disqualification threshold reached
                if (this.fullscreenExitCount >= this.maxFullscreenExits) {
                    console.error(`❌ DISQUALIFICATION TRIGGERED: ${this.fullscreenExitCount} exits`);
                    this.isDisqualified = true;
                    
                    alert(`⚠️ EXAM DISQUALIFIED\n\n` +
                        `You have exited fullscreen mode ${this.fullscreenExitCount} times.\n\n` +
                        `The maximum allowed is ${this.maxFullscreenExits} exits.\n\n` +
                        `Your exam will now be submitted with a score of 0%.\n\n` +
                        `This incident has been logged.`);
                    
                    // Disable all interactions immediately
                    document.body.style.pointerEvents = 'none';
                    document.body.style.opacity = '0.5';
                    
                    // Force submission
                    await this.autoSubmitTestDisqualified();
                    
                } else {
                    const remaining = this.maxFullscreenExits - this.fullscreenExitCount;
                    alert(`⚠️ WARNING: Fullscreen Exit #${this.fullscreenExitCount}/${this.maxFullscreenExits}\n\n` +
                        `Exiting fullscreen mode is not allowed during the exam.\n\n` +
                        `You have ${remaining} warning(s) remaining.\n\n` +
                        `After ${this.maxFullscreenExits} exits, you will be DISQUALIFIED.\n\n` +
                        `The exam will now return to fullscreen mode.`);
                    
                    await this.restoreFullscreenWithRetry();
                }
            }
        };

        // Register event listeners for ALL browser types (CRITICAL FIX)
        const fullscreenEvents = [
            'fullscreenchange',        // Chrome, Edge, Opera
            'mozfullscreenchange',     // Firefox
            'webkitfullscreenchange',  // Safari
            'MSFullscreenChange'       // IE11
        ];

        console.log('📋 Registering fullscreen event listeners for all browsers...');
        fullscreenEvents.forEach(eventName => {
            document.addEventListener(eventName, fullscreenChangeHandler.bind(this));
            console.log(`✓ Registered: ${eventName}`);
        });

        console.log('✓ Enhanced event tracking enabled');
    }
    
    /**
     * NEW: Restore fullscreen mode with retry mechanism
     */
    async restoreFullscreenWithRetry() {
        await this.sleep(300);
        
        const attemptFullscreen = async () => {
            this.fullscreenRetryAttempts++;
            
            console.log(`Attempting to restore fullscreen (attempt ${this.fullscreenRetryAttempts}/${this.maxFullscreenRetries})...`);
            
            try {
                const elem = document.documentElement;
                
                if (elem.requestFullscreen) {
                    await elem.requestFullscreen();
                    console.log('✓ Fullscreen restored successfully');
                    return true;
                } else if (elem.mozRequestFullScreen) {
                    await elem.mozRequestFullScreen();
                    return true;
                } else if (elem.webkitRequestFullscreen) {
                    await elem.webkitRequestFullscreen();
                    return true;
                } else if (elem.msRequestFullscreen) {
                    await elem.msRequestFullscreen();
                    return true;
                }
            } catch (error) {
                console.error(`✗ Fullscreen restore attempt ${this.fullscreenRetryAttempts} failed:`, error);
                return false;
            }
            
            return false;
        };
        
        let success = await attemptFullscreen();
        
        while (!success && this.fullscreenRetryAttempts < this.maxFullscreenRetries) {
            await this.sleep(500 * this.fullscreenRetryAttempts);
            success = await attemptFullscreen();
        }
        
        if (!success) {
            console.error('✗ Failed to restore fullscreen after maximum retries');
            await this.logEvent('fullscreen_restore_failed', {
                severity: 'critical',
                retry_attempts: this.fullscreenRetryAttempts,
                exit_count: this.fullscreenExitCount
            });
        }
    }
    
    /**
     * Auto-submit test when disqualified with multiple fallbacks
     */
    async autoSubmitTestDisqualified() {
        console.log('🚫 Auto-submitting test due to disqualification...');
        
        // Log the disqualification event
        await this.logEvent('exam_disqualified', {
            severity: 'critical',
            reason: 'excessive_fullscreen_exits',
            exit_count: this.fullscreenExitCount,
            timestamp: new Date().toISOString()
        });
        
        await this.sleep(1000);
        
        // Method 1: Try POST form submission
        try {
            console.log('📝 Attempting POST form submission...');
            
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/attempt/${this.attemptId}/submit/`;
            
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrfmiddlewaretoken';
            csrfInput.value = this.csrfToken;
            form.appendChild(csrfInput);
            
            const disqualifiedInput = document.createElement('input');
            disqualifiedInput.type = 'hidden';
            disqualifiedInput.name = 'disqualified';
            disqualifiedInput.value = 'true';
            form.appendChild(disqualifiedInput);
            
            const reasonInput = document.createElement('input');
            reasonInput.type = 'hidden';
            reasonInput.name = 'disqualification_reason';
            reasonInput.value = `Excessive fullscreen exits (${this.fullscreenExitCount} times)`;
            form.appendChild(reasonInput);
            
            document.body.appendChild(form);
            form.submit();
            
            // Safety timeout: if page doesn't redirect, force it
            setTimeout(() => {
                console.warn('⚠️ Form submission timeout - using fallback');
                window.location.href = `/attempt/${this.attemptId}/submit/?disqualified=true&reason=fullscreen_exits_${this.fullscreenExitCount}`;
            }, 3000);
            
        } catch (error) {
            console.error('❌ POST form submission failed:', error);
            
            // Method 2: Fallback to GET navigation
            console.log('🔄 Using fallback: GET navigation');
            window.location.href = `/attempt/${this.attemptId}/submit/?disqualified=true&reason=fullscreen_exits_${this.fullscreenExitCount}`;
        }
    }
    
    /**
     * Setup comprehensive text selection and copy/paste blocking
     */
    setupSelectionBlocking() {
        console.log('🔒 Setting up comprehensive text selection blocking...');
        
        const style = document.createElement('style');
        style.textContent = `
            body, * {
                -webkit-user-select: none !important;
                -moz-user-select: none !important;
                -ms-user-select: none !important;
                user-select: none !important;
                -webkit-touch-callout: none !important;
            }
            
            input[type="text"],
            input[type="number"],
            input[type="email"],
            textarea {
                -webkit-user-select: text !important;
                -moz-user-select: text !important;
                -ms-user-select: text !important;
                user-select: text !important;
            }
            
            * {
                -webkit-user-drag: none !important;
                -moz-user-drag: none !important;
                user-drag: none !important;
            }
        `;
        document.head.appendChild(style);
        
        document.addEventListener('selectstart', async (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return true;
            }
            
            e.preventDefault();
            this.selectionAttempts++;
            
            console.log(`🚨 Text selection attempt blocked (#${this.selectionAttempts})`);
            
            if (this.selectionAttempts % 3 === 0) {
                await this.captureEventScreenshot('text_selection_attempt', {
                    attempt_count: this.selectionAttempts,
                    severity: 'warning'
                });
            }
            
            await this.logEvent('text_selection_blocked', {
                attempt_count: this.selectionAttempts,
                severity: this.selectionAttempts >= 3 ? 'warning' : 'info'
            });
            
            return false;
        });
        
        document.addEventListener('dragstart', async (e) => {
            e.preventDefault();
            console.log('🚨 Drag attempt blocked');
            
            await this.logEvent('drag_blocked', {
                severity: 'info'
            });
            
            return false;
        });
        
        document.addEventListener('selectionchange', async () => {
            const selection = window.getSelection();
            
            if (selection && selection.toString().length > 0) {
                const activeElement = document.activeElement;
                
                if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) {
                    return;
                }
                
                selection.removeAllRanges();
                
                this.selectionAttempts++;
                
                if (this.selectionAttempts % 5 === 0) {
                    console.log(`🚨 Persistent selection attempts detected (${this.selectionAttempts})`);
                    
                    await this.logEvent('persistent_selection_attempts', {
                        attempt_count: this.selectionAttempts,
                        severity: 'warning'
                    });
                }
            }
        });
        
        console.log('✓ Text selection blocking enabled');
    }
    
    /**
     * Setup browser lockdown with enhanced copy/paste blocking
     */
    setupBrowserLockdown() {
        console.log('🔒 Setting up enhanced browser lockdown...');
        
        let rightClickCount = 0;
        document.addEventListener('contextmenu', async (e) => {
            e.preventDefault();
            rightClickCount++;
            
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
            
            return false;
        });
        
        document.addEventListener('keydown', async (e) => {
            let blocked = false;
            let eventType = '';
            let action = '';
            
            if (e.key === 'F12' || 
                (e.ctrlKey && e.shiftKey && ['I', 'i', 'J', 'j', 'C', 'c'].includes(e.key)) ||
                (e.ctrlKey && ['U', 'u'].includes(e.key))) {
                blocked = true;
                eventType = 'devtools_blocked';
                action = 'devtools';
            }
            
            // NEW: Block Ctrl+C
            if (e.ctrlKey && ['C', 'c'].includes(e.key)) {
                if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                    blocked = true;
                    eventType = 'copy_blocked';
                    action = 'copy';
                    this.copyAttempts++;
                    
                    console.log(`🚨 Copy attempt blocked (Ctrl+C) - #${this.copyAttempts}`);
                    
                    if (this.copyAttempts % 3 === 0) {
                        await this.captureEventScreenshot('copy_attempt', {
                            attempt_count: this.copyAttempts,
                            severity: 'warning',
                            method: 'keyboard'
                        });
                    }
                }
            }
            
            // NEW: Block Ctrl+V
            if (e.ctrlKey && ['V', 'v'].includes(e.key)) {
                if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                    blocked = true;
                    eventType = 'paste_blocked';
                    action = 'paste';
                    this.pasteAttempts++;
                    
                    console.log(`🚨 Paste attempt blocked (Ctrl+V) - #${this.pasteAttempts}`);
                    
                    if (this.pasteAttempts % 3 === 0) {
                        await this.captureEventScreenshot('paste_attempt', {
                            attempt_count: this.pasteAttempts,
                            severity: 'warning',
                            method: 'keyboard'
                        });
                    }
                }
            }
            
            // NEW: Block Ctrl+A
            if (e.ctrlKey && ['A', 'a'].includes(e.key)) {
                if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                    blocked = true;
                    eventType = 'select_all_blocked';
                    action = 'select_all';
                    this.selectAllAttempts++;
                    
                    console.log(`🚨 Select All attempt blocked (Ctrl+A) - #${this.selectAllAttempts}`);
                    
                    if (this.selectAllAttempts % 3 === 0) {
                        await this.captureEventScreenshot('select_all_attempt', {
                            attempt_count: this.selectAllAttempts,
                            severity: 'warning'
                        });
                    }
                }
            }
            
            if ((e.ctrlKey || e.metaKey) && ['P', 'p'].includes(e.key)) {
                blocked = true;
                eventType = 'print_blocked';
                action = 'print';
            }
            
            if ((e.ctrlKey || e.metaKey) && ['S', 's'].includes(e.key)) {
                blocked = true;
                eventType = 'save_blocked';
                action = 'save';
            }
            
            if (blocked) {
                e.preventDefault();
                e.stopPropagation();
                
                await this.logEvent(eventType, {
                    action: action,
                    key: e.key,
                    severity: 'warning'
                });
                
                return false;
            }
        });
        
        document.addEventListener('copy', async (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return true;
            }
            
            e.preventDefault();
            e.stopPropagation();
            this.copyAttempts++;
            
            console.log(`🚨 Copy event blocked (context menu) - #${this.copyAttempts}`);
            
            if (this.copyAttempts % 3 === 0) {
                await this.captureEventScreenshot('copy_attempt', {
                    attempt_count: this.copyAttempts,
                    severity: 'warning',
                    method: 'context_menu'
                });
            }
            
            await this.logEvent('copy_event_blocked', {
                action: 'copy',
                attempt_count: this.copyAttempts,
                severity: 'warning'
            });
            
            return false;
        });
        
        document.addEventListener('paste', async (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return true;
            }
            
            e.preventDefault();
            e.stopPropagation();
            this.pasteAttempts++;
            
            console.log(`🚨 Paste event blocked (context menu) - #${this.pasteAttempts}`);
            
            if (this.pasteAttempts % 3 === 0) {
                await this.captureEventScreenshot('paste_attempt', {
                    attempt_count: this.pasteAttempts,
                    severity: 'warning',
                    method: 'context_menu'
                });
            }
            
            await this.logEvent('paste_event_blocked', {
                action: 'paste',
                attempt_count: this.pasteAttempts,
                severity: 'warning'
            });
            
            return false;
        });
        
        document.addEventListener('cut', async (e) => {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return true;
            }
            
            e.preventDefault();
            e.stopPropagation();
            
            console.log('🚨 Cut event blocked');
            
            await this.logEvent('cut_event_blocked', {
                action: 'cut',
                severity: 'warning'
            });
            
            return false;
        });
        
        console.log('✓ Enhanced browser lockdown enabled');
        console.log('   ✓ Right-click disabled');
        console.log('   ✓ Ctrl+C (copy) blocked');
        console.log('   ✓ Ctrl+V (paste) blocked');
        console.log('   ✓ Ctrl+A (select all) blocked');
        console.log('   ✓ DevTools shortcuts blocked');
        console.log('   ✓ Print blocked');
        console.log('   ✓ Text selection disabled');
    }
    
    /**
     * Capture screenshot triggered by specific event
     */
    async captureEventScreenshot(eventType, metadata = {}) {
        if (!this.captureOnEvents) {
            console.log('Event screenshots disabled');
            return;
        }
        
        const now = Date.now();
        const lastCapture = this.lastEventScreenshot[eventType] || 0;
        
        if (now - lastCapture < this.eventScreenshotCooldown) {
            console.log(`⏳ Skipping ${eventType} screenshot (cooldown)`);
            return;
        }
        
        this.lastEventScreenshot[eventType] = now;
        
        try {
            await new Promise(resolve => setTimeout(resolve, this.eventScreenshotDelay));
            
            console.log(`📸 Capturing event-triggered screenshot: ${eventType}`);
            
            const canvas = await html2canvas(document.body, {
                allowTaint: true,
                useCORS: true,
                logging: false,
                scale: 0.5,
                backgroundColor: '#ffffff',
                removeContainer: true,
                imageTimeout: 5000,
                onclone: (clonedDoc) => {
                    const problematic = clonedDoc.querySelectorAll('video, iframe, embed');
                    problematic.forEach(el => el.remove());
                }
            });
            
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/jpeg', 0.6);
            });
            
            if (!blob) {
                console.error('Failed to create blob from canvas');
                return;
            }
            
            await this.uploadEventSnapshot(blob, eventType, metadata);
            
            console.log(`✓ Event screenshot captured: ${eventType}`);
            
        } catch (error) {
            console.error(`✗ Failed to capture event screenshot (${eventType}):`, error);
            
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
        formData.append('snapshot_type', `event_${eventType}`);
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
        
        const videoTrack = this.videoStream.getVideoTracks()[0];
        if (!videoTrack || videoTrack.readyState === 'ended' || !videoTrack.enabled) {
            console.warn('Camera is not active - skipping snapshot');
            return;
        }
        
        try {
            const video = document.createElement('video');
            video.srcObject = this.videoStream;
            video.play();
            
            await new Promise(resolve => {
                video.onloadedmetadata = resolve;
            });
            
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0);
            
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/jpeg', 0.6);
            });
            
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
        this.captureWebcamSnapshot();
        this.captureScreenshot();
        
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
        } else if (elem.mozRequestFullScreen) {
            elem.mozRequestFullScreen().catch(err => {
                console.error('Fullscreen request failed:', err);
            });
        } else if (elem.webkitRequestFullscreen) {
            elem.webkitRequestFullscreen().catch(err => {
                console.error('Fullscreen request failed:', err);
            });
        } else if (elem.msRequestFullscreen) {
            elem.msRequestFullscreen().catch(err => {
                console.error('Fullscreen request failed:', err);
            });
        }
    }
    
    /**
     * Log IP address to database
     */
    async logIPAddress() {
        try {
            const response = await fetch('https://api.ipify.org?format=json');
            const data = await response.json();
            
            await this.logEvent('ip_logged', { 
                ip: data.ip,
                severity: 'info'
            });
            
            console.log('✓ IP address logged:', data.ip);
        } catch (error) {
            console.error('Failed to log IP:', error);
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
     * Helper: Sleep function
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    /**
     * Cleanup resources when exam ends
     */
    cleanup() {
        if (this.streamMonitorTimer) {
            clearInterval(this.streamMonitorTimer);
        }
        
        if (this.snapshotTimer) {
            clearInterval(this.snapshotTimer);
        }
        
        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => track.stop());
        }
        
        if (document.fullscreenElement) {
            document.exitFullscreen();
        }
        
        console.log('✓ Proctoring system cleaned up');
    }
}

// Export for use in templates
window.ProctoringSystem = ProctoringSystem;
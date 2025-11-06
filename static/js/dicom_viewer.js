class DICOMViewer3D {
    constructor(containerId, dicomUrls, options = {}) {
        this.container = document.getElementById(containerId);
        this.dicomUrls = Array.isArray(dicomUrls) ? dicomUrls : [dicomUrls];
        this.options = {
            enableHotspots: options.enableHotspots || false,
            hotspotRegions: options.hotspotRegions || [],
            showCrosshairs: options.showCrosshairs !== false,
            allowWindowLevel: options.allowWindowLevel !== false,
            allowPan: options.allowPan !== false,
            allowZoom: options.allowZoom !== false,
            onCoordinateClick: options.onCoordinateClick || null,
            ...options
        };
        
        this.renderingEngineId = 'MRIViewer_' + Math.random().toString(36).substr(2, 9);
        this.viewportIds = {
            axial: 'AXIAL',
            sagittal: 'SAGITTAL',
            coronal: 'CORONAL'
        };
        
        this.renderingEngine = null;
        this.volume = null;
        this.volumeId = 'VOLUME_' + Date.now();
        this.clickedCoordinates = null;
    }
    
    async initialize() {
        try {
            console.log('Initializing 3D DICOM Viewer...');
            
            // Verify Cornerstone3D is loaded
            if (typeof cornerstone3D === 'undefined') {
                throw new Error('Cornerstone3D library not loaded');
            }
            
            // Create the UI layout
            this.createLayout();
            
            // Initialize Cornerstone3D
            await this.initializeCornerstone();
            
            // Load the DICOM volume
            await this.loadVolume();
            
            // Setup viewports
            await this.setupViewports();
            
            // Setup interactions
            this.setupInteractions();
            
            console.log('✓ 3D DICOM Viewer initialized successfully');
            return true;
            
        } catch (error) {
            console.error('Failed to initialize 3D DICOM viewer:', error);
            this.showError(error.message);
            return false;
        }
    }
    
    createLayout() {
        this.container.innerHTML = `
            <div class="mpr-viewer-container">
                <!-- Controls Bar -->
                <div class="mpr-controls">
                    <div class="control-group">
                        <button id="resetBtn" class="control-btn" title="Reset All Views">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" stroke-width="2"/>
                                <path d="M21 3v5h-5" stroke-width="2"/>
                            </svg>
                            Reset
                        </button>
                        <button id="windowLevelBtn" class="control-btn" title="Adjust Window/Level">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <rect x="3" y="3" width="18" height="18" rx="2" stroke-width="2"/>
                                <path d="M3 9h18M9 3v18" stroke-width="2"/>
                            </svg>
                            W/L
                        </button>
                        <button id="syncBtn" class="control-btn active" title="Sync Crosshairs">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                <circle cx="12" cy="12" r="10" stroke-width="2"/>
                                <path d="M12 2v20M2 12h20" stroke-width="2"/>
                            </svg>
                            Sync
                        </button>
                    </div>
                    <div class="coordinate-display" id="coordDisplay">
                        <span>Hover over image to see coordinates</span>
                    </div>
                </div>
                
                <!-- MPR Grid Layout -->
                <div class="mpr-grid">
                    <!-- Axial View (Top-Down) -->
                    <div class="mpr-viewport" id="viewport-axial">
                        <div class="viewport-label">
                            <span class="label-text">AXIAL</span>
                            <span class="label-subtext">Top-Down View</span>
                        </div>
                        <div id="${this.viewportIds.axial}" class="viewport-canvas"></div>
                    </div>
                    
                    <!-- Sagittal View (Left-Right) -->
                    <div class="mpr-viewport" id="viewport-sagittal">
                        <div class="viewport-label">
                            <span class="label-text">SAGITTAL</span>
                            <span class="label-subtext">Left-Right View</span>
                        </div>
                        <div id="${this.viewportIds.sagittal}" class="viewport-canvas"></div>
                    </div>
                    
                    <!-- Coronal View (Front-Back) -->
                    <div class="mpr-viewport" id="viewport-coronal">
                        <div class="viewport-label">
                            <span class="label-text">CORONAL</span>
                            <span class="label-subtext">Front-Back View</span>
                        </div>
                        <div id="${this.viewportIds.coronal}" class="viewport-canvas"></div>
                    </div>
                    
                    <!-- 3D Volume Rendering (Optional) -->
                    <div class="mpr-viewport" id="viewport-3d">
                        <div class="viewport-label">
                            <span class="label-text">3D VOLUME</span>
                            <span class="label-subtext">Volume Render</span>
                        </div>
                        <div class="viewport-canvas viewport-3d-placeholder">
                            <div class="placeholder-content">
                                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                    <path d="M12 2L2 7l10 5 10-5-10-5z" stroke-width="2"/>
                                    <path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke-width="2"/>
                                </svg>
                                <p>3D Volume Rendering</p>
                                <small>Available in full version</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    async initializeCornerstone() {
        const { init, volumeLoader, Enums } = cornerstone3D;
        
        // Initialize Cornerstone3D
        await init();
        console.log('✓ Cornerstone3D initialized');
        
        // Register volume loader for DICOM files
        // Note: In production, you'd use cornerstone3DTools.volumeLoader
        // For now, we'll handle single DICOM or image stacks
    }
    
    async loadVolume() {
        try {
            const { utilities, Enums } = cornerstone3D;
            
            // For single DICOM or image stack
            if (this.dicomUrls.length === 1) {
                // Single slice - create pseudo-volume
                this.volumeId = await this.createImageStackVolume();
            } else {
                // Multiple slices - create proper volume
                this.volumeId = await this.createMultiSliceVolume();
            }
            
            console.log('✓ Volume loaded:', this.volumeId);
            
        } catch (error) {
            console.error('Error loading volume:', error);
            throw new Error('Failed to load DICOM data');
        }
    }
    
    async createImageStackVolume() {
        // For single image or PNG/JPG, create a pseudo 3D volume
        const { cache, volumeLoader } = cornerstone3D;
        
        // Create image IDs
        const imageIds = this.dicomUrls.map(url => {
            if (url.endsWith('.dcm')) {
                return 'wadouri:' + url;
            } else {
                return url.startsWith('http') ? url : window.location.origin + url;
            }
        });
        
        return imageIds[0]; // For now, return single image ID
    }
    
    async createMultiSliceVolume() {
        // Create volume from multiple DICOM slices
        const { volumeLoader } = cornerstone3D;
        
        const imageIds = this.dicomUrls.map(url => 'wadouri:' + url);
        
        const volume = await volumeLoader.createAndCacheVolume(this.volumeId, {
            imageIds: imageIds
        });
        
        await volume.load();
        
        return this.volumeId;
    }
    
    async setupViewports() {
        const { 
            RenderingEngine, 
            Enums, 
            setVolumesForViewports 
        } = cornerstone3D;
        
        // Create rendering engine
        this.renderingEngine = new RenderingEngine(this.renderingEngineId);
        
        // Define viewport configurations for MPR
        const viewportInputArray = [
            {
                viewportId: this.viewportIds.axial,
                type: Enums.ViewportType.ORTHOGRAPHIC,
                element: document.getElementById(this.viewportIds.axial),
                defaultOptions: {
                    orientation: Enums.OrientationAxis.AXIAL,
                    background: [0, 0, 0]
                }
            },
            {
                viewportId: this.viewportIds.sagittal,
                type: Enums.ViewportType.ORTHOGRAPHIC,
                element: document.getElementById(this.viewportIds.sagittal),
                defaultOptions: {
                    orientation: Enums.OrientationAxis.SAGITTAL,
                    background: [0, 0, 0]
                }
            },
            {
                viewportId: this.viewportIds.coronal,
                type: Enums.ViewportType.ORTHOGRAPHIC,
                element: document.getElementById(this.viewportIds.coronal),
                defaultOptions: {
                    orientation: Enums.OrientationAxis.CORONAL,
                    background: [0, 0, 0]
                }
            }
        ];
        
        // Create viewports
        this.renderingEngine.setViewports(viewportInputArray);
        
        console.log('✓ Viewports created');
        
        // Set volume for all viewports
        await this.setVolumeForViewports();
        
        // Render all viewports
        this.renderingEngine.renderViewports([
            this.viewportIds.axial,
            this.viewportIds.sagittal,
            this.viewportIds.coronal
        ]);
        
        console.log('✓ Viewports rendered');
    }
    
    async setVolumeForViewports() {
        const { setVolumesForViewports } = cornerstone3D;
        
        // For single image, we need different approach
        // Set the same image data to all 3 viewports
        const axialViewport = this.renderingEngine.getViewport(this.viewportIds.axial);
        const sagittalViewport = this.renderingEngine.getViewport(this.viewportIds.sagittal);
        const coronalViewport = this.renderingEngine.getViewport(this.viewportIds.coronal);
        
        // For demonstration with single image
        // Each viewport will show the same 2D slice
        // In production with real DICOM stack, this would show different planes
        
        const imageId = this.volumeId;
        
        await axialViewport.setImageIds([imageId]);
        await sagittalViewport.setImageIds([imageId]);
        await coronalViewport.setImageIds([imageId]);
    }
    
    setupInteractions() {
        const { utilities } = cornerstone3D;
        
        // Setup tools (zoom, pan, window/level)
        this.setupTools();
        
        // Setup crosshair synchronization
        if (this.options.showCrosshairs) {
            this.setupCrosshairs();
        }
        
        // Setup coordinate tracking
        this.setupCoordinateTracking();
        
        // Setup click handlers for hotspots
        if (this.options.enableHotspots) {
            this.setupHotspotClick();
        }
        
        // Setup control buttons
        this.setupControls();
    }
    
    setupTools() {
        // Add cornerstoneTools initialization here
        // For now, basic mouse interactions
        
        Object.values(this.viewportIds).forEach(viewportId => {
            const element = document.getElementById(viewportId);
            if (!element) return;
            
            // Mouse wheel for scrolling through slices
            element.addEventListener('wheel', (e) => {
                e.preventDefault();
                // Implement slice scrolling
            });
            
            // Middle mouse for pan
            let isPanning = false;
            let lastX = 0;
            let lastY = 0;
            
            element.addEventListener('mousedown', (e) => {
                if (e.button === 1 || (e.button === 0 && e.shiftKey)) {
                    isPanning = true;
                    lastX = e.clientX;
                    lastY = e.clientY;
                    e.preventDefault();
                }
            });
            
            element.addEventListener('mousemove', (e) => {
                if (isPanning) {
                    const deltaX = e.clientX - lastX;
                    const deltaY = e.clientY - lastY;
                    
                    const viewport = this.renderingEngine.getViewport(viewportId);
                    const camera = viewport.getCamera();
                    
                    // Pan camera
                    camera.position[0] -= deltaX * 0.5;
                    camera.position[1] += deltaY * 0.5;
                    
                    viewport.setCamera(camera);
                    viewport.render();
                    
                    lastX = e.clientX;
                    lastY = e.clientY;
                }
            });
            
            element.addEventListener('mouseup', () => {
                isPanning = false;
            });
        });
    }
    
    setupCrosshairs() {
        // Implement crosshair synchronization between views
        // When user clicks on one view, show crosshairs on all views
        
        Object.entries(this.viewportIds).forEach(([name, viewportId]) => {
            const element = document.getElementById(viewportId);
            if (!element) return;
            
            element.addEventListener('mousemove', (e) => {
                const rect = element.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                // Calculate world coordinates
                const viewport = this.renderingEngine.getViewport(viewportId);
                const canvas = viewport.getCanvas();
                
                // Draw crosshairs on all other viewports
                this.updateCrosshairs(viewportId, x, y);
            });
        });
    }
    
    updateCrosshairs(sourceViewportId, x, y) {
        // Draw crosshairs on all viewports except source
        // This provides visual feedback of where you are in 3D space
        
        Object.entries(this.viewportIds).forEach(([name, viewportId]) => {
            if (viewportId === sourceViewportId) return;
            
            const viewport = this.renderingEngine.getViewport(viewportId);
            // Draw crosshair lines
            // Implementation depends on Cornerstone3D annotation tools
        });
    }
    
    setupCoordinateTracking() {
        Object.entries(this.viewportIds).forEach(([name, viewportId]) => {
            const element = document.getElementById(viewportId);
            if (!element) return;
            
            element.addEventListener('mousemove', (e) => {
                const rect = element.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                // Get viewport
                const viewport = this.renderingEngine.getViewport(viewportId);
                
                // Convert canvas coordinates to world coordinates
                const worldPos = viewport.canvasToWorld([x, y]);
                
                // Update display
                const coordDisplay = document.getElementById('coordDisplay');
                if (coordDisplay && worldPos) {
                    coordDisplay.innerHTML = `
                        <strong>${name.toUpperCase()}:</strong> 
                        X: ${worldPos[0].toFixed(1)}mm, 
                        Y: ${worldPos[1].toFixed(1)}mm, 
                        Z: ${worldPos[2].toFixed(1)}mm
                    `;
                }
            });
        });
    }
    
    setupHotspotClick() {
        Object.entries(this.viewportIds).forEach(([name, viewportId]) => {
            const element = document.getElementById(viewportId);
            if (!element) return;
            
            element.addEventListener('click', (e) => {
                const rect = element.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                // Get viewport
                const viewport = this.renderingEngine.getViewport(viewportId);
                
                // Convert to world coordinates
                const worldPos = viewport.canvasToWorld([x, y]);
                
                this.clickedCoordinates = {
                    viewport: name,
                    canvas: { x, y },
                    world: worldPos
                };
                
                // Check if click hit any hotspot
                const hitHotspot = this.checkHotspotHit(worldPos);
                
                // Callback
                if (this.options.onCoordinateClick) {
                    this.options.onCoordinateClick(this.clickedCoordinates, hitHotspot);
                }
                
                // Visual feedback
                this.drawClickMarker(viewportId, x, y, hitHotspot);
            });
        });
    }
    
    checkHotspotHit(worldPos) {
        // Check if clicked position is within any hotspot region
        for (const hotspot of this.options.hotspotRegions) {
            if (this.isPointInHotspot(worldPos, hotspot)) {
                return hotspot;
            }
        }
        return null;
    }
    
    isPointInHotspot(point, hotspot) {
        // Simple rectangular hotspot check
        // Extend this for more complex shapes
        const [x, y, z] = point;
        
        return (
            x >= hotspot.x && x <= hotspot.x + hotspot.width &&
            y >= hotspot.y && y <= hotspot.y + hotspot.height
        );
    }
    
    drawClickMarker(viewportId, x, y, isHotspot) {
        const element = document.getElementById(viewportId);
        if (!element) return;
        
        // Create temporary marker
        const marker = document.createElement('div');
        marker.className = 'click-marker' + (isHotspot ? ' hotspot-hit' : '');
        marker.style.cssText = `
            position: absolute;
            left: ${x - 10}px;
            top: ${y - 10}px;
            width: 20px;
            height: 20px;
            border: 3px solid ${isHotspot ? '#00ff00' : '#ff0000'};
            border-radius: 50%;
            pointer-events: none;
            animation: markerPulse 0.5s ease-out;
        `;
        
        element.parentElement.appendChild(marker);
        
        // Remove after animation
        setTimeout(() => marker.remove(), 500);
    }
    
    setupControls() {
        // Reset button
        const resetBtn = document.getElementById('resetBtn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetAllViews());
        }
        
        // Window/Level button
        const windowLevelBtn = document.getElementById('windowLevelBtn');
        if (windowLevelBtn) {
            windowLevelBtn.addEventListener('click', () => this.toggleWindowLevel());
        }
        
        // Sync button
        const syncBtn = document.getElementById('syncBtn');
        if (syncBtn) {
            syncBtn.addEventListener('click', (e) => {
                this.options.showCrosshairs = !this.options.showCrosshairs;
                e.target.classList.toggle('active');
            });
        }
    }
    
    resetAllViews() {
        Object.values(this.viewportIds).forEach(viewportId => {
            const viewport = this.renderingEngine.getViewport(viewportId);
            viewport.resetCamera();
            viewport.render();
        });
        
        console.log('✓ All views reset');
    }
    
    toggleWindowLevel() {
        // Toggle window/level adjustment mode
        console.log('Window/Level adjustment mode toggled');
        // Implement W/L adjustment with mouse drag
    }
    
    getClickedCoordinates() {
        return this.clickedCoordinates;
    }
    
    showError(message) {
        this.container.innerHTML = `
            <div class="error-container">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <circle cx="12" cy="12" r="10" stroke-width="2"/>
                    <path d="M12 8v4M12 16h.01" stroke-width="2" stroke-linecap="round"/>
                </svg>
                <h3>Viewer Error</h3>
                <p>${message}</p>
            </div>
        `;
    }
    
    destroy() {
        if (this.renderingEngine) {
            this.renderingEngine.destroy();
        }
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DICOMViewer3D;
}
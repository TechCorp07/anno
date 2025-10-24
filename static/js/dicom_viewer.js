/**
 * Cornerstone3D DICOM Viewer for MRI Training Platform
 * Features: Multi-slice navigation, hotspot detection, windowing controls
 */

class DICOMViewer {
    constructor(elementId, dicomUrl, hotspotRegions = []) {
        this.element = document.getElementById(elementId);
        this.dicomUrl = dicomUrl;
        this.hotspotRegions = hotspotRegions; // Array of {x, y, width, height, label}
        this.clickedCoordinates = null;
        this.imageId = null;
        this.viewport = null;
        
        // Stack management for multi-slice viewing
        this.currentImageIndex = 0;
        this.imageIds = [];
        
        // Callback for when user clicks on image
        this.onCoordinateClick = null;
    }
    
    /**
     * Initialize the viewer
     */
    async initialize() {
        try {
            // Initialize Cornerstone3D
            await this.initializeCornerstone();
            
            // Load DICOM image
            await this.loadDICOM();
            
            // Setup interaction handlers
            this.setupInteractions();
            
            // Setup windowing controls
            this.setupWindowing();
            
            console.log('DICOM Viewer initialized successfully');
            return true;
        } catch (error) {
            console.error('Failed to initialize DICOM viewer:', error);
            this.showError('Unable to load DICOM image. Please contact support.');
            return false;
        }
    }
    
    /**
     * Initialize Cornerstone libraries
     */
    async initializeCornerstone() {
        // Initialize Cornerstone Core
        cornerstone.enable(this.element);
        
        // Enable web image loader for demo purposes
        // In production, use cornerstoneWADOImageLoader for real DICOM
        cornerstoneWebImageLoader.external.cornerstone = cornerstone;
    }
    
    /**
     * Load DICOM image(s)
     */
    async loadDICOM() {
        // For demo: Load image as web image
        // For production DICOM: Use 'wadouri:' + dicomUrl
        
        if (this.dicomUrl.endsWith('.dcm')) {
            // Real DICOM file
            this.imageId = 'wadouri:' + this.dicomUrl;
        } else {
            // Web image (PNG/JPG) for demo
            this.imageId = this.dicomUrl;
        }
        
        // Load the image
        const image = await cornerstone.loadImage(this.imageId);
        
        // Display the image
        cornerstone.displayImage(this.element, image);
        
        // Store viewport reference
        this.viewport = cornerstone.getViewport(this.element);
        
        // If multiple slices, setup stack
        if (this.imageIds.length > 1) {
            const stack = {
                currentImageIdIndex: 0,
                imageIds: this.imageIds
            };
            cornerstoneTools.addStackStateManager(this.element, ['stack']);
            cornerstoneTools.addToolState(this.element, 'stack', stack);
        }
    }
    
    /**
     * Setup interaction handlers
     */
    setupInteractions() {
        // Enable mouse click for hotspot detection
        this.element.addEventListener('click', (event) => {
            this.handleClick(event);
        });
        
        // Enable zoom with mouse wheel
        this.element.addEventListener('wheel', (event) => {
            event.preventDefault();
            const viewport = cornerstone.getViewport(this.element);
            const delta = event.deltaY < 0 ? 0.1 : -0.1;
            viewport.scale += delta;
            cornerstone.setViewport(this.element, viewport);
        });
        
        // Enable pan with mouse drag
        let isPanning = false;
        let startX, startY;
        
        this.element.addEventListener('mousedown', (event) => {
            if (event.button === 2) { // Right click
                event.preventDefault();
                isPanning = true;
                startX = event.clientX;
                startY = event.clientY;
            }
        });
        
        this.element.addEventListener('mousemove', (event) => {
            if (isPanning) {
                const viewport = cornerstone.getViewport(this.element);
                const deltaX = event.clientX - startX;
                const deltaY = event.clientY - startY;
                
                viewport.translation.x += deltaX;
                viewport.translation.y += deltaY;
                
                cornerstone.setViewport(this.element, viewport);
                
                startX = event.clientX;
                startY = event.clientY;
            }
        });
        
        this.element.addEventListener('mouseup', () => {
            isPanning = false;
        });
        
        // Prevent context menu
        this.element.addEventListener('contextmenu', (e) => e.preventDefault());
    }
    
    /**
     * Handle click on image for hotspot detection
     */
    handleClick(event) {
        const rect = this.element.getBoundingClientRect();
        
        // Get click coordinates relative to canvas
        const clickX = event.clientX - rect.left;
        const clickY = event.clientY - rect.top;
        
        // Convert to image coordinates
        const viewport = cornerstone.getViewport(this.element);
        const image = cornerstone.getEnabledElement(this.element).image;
        
        // Account for scale and translation
        const imageX = (clickX / viewport.scale) - viewport.translation.x;
        const imageY = (clickY / viewport.scale) - viewport.translation.y;
        
        // Store coordinates
        this.clickedCoordinates = {
            x: Math.round(imageX),
            y: Math.round(imageY),
            canvasX: clickX,
            canvasY: clickY
        };
        
        console.log('Clicked coordinates:', this.clickedCoordinates);
        
        // Draw marker at click location
        this.drawClickMarker(clickX, clickY);
        
        // Check if click is in any hotspot
        const hitHotspot = this.checkHotspot(imageX, imageY);
        
        // Trigger callback if provided
        if (this.onCoordinateClick) {
            this.onCoordinateClick(this.clickedCoordinates, hitHotspot);
        }
        
        return this.clickedCoordinates;
    }
    
    /**
     * Check if coordinates are within any hotspot region
     */
    checkHotspot(x, y) {
        for (const region of this.hotspotRegions) {
            const inX = x >= region.x && x <= region.x + region.width;
            const inY = y >= region.y && y <= region.y + region.height;
            
            if (inX && inY) {
                console.log('Hit hotspot:', region.label || 'Unnamed region');
                return region;
            }
        }
        return null;
    }
    
    /**
     * Draw click marker on canvas
     */
    drawClickMarker(x, y) {
        const canvas = this.element.querySelector('canvas');
        const ctx = canvas.getContext('2d');
        
        // Clear previous marker (redraw image first)
        cornerstone.updateImage(this.element);
        
        // Draw crosshair
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 2;
        
        // Horizontal line
        ctx.beginPath();
        ctx.moveTo(x - 20, y);
        ctx.lineTo(x + 20, y);
        ctx.stroke();
        
        // Vertical line
        ctx.beginPath();
        ctx.moveTo(x, y - 20);
        ctx.lineTo(x, y + 20);
        ctx.stroke();
        
        // Circle
        ctx.beginPath();
        ctx.arc(x, y, 10, 0, 2 * Math.PI);
        ctx.stroke();
    }
    
    /**
     * Setup windowing controls (brightness/contrast)
     */
    setupWindowing() {
        // Add preset buttons
        this.createPresetButtons();
    }
    
    /**
     * Create windowing preset buttons
     */
    createPresetButtons() {
        const presetContainer = document.getElementById('windowing-presets');
        if (!presetContainer) return;
        
        const presets = [
            { name: 'Soft Tissue', ww: 400, wc: 40 },
            { name: 'Lung', ww: 1500, wc: -600 },
            { name: 'Bone', ww: 2000, wc: 500 },
            { name: 'Brain', ww: 80, wc: 40 }
        ];
        
        presets.forEach(preset => {
            const button = document.createElement('button');
            button.textContent = preset.name;
            button.className = 'px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition';
            button.onclick = () => this.applyWindowing(preset.ww, preset.wc);
            presetContainer.appendChild(button);
        });
    }
    
    /**
     * Apply windowing settings
     */
    applyWindowing(windowWidth, windowCenter) {
        const viewport = cornerstone.getViewport(this.element);
        viewport.voi.windowWidth = windowWidth;
        viewport.voi.windowCenter = windowCenter;
        cornerstone.setViewport(this.element, viewport);
    }
    
    /**
     * Navigate to specific slice (for multi-slice DICOM)
     */
    goToSlice(index) {
        if (index >= 0 && index < this.imageIds.length) {
            this.currentImageIndex = index;
            cornerstone.loadImage(this.imageIds[index]).then(image => {
                cornerstone.displayImage(this.element, image);
            });
        }
    }
    
    /**
     * Load image stack (multiple slices)
     */
    async loadImageStack(imageUrls) {
        this.imageIds = imageUrls;
        await this.loadDICOM();
    }
    
    /**
     * Reset viewport to default
     */
    reset() {
        cornerstone.reset(this.element);
    }
    
    /**
     * Show error message
     */
    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'absolute inset-0 flex items-center justify-center bg-red-100';
        errorDiv.innerHTML = `
            <div class="text-center p-6">
                <svg class="mx-auto h-12 w-12 text-red-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <p class="text-red-700 font-semibold">${message}</p>
            </div>
        `;
        this.element.appendChild(errorDiv);
    }
    
    /**
     * Get clicked coordinates for submission
     */
    getClickedCoordinates() {
        return this.clickedCoordinates;
    }
    
    /**
     * Cleanup
     */
    destroy() {
        cornerstone.disable(this.element);
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DICOMViewer;
}
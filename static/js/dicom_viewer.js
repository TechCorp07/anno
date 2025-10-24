/**
 * SIMPLE Cornerstone DICOM Viewer for MRI Training Platform
 * Handles both DICOM (.dcm) and regular images (PNG/JPG)
 */

class DICOMViewer {
    constructor(elementId, dicomUrl, hotspotRegions = []) {
        this.element = document.getElementById(elementId);
        this.dicomUrl = dicomUrl;
        this.hotspotRegions = hotspotRegions || [];
        this.clickedCoordinates = null;
        this.imageId = null;
        this.viewport = null;
        this.canvas = null;
        this.onCoordinateClick = null;
    }
    
    async initialize() {
        try {
            console.log('Starting DICOM viewer initialization...');
            
            if (typeof cornerstone === 'undefined') {
                throw new Error('Cornerstone library not loaded');
            }
            
            // Setup canvas
            this.setupCanvas();
            
            // Register image loader FIRST
            this.registerImageLoader();
            
            // Load image
            await this.loadImage();
            
            // Setup interactions
            this.setupInteractions();
            
            console.log('✓ DICOM Viewer initialized successfully');
            return true;
        } catch (error) {
            console.error('Failed to initialize DICOM viewer:', error);
            this.showError('Unable to load image: ' + error.message);
            return false;
        }
    }
    
    setupCanvas() {
        // Create canvas if doesn't exist
        if (!this.element.querySelector('canvas')) {
            this.canvas = document.createElement('canvas');
            this.canvas.width = this.element.offsetWidth || 512;
            this.canvas.height = this.element.offsetHeight || 512;
            this.canvas.style.width = '100%';
            this.canvas.style.height = '100%';
            this.element.innerHTML = '';
            this.element.appendChild(this.canvas);
        } else {
            this.canvas = this.element.querySelector('canvas');
        }
        
        cornerstone.enable(this.canvas);
        console.log('✓ Canvas enabled');
    }
    
    registerImageLoader() {
        console.log('Checking image loader...');
        console.log('cornerstoneWebImageLoader available:', typeof cornerstoneWebImageLoader !== 'undefined');
        
        // CRITICAL: Ensure web image loader is registered
        if (typeof cornerstoneWebImageLoader === 'undefined') {
            console.error('❌ cornerstoneWebImageLoader not loaded!');
            throw new Error('Web image loader library not loaded');
        }
        
        // Set cornerstone reference
        cornerstoneWebImageLoader.external.cornerstone = cornerstone;
        
        // ALWAYS register - force it even if already registered
        try {
            cornerstone.registerImageLoader('http', cornerstoneWebImageLoader.loadImage);
            cornerstone.registerImageLoader('https', cornerstoneWebImageLoader.loadImage);
            console.log('✓ Web image loader registered for http/https');
        } catch (error) {
            console.error('Failed to register image loader:', error);
            throw error;
        }
    }
    
    async loadImage() {
        console.log('Loading image from:', this.dicomUrl);
        
        // Determine image type
        if (this.dicomUrl.endsWith('.dcm')) {
            // DICOM file
            this.imageId = 'wadouri:' + this.dicomUrl;
        } else {
            // PNG/JPG - convert to absolute URL
            this.imageId = this.makeAbsoluteUrl(this.dicomUrl);
        }
        
        console.log('Image ID:', this.imageId);
        
        try {
            const image = await cornerstone.loadImage(this.imageId);
            console.log('✓ Image loaded:', image.width, 'x', image.height);
            
            await cornerstone.displayImage(this.canvas, image);
            console.log('✓ Image displayed');
            
            this.viewport = cornerstone.getViewport(this.canvas);
        } catch (error) {
            console.error('Image load error:', error);
            throw new Error('Failed to load image: ' + error.message);
        }
    }
    
    makeAbsoluteUrl(url) {
        // Convert relative URL to absolute URL with proper scheme
        if (url.startsWith('http://') || url.startsWith('https://')) {
            return url;
        }
        
        // Create absolute URL
        const baseUrl = window.location.origin;
        if (url.startsWith('/')) {
            return baseUrl + url;
        } else {
            return baseUrl + '/' + url;
        }
    }
    
    setupInteractions() {
        // Click handler
        this.canvas.addEventListener('click', (event) => {
            this.handleClick(event);
        });
        
        // Zoom with mouse wheel
        this.canvas.addEventListener('wheel', (event) => {
            event.preventDefault();
            const viewport = cornerstone.getViewport(this.canvas);
            const delta = event.deltaY < 0 ? 0.1 : -0.1;
            viewport.scale = Math.max(0.1, Math.min(10, viewport.scale + delta));
            cornerstone.setViewport(this.canvas, viewport);
        });
        
        // Pan with drag
        let isDragging = false;
        let lastX, lastY;
        
        this.canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            lastX = e.clientX;
            lastY = e.clientY;
            this.canvas.style.cursor = 'grabbing';
        });
        
        this.canvas.addEventListener('mousemove', (e) => {
            if (isDragging) {
                const deltaX = e.clientX - lastX;
                const deltaY = e.clientY - lastY;
                const viewport = cornerstone.getViewport(this.canvas);
                viewport.translation.x += deltaX;
                viewport.translation.y += deltaY;
                cornerstone.setViewport(this.canvas, viewport);
                lastX = e.clientX;
                lastY = e.clientY;
            }
        });
        
        this.canvas.addEventListener('mouseup', () => {
            isDragging = false;
            this.canvas.style.cursor = 'crosshair';
        });
        
        this.canvas.addEventListener('mouseleave', () => {
            isDragging = false;
            this.canvas.style.cursor = 'crosshair';
        });
    }
    
    handleClick(event) {
        const rect = this.canvas.getBoundingClientRect();
        const canvasX = event.clientX - rect.left;
        const canvasY = event.clientY - rect.top;
        
        // Convert to image coordinates
        const imageCoords = this.canvasToImageCoordinates(canvasX, canvasY);
        
        this.clickedCoordinates = {
            x: Math.round(imageCoords.x),
            y: Math.round(imageCoords.y)
        };
        
        console.log('Clicked at:', this.clickedCoordinates);
        
        // Draw marker
        this.drawClickMarker(canvasX, canvasY);
        
        // Callback
        if (this.onCoordinateClick) {
            const hitHotspot = this.checkHotspotHit(this.clickedCoordinates);
            this.onCoordinateClick(this.clickedCoordinates, hitHotspot);
        }
    }
    
    canvasToImageCoordinates(canvasX, canvasY) {
        try {
            const viewport = cornerstone.getViewport(this.canvas);
            const enabledElement = cornerstone.getEnabledElement(this.canvas);
            const image = enabledElement.image;
            
            const imageX = (canvasX - viewport.translation.x) / viewport.scale;
            const imageY = (canvasY - viewport.translation.y) / viewport.scale;
            
            return {
                x: Math.max(0, Math.min(image.width, imageX)),
                y: Math.max(0, Math.min(image.height, imageY))
            };
        } catch (error) {
            return { x: canvasX, y: canvasY };
        }
    }
    
    checkHotspotHit(coords) {
        for (const hotspot of this.hotspotRegions) {
            if (coords.x >= hotspot.x && 
                coords.x <= hotspot.x + hotspot.width &&
                coords.y >= hotspot.y && 
                coords.y <= hotspot.y + hotspot.height) {
                return hotspot;
            }
        }
        return null;
    }
    
    drawClickMarker(x, y) {
        try {
            cornerstone.draw(this.canvas);
            const ctx = this.canvas.getContext('2d');
            
            ctx.strokeStyle = '#00ff00';
            ctx.lineWidth = 2;
            
            // Crosshair
            ctx.beginPath();
            ctx.moveTo(x - 20, y);
            ctx.lineTo(x + 20, y);
            ctx.stroke();
            
            ctx.beginPath();
            ctx.moveTo(x, y - 20);
            ctx.lineTo(x, y + 20);
            ctx.stroke();
            
            // Circle
            ctx.beginPath();
            ctx.arc(x, y, 10, 0, 2 * Math.PI);
            ctx.stroke();
        } catch (error) {
            console.warn('Could not draw marker:', error);
        }
    }
    
    showError(message) {
        this.element.innerHTML = `
            <div class="flex items-center justify-center h-full bg-red-900 text-red-200 rounded-lg">
                <div class="text-center p-6">
                    <svg class="mx-auto h-12 w-12 text-red-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <p class="text-red-300 font-semibold mb-2">Image Viewer Error</p>
                    <p class="text-sm text-red-400">${message}</p>
                </div>
            </div>
        `;
    }
    
    getClickedCoordinates() {
        return this.clickedCoordinates;
    }
    
    destroy() {
        try {
            if (this.canvas) {
                cornerstone.disable(this.canvas);
            }
        } catch (error) {
            console.warn('Cleanup error:', error);
        }
    }
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DICOMViewer;
}
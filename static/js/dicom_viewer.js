/**
 * FIXED: DICOM Viewer with proper canvas rendering
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
        this.usingNativeCanvas = false;  // Flag for fallback mode
        this.nativeImage = null;         // Store native image if using fallback
        this.nativeState = null;         // Store zoom/pan state for native mode
    }
    
    async initialize() {
        try {
            console.log('Starting DICOM viewer initialization...');
            
            if (typeof cornerstone === 'undefined') {
                throw new Error('Cornerstone library not loaded');
            }
            
            // Setup canvas FIRST
            this.setupCanvas();
            
            // Register image loader
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
        console.log('Setting up canvas...');
        
        // Clear existing content
        this.element.innerHTML = '';
        
        // Create canvas element
        this.canvas = document.createElement('canvas');
        
        // CRITICAL FIX: Set explicit dimensions based on container
        const containerWidth = this.element.offsetWidth || 700;
        const containerHeight = this.element.offsetHeight || 500;
        
        console.log(`Container dimensions: ${containerWidth}x${containerHeight}`);
        
        // Set canvas internal dimensions (affects rendering resolution)
        this.canvas.width = containerWidth;
        this.canvas.height = containerHeight;
        
        // Set canvas display dimensions via CSS
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.display = 'block';
        
        // CRITICAL FIX: White background for transparent PNGs
        this.canvas.style.backgroundColor = '#ffffff';
        
        // Fill canvas with white to handle transparency
        const ctx = this.canvas.getContext('2d');
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Add to DOM
        this.element.appendChild(this.canvas);
        
        // Enable Cornerstone on this canvas
        try {
            cornerstone.enable(this.canvas);
            console.log('✓ Canvas enabled for Cornerstone');
        } catch (error) {
            console.error('Failed to enable canvas:', error);
            throw error;
        }
    }
    
    registerImageLoader() {
        console.log('Registering image loaders...');
        
        // Check if web image loader is available
        if (typeof cornerstoneWebImageLoader === 'undefined') {
            console.error('❌ cornerstoneWebImageLoader not loaded!');
            throw new Error('Web image loader library not loaded');
        }
        
        // Set cornerstone reference for web image loader
        cornerstoneWebImageLoader.external.cornerstone = cornerstone;
        
        // FORCE registration (even if already registered)
        try {
            cornerstone.registerImageLoader('http', cornerstoneWebImageLoader.loadImage);
            cornerstone.registerImageLoader('https', cornerstoneWebImageLoader.loadImage);
            console.log('✓ Web image loaders registered for http/https');
        } catch (error) {
            console.warn('Image loader registration warning (may already be registered):', error);
        }
    }
    
    async loadImage() {
        console.log('Loading image from:', this.dicomUrl);
        
        // Check if this is a DICOM file or regular image
        const isDicom = this.dicomUrl.endsWith('.dcm');
        
        if (isDicom) {
            // Use Cornerstone for DICOM files
            await this.loadWithCornerstone();
        } else {
            // Try Cornerstone first, fallback to native if it fails
            try {
                await this.loadWithCornerstone();
                
                // Verify the image actually rendered
                const hasPixels = this.verifyImageRendered();
                if (!hasPixels) {
                    console.warn('⚠️ Cornerstone did not render pixels, trying native method...');
                    await this.loadWithNativeCanvas();
                }
            } catch (error) {
                console.warn('⚠️ Cornerstone failed, trying native method:', error.message);
                await this.loadWithNativeCanvas();
            }
        }
    }
    
    /**
     * Verify that the canvas actually has image pixels rendered
     */
    verifyImageRendered() {
        try {
            const ctx = this.canvas.getContext('2d');
            const imageData = ctx.getImageData(
                Math.floor(this.canvas.width / 2), 
                Math.floor(this.canvas.height / 2), 
                1, 1
            );
            const data = imageData.data;
            
            // Check if pixel is not just white/black/transparent
            const isWhite = data[0] === 255 && data[1] === 255 && data[2] === 255;
            const isBlack = data[0] === 0 && data[1] === 0 && data[2] === 0;
            const isTransparent = data[3] === 0;
            
            if (isWhite || isBlack || isTransparent) {
                // Check a few more pixels to be sure
                let coloredPixelCount = 0;
                const samples = [[50, 50], [100, 100], [150, 150]];
                
                samples.forEach(([x, y]) => {
                    if (x < this.canvas.width && y < this.canvas.height) {
                        const sampleData = ctx.getImageData(x, y, 1, 1).data;
                        if (!(sampleData[0] === 255 && sampleData[1] === 255 && sampleData[2] === 255) &&
                            !(sampleData[0] === 0 && sampleData[1] === 0 && sampleData[2] === 0) &&
                            sampleData[3] !== 0) {
                            coloredPixelCount++;
                        }
                    }
                });
                
                return coloredPixelCount > 0;
            }
            
            return true; // Has colored pixels
        } catch (error) {
            console.warn('Could not verify pixels:', error);
            return true; // Assume it worked
        }
    }
    
    /**
     * Load image using Cornerstone (for DICOM or as first attempt for PNG/JPG)
     */
    async loadWithCornerstone() {
        console.log('Attempting Cornerstone loading...');
        
        // Determine image type and create proper imageId
        if (this.dicomUrl.endsWith('.dcm')) {
            // DICOM file
            this.imageId = 'wadouri:' + this.dicomUrl;
        } else {
            // PNG/JPG - convert to absolute URL
            this.imageId = this.makeAbsoluteUrl(this.dicomUrl);
        }
        
        console.log('Image ID:', this.imageId);
        
        // Load the image
        const image = await cornerstone.loadImage(this.imageId);
        console.log(`✓ Image loaded: ${image.width}x${image.height} (min: ${image.minPixelValue}, max: ${image.maxPixelValue})`);
        
        // CRITICAL FIX: Resize canvas to match image aspect ratio
        this.resizeCanvasForImage(image);
        
        // Display the image
        await cornerstone.displayImage(this.canvas, image);
        console.log('✓ Image displayed on canvas');
        
        // CRITICAL FIX: Reset and fit viewport to show the entire image
        cornerstone.reset(this.canvas);
        console.log('✓ Viewport reset');
        
        // Fit image to canvas
        cornerstone.fitToWindow(this.canvas);
        console.log('✓ Image fitted to window');
        
        // ADDITIONAL FIX: Manually adjust viewport (especially for PNG/JPG)
        this.adjustViewportForImage();
        console.log('✓ Viewport adjusted');
        
        // Get the viewport after fitting
        this.viewport = cornerstone.getViewport(this.canvas);
        console.log('✓ Viewport after fit:', this.viewport);
        
        // Force multiple redraws to ensure visibility
        cornerstone.draw(this.canvas);
        
        // Additional draw after a brief delay (sometimes needed)
        setTimeout(() => {
            try {
                cornerstone.draw(this.canvas);
                console.log('✓ Secondary draw completed');
            } catch (e) {
                console.warn('Secondary draw failed:', e);
            }
        }, 100);
    }
    
    /**
     * Load image using native HTML5 Canvas API (fallback for PNG/JPG)
     */
    async loadWithNativeCanvas() {
        console.log('🔄 Loading with native canvas method...');
        
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous';
            
            img.onload = () => {
                console.log(`✓ Native image loaded: ${img.width}x${img.height}`);
                
                // Resize canvas to fit image
                const containerWidth = this.element.offsetWidth || 700;
                const containerHeight = this.element.offsetHeight || 500;
                const imageAspect = img.width / img.height;
                const containerAspect = containerWidth / containerHeight;
                
                let canvasWidth, canvasHeight;
                if (imageAspect > containerAspect) {
                    canvasWidth = containerWidth;
                    canvasHeight = containerWidth / imageAspect;
                } else {
                    canvasHeight = containerHeight;
                    canvasWidth = containerHeight * imageAspect;
                }
                
                this.canvas.width = Math.floor(canvasWidth);
                this.canvas.height = Math.floor(canvasHeight);
                console.log(`Canvas resized to ${this.canvas.width}x${this.canvas.height}`);
                
                // Draw white background
                const ctx = this.canvas.getContext('2d');
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
                
                // Draw image centered
                ctx.drawImage(img, 0, 0, this.canvas.width, this.canvas.height);
                console.log('✓ Image drawn to canvas with native method');
                
                // Store image reference for later use
                this.nativeImage = img;
                this.usingNativeCanvas = true;
                
                resolve();
            };
            
            img.onerror = (error) => {
                console.error('❌ Native image load failed:', error);
                reject(new Error('Failed to load image with native method'));
            };
            
            img.src = this.makeAbsoluteUrl(this.dicomUrl);
        });
    }
    
    resizeCanvasForImage(image) {
        // Calculate aspect ratio
        const imageAspect = image.width / image.height;
        const containerWidth = this.element.offsetWidth || 700;
        const containerHeight = this.element.offsetHeight || 500;
        
        let canvasWidth, canvasHeight;
        
        // Fit image to container while maintaining aspect ratio
        const containerAspect = containerWidth / containerHeight;
        
        if (imageAspect > containerAspect) {
            // Image is wider - fit to width
            canvasWidth = containerWidth;
            canvasHeight = containerWidth / imageAspect;
        } else {
            // Image is taller - fit to height
            canvasHeight = containerHeight;
            canvasWidth = containerHeight * imageAspect;
        }
        
        console.log(`Resizing canvas to ${canvasWidth}x${canvasHeight} for image ${image.width}x${image.height}`);
        
        // Update canvas dimensions
        this.canvas.width = Math.floor(canvasWidth);
        this.canvas.height = Math.floor(canvasHeight);
        
        // Also ensure the canvas is visible
        this.canvas.style.display = 'block';
        this.canvas.style.backgroundColor = '#000';
    }
    
    makeAbsoluteUrl(url) {
        // Convert relative URL to absolute URL
        if (url.startsWith('http://') || url.startsWith('https://')) {
            return url;
        }
        
        const baseUrl = window.location.origin;
        if (url.startsWith('/')) {
            return baseUrl + url;
        } else {
            return baseUrl + '/' + url;
        }
    }
    
    /**
     * Manually adjust viewport for images that don't render properly
     * This is a fallback for PNG/JPG images
     */
    adjustViewportForImage() {
        try {
            const enabledElement = cornerstone.getEnabledElement(this.canvas);
            const image = enabledElement.image;
            const viewport = cornerstone.getViewport(this.canvas);
            
            console.log('Adjusting viewport for image...');
            console.log('  Image type:', image.color ? 'Color (RGB/RGBA)' : 'Grayscale');
            console.log('  Has alpha:', image.rgba ? 'Yes' : 'No');
            
            // For PNG/JPG images, ensure proper window/level
            if (image.color) {
                // Color image - set standard RGB window/level
                console.log('Color image detected, setting standard viewport');
                
                // For transparent PNGs, we may need to adjust
                viewport.voi = {
                    windowWidth: 255,
                    windowCenter: 128
                };
                
            } else {
                // Grayscale - may need window/level adjustment
                console.log('Grayscale image, adjusting viewport...');
                
                // Set window/level based on image min/max
                const windowWidth = image.maxPixelValue - image.minPixelValue;
                const windowCenter = (image.maxPixelValue + image.minPixelValue) / 2;
                
                viewport.voi = {
                    windowWidth: windowWidth,
                    windowCenter: windowCenter
                };
                
                console.log(`Setting VOI - Width: ${windowWidth}, Center: ${windowCenter}`);
            }
            
            // Ensure scale is appropriate
            if (viewport.scale < 0.1 || viewport.scale > 10) {
                viewport.scale = 1.0;
                console.log('Reset scale to 1.0');
            }
            
            // Apply the viewport
            cornerstone.setViewport(this.canvas, viewport);
            cornerstone.draw(this.canvas);
            
            console.log('✓ Viewport applied:', viewport);
            
        } catch (error) {
            console.warn('Could not adjust viewport:', error);
        }
    }
    
    setupInteractions() {
        // Click handler for coordinate capture
        this.canvas.addEventListener('click', (event) => {
            this.handleClick(event);
        });
        
        if (this.usingNativeCanvas) {
            // Native canvas mode - implement basic zoom/pan
            this.setupNativeInteractions();
        } else {
            // Cornerstone mode - use Cornerstone's interactions
            this.setupCornerstoneInteractions();
        }
    }
    
    setupNativeInteractions() {
        let scale = 1.0;
        let translateX = 0;
        let translateY = 0;
        
        // Zoom with mouse wheel
        this.canvas.addEventListener('wheel', (event) => {
            event.preventDefault();
            const delta = event.deltaY < 0 ? 0.1 : -0.1;
            scale = Math.max(0.1, Math.min(10, scale + delta));
            this.redrawNativeCanvas(scale, translateX, translateY);
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
                translateX += deltaX;
                translateY += deltaY;
                this.redrawNativeCanvas(scale, translateX, translateY);
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
        
        // Store state for redrawing
        this.nativeState = { scale, translateX, translateY };
    }
    
    redrawNativeCanvas(scale, translateX, translateY) {
        if (!this.nativeImage) return;
        
        const ctx = this.canvas.getContext('2d');
        ctx.setTransform(1, 0, 0, 1, 0, 0); // Reset transform
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Fill background
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Apply transform
        ctx.translate(translateX, translateY);
        ctx.scale(scale, scale);
        
        // Draw image
        ctx.drawImage(this.nativeImage, 0, 0, this.canvas.width / scale, this.canvas.height / scale);
        
        // Store state
        this.nativeState = { scale, translateX, translateY };
    }
    
    setupCornerstoneInteractions() {
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
            if (this.usingNativeCanvas && this.nativeImage) {
                // Native canvas mode - direct mapping
                const scaleX = this.nativeImage.width / this.canvas.width;
                const scaleY = this.nativeImage.height / this.canvas.height;
                
                return {
                    x: Math.max(0, Math.min(this.nativeImage.width, canvasX * scaleX)),
                    y: Math.max(0, Math.min(this.nativeImage.height, canvasY * scaleY))
                };
            } else {
                // Cornerstone mode
                const viewport = cornerstone.getViewport(this.canvas);
                const enabledElement = cornerstone.getEnabledElement(this.canvas);
                const image = enabledElement.image;
                
                // Account for scale and translation
                const imageX = (canvasX - viewport.translation.x) / viewport.scale;
                const imageY = (canvasY - viewport.translation.y) / viewport.scale;
                
                return {
                    x: Math.max(0, Math.min(image.width, imageX)),
                    y: Math.max(0, Math.min(image.height, imageY))
                };
            }
        } catch (error) {
            console.warn('Coordinate conversion error:', error);
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
            if (this.usingNativeCanvas) {
                // Native canvas mode - need to redraw image first
                const ctx = this.canvas.getContext('2d');
                
                // Redraw background and image
                ctx.fillStyle = '#ffffff';
                ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
                ctx.drawImage(this.nativeImage, 0, 0, this.canvas.width, this.canvas.height);
                
                // Draw marker on top
                ctx.strokeStyle = '#00ff00';
                ctx.lineWidth = 3;
                ctx.shadowColor = '#00ff00';
                ctx.shadowBlur = 10;
                
                // Draw crosshair
                ctx.beginPath();
                ctx.moveTo(x - 20, y);
                ctx.lineTo(x + 20, y);
                ctx.stroke();
                
                ctx.beginPath();
                ctx.moveTo(x, y - 20);
                ctx.lineTo(x, y + 20);
                ctx.stroke();
                
                // Draw circle
                ctx.beginPath();
                ctx.arc(x, y, 12, 0, 2 * Math.PI);
                ctx.stroke();
                
                ctx.shadowBlur = 0;
                
            } else {
                // Cornerstone mode
                cornerstone.draw(this.canvas);
                
                const ctx = this.canvas.getContext('2d');
                ctx.strokeStyle = '#00ff00';
                ctx.lineWidth = 3;
                ctx.shadowColor = '#00ff00';
                ctx.shadowBlur = 10;
                
                // Draw crosshair
                ctx.beginPath();
                ctx.moveTo(x - 20, y);
                ctx.lineTo(x + 20, y);
                ctx.stroke();
                
                ctx.beginPath();
                ctx.moveTo(x, y - 20);
                ctx.lineTo(x, y + 20);
                ctx.stroke();
                
                // Draw circle
                ctx.beginPath();
                ctx.arc(x, y, 12, 0, 2 * Math.PI);
                ctx.stroke();
                
                ctx.shadowBlur = 0;
            }
            
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
    
    resetView() {
        try {
            if (this.usingNativeCanvas) {
                // Reset native canvas state
                this.redrawNativeCanvas(1.0, 0, 0);
                console.log('✓ Native canvas view reset');
            } else {
                // Reset Cornerstone viewport
                cornerstone.reset(this.canvas);
                this.viewport = cornerstone.getViewport(this.canvas);
                console.log('✓ Cornerstone view reset');
            }
        } catch (error) {
            console.error('Reset error:', error);
        }
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

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DICOMViewer;
}
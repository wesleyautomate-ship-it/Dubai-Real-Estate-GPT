/**
 * Utility functions for RealEstateGPT Chat Interface
 * Handles property data parsing, formatting, and validation
 */

/**
 * Safely parse property data from various response formats
 * @param {Object|Array|string} data - Property data from API
 * @returns {Array} Normalized array of property objects
 */
function parsePropertyData(data) {
    // Case 1: Already an array of objects
    if (Array.isArray(data)) {
        return data.map(normalizeProperty).filter(p => p !== null);
    }
    
    // Case 2: Object with results array
    if (data && typeof data === 'object' && Array.isArray(data.results)) {
        return data.results.map(normalizeProperty).filter(p => p !== null);
    }
    
    // Case 3: Text blob with property listings
    if (typeof data === 'string') {
        return parsePropertyText(data);
    }
    
    // Case 4: Single property object
    if (data && typeof data === 'object') {
        const normalized = normalizeProperty(data);
        return normalized ? [normalized] : [];
    }
    
    return [];
}

/**
 * Parse property data from text format
 * Expected format: "- ID: 1, Title: ..., Location: ..., Price: AED ..."
 * @param {string} text - Text containing property listings
 * @returns {Array} Array of normalized property objects
 */
function parsePropertyText(text) {
    if (!text || typeof text !== 'string') return [];
    
    const properties = [];
    const lines = text.split('\n');
    
    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.length < 10) continue;
        
        try {
            // Extract property data from line
            const property = {};
            
            // ID
            const idMatch = trimmed.match(/ID:\s*(\d+)/i);
            if (idMatch) property.id = idMatch[1];
            
            // Unit
            const unitMatch = trimmed.match(/Unit:\s*([^,]+)/i);
            if (unitMatch) property.unit = unitMatch[1].trim();
            
            // Title (fallback to unit)
            const titleMatch = trimmed.match(/Title:\s*([^,]+)/i);
            if (titleMatch) {
                property.title = titleMatch[1].trim();
            } else if (property.unit) {
                property.title = property.unit;
            }
            
            // Building
            const buildingMatch = trimmed.match(/Building:\s*([^,]+)/i);
            if (buildingMatch) property.building = buildingMatch[1].trim();
            
            // Location/Community
            const locationMatch = trimmed.match(/(?:Location|Community):\s*([^,]+)/i);
            if (locationMatch) property.location = locationMatch[1].trim();
            
            // Property Type
            const typeMatch = trimmed.match(/Type:\s*([^,]+)/i);
            if (typeMatch) property.property_type = typeMatch[1].trim();
            
            // Bedrooms
            const bedroomsMatch = trimmed.match(/Bedrooms?:\s*(\d+)/i);
            if (bedroomsMatch) property.bedrooms = parseInt(bedroomsMatch[1]);
            
            // Price
            const priceMatch = trimmed.match(/Price:\s*(?:AED\s*)?([0-9,]+)/i);
            if (priceMatch) {
                property.price = parseFloat(priceMatch[1].replace(/,/g, ''));
            }
            
            // Owner
            const ownerMatch = trimmed.match(/Owner:\s*([^,]+)/i);
            if (ownerMatch) property.owner = ownerMatch[1].trim();
            
            // Only add if we have at least a title or unit
            if (property.title || property.unit) {
                properties.push(normalizeProperty(property));
            }
        } catch (error) {
            // Silently skip malformed lines
            console.debug('Failed to parse property line:', trimmed);
        }
    }
    
    return properties.filter(p => p !== null);
}

/**
 * Normalize a property object to consistent format
 * @param {Object} property - Raw property data
 * @returns {Object|null} Normalized property or null if invalid
 */
function normalizeProperty(property) {
    if (!property || typeof property !== 'object') return null;
    
    // Must have at least a title, unit, or property_id
    if (!property.title && !property.unit && !property.property_id) {
        return null;
    }
    
    return {
        id: property.id || property.property_id || null,
        title: property.title || property.unit || 'Property',
        unit: property.unit || null,
        building: property.building || null,
        location: property.location || property.community || null,
        property_type: property.property_type || property.type || null,
        bedrooms: property.bedrooms ? parseInt(property.bedrooms) : null,
        size_sqft: property.size_sqft || property.area_sqft || null,
        price: property.price || property.price_aed || property.last_price || null,
        owner: property.owner || property.owner_name || property.buyer_name || null,
        owner_phone: property.owner_phone || null
    };
}

/**
 * Format price as AED currency
 * @param {number} price - Price value
 * @returns {string} Formatted price string
 */
function formatPrice(price) {
    if (!price || isNaN(price)) return 'N/A';
    return `AED ${Math.round(price).toLocaleString()}`;
}

/**
 * Format date string to readable format
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date
 */
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
    } catch {
        return dateString;
    }
}

/**
 * Truncate text to specified length
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
function truncateText(text, maxLength = 200) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

/**
 * Validate property search results
 * @param {Object} response - API response
 * @returns {boolean} Whether response is valid
 */
function isValidPropertyResponse(response) {
    return response 
        && typeof response === 'object'
        && (Array.isArray(response.results) || Array.isArray(response.portfolio) || Array.isArray(response.history));
}

/**
 * Extract property count from response
 * @param {Object} response - API response
 * @returns {number} Number of properties
 */
function getPropertyCount(response) {
    if (!response) return 0;
    
    if (response.total) return parseInt(response.total);
    if (response.total_properties) return parseInt(response.total_properties);
    if (response.total_transactions) return parseInt(response.total_transactions);
    if (Array.isArray(response.results)) return response.results.length;
    if (Array.isArray(response.portfolio)) return response.portfolio.length;
    if (Array.isArray(response.history)) return response.history.length;
    
    return 0;
}

/**
 * Build WhatsApp link from phone number
 * @param {string} phone - Phone number
 * @returns {string} WhatsApp URL
 */
function buildWhatsAppLink(phone) {
    if (!phone) return '#';
    const cleaned = phone.replace(/\D/g, '');
    return `https://wa.me/${cleaned}`;
}

/**
 * Sanitize HTML to prevent XSS
 * @param {string} text - Raw text
 * @returns {string} Sanitized text
 */
function sanitizeText(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export utilities for use in chat-script.js
if (typeof window !== 'undefined') {
    window.PropertyUtils = {
        parsePropertyData,
        parsePropertyText,
        normalizeProperty,
        formatPrice,
        formatDate,
        truncateText,
        isValidPropertyResponse,
        getPropertyCount,
        buildWhatsAppLink,
        sanitizeText
    };
}

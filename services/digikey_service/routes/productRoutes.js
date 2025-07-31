const express = require('express');
const ProductController = require('../controllers/ProductController');
const { loggerInfo } = require('../utils/logger');

const router = express.Router();
const productController = new ProductController();

// Middleware to log all API requests
router.use((req, res, next) => {
    loggerInfo(`${req.method} ${req.originalUrl} - ${req.ip}`);
    next();
});

/**
 * POST /api/search
 * Search products using DigiKey API and store in MongoDB
 * Body: { "query": "search_term" }
 */
router.post('/search/keyword', async (req, res) => {
    await productController.searchProducts(req, res);
});

/**
 * GET /api/products/:productNumber
 * Get product details from DigiKey API by product number and store in MongoDB
 */
router.get('/products/:productNumber/productdetails', async (req, res) => {
    await productController.getProductDetailsByNumber(req, res);
});

/**
 * GET /api/health
 * Health check endpoint
 */
router.get('/health', async (req, res) => {
    await productController.healthCheck(req, res);
});

/**
 * GET /api/stats
 * Get product statistics
 */
router.get('/stats', async (req, res) => {
    await productController.getProductStats(req, res);
});

/**
 * GET /api/
 * API information endpoint
 */
router.get('/', (req, res) => {
    res.json({
        success: true,
        service: 'DigiKey Service API',
        version: '1.0.0',
        description: 'Microservice for integrating with DigiKey API and managing product data',
        endpoints: {
            'POST /api/search': 'Search products using DigiKey API',
            'GET /api/products': 'Get stored products from database',
            'GET /api/health': 'Health check endpoint',
            'GET /api/stats': 'Get product statistics',
            'GET /api/': 'API information'
        },
        timestamp: new Date().toISOString()
    });
});

module.exports = router;
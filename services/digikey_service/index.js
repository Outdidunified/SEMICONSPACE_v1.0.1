require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { connectToDatabase } = require('./config/db');
const productRoutes = require('./routes/productRoutes');
const { loggerInfo, loggerError, loggerSuccess } = require('./utils/logger');

// Create Express application
const app = express();
const PORT = process.env.PORT || 8009;

// Middleware
app.use(cors({
    origin: process.env.CORS_ORIGIN || 'http://172.232.110.10:8000',
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
}));

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Request logging middleware
app.use((req, res, next) => {
    const startTime = Date.now();

    res.on('finish', () => {
        const duration = Date.now() - startTime;
        const logMessage = `${req.method} ${req.originalUrl} - ${res.statusCode} - ${duration}ms - ${req.ip}`;

        if (res.statusCode >= 400) {
            loggerError(logMessage);
        } else {
            loggerInfo(logMessage);
        }
    });

    next();
});

// Routes
app.use('/DigiKey', productRoutes);

// Root endpoint
app.get('/', (req, res) => {
    res.json({
        success: true,
        message: 'DigiKey Service is running',
        service: 'digikey_service',
        version: '1.0.0',
        timestamp: new Date().toISOString(),
        endpoints: {
            'GET /': 'Service information',
            'GET /api': 'API information',
            'POST /api/search': 'Search products',
            'GET /api/products': 'Get stored products',
            'GET /api/health': 'Health check',
            'GET /api/stats': 'Product statistics'
        }
    });
});

// 404 handler
app.use('*', (req, res) => {
    loggerError(`404 - Route not found: ${req.method} ${req.originalUrl}`);
    res.status(404).json({
        success: false,
        error: 'Route not found',
        message: `The requested endpoint ${req.method} ${req.originalUrl} does not exist`,
        timestamp: new Date().toISOString()
    });
});

// Global error handler
app.use((error, req, res, next) => {
    loggerError(`Global error handler: ${error.message}`);
    loggerError(`Stack trace: ${error.stack}`);

    res.status(500).json({
        success: false,
        error: 'Internal server error',
        message: 'An unexpected error occurred',
        timestamp: new Date().toISOString()
    });
});

// Graceful shutdown handler
const gracefulShutdown = (signal) => {
    loggerInfo(`Received ${signal}. Starting graceful shutdown...`);

    global.server.close(() => {
        loggerInfo('HTTP server closed');

        // Close database connection
        const { closeDatabaseConnection } = require('./config/db');
        closeDatabaseConnection()
            .then(() => {
                loggerInfo('Database connection closed');
                process.exit(0);
            })
            .catch((error) => {
                loggerError(`Error closing database connection: ${error.message}`);
                process.exit(1);
            });
    });

    // Force close after 10 seconds
    setTimeout(() => {
        loggerError('Forcing shutdown after timeout');
        process.exit(1);
    }, 10000);
};

// Handle process signals
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
    loggerError(`Uncaught Exception: ${error.message}`);
    loggerError(`Stack trace: ${error.stack}`);
    process.exit(1);
});

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
    loggerError(`Unhandled Rejection at: ${promise}, reason: ${reason}`);
    process.exit(1);
});

// Start server
async function startServer() {
    try {
        // Connect to MongoDB
        loggerInfo('Starting DigiKey Service...');
        await connectToDatabase();

        const os = require('os');
        // Start HTTP server
        const server = app.listen(PORT, () => {
            // Get local network IP address
            const interfaces = os.networkInterfaces();
            let localIp = 'localhost';
            for (const name of Object.keys(interfaces)) {
                for (const iface of interfaces[name]) {
                    if (iface.family === 'IPv4' && !iface.internal) {
                        localIp = iface.address;
                        break;
                    }
                }
                if (localIp !== 'localhost') break;
            }

            loggerSuccess(`DigiKey Service is running on http://${localIp}:${PORT}`);
            loggerInfo(`Environment: ${process.env.NODE_ENV || 'development'}`);
            loggerInfo(`Process ID: ${process.pid}`);
            loggerInfo('Service is ready to accept requests');
        });

        // Make server available for graceful shutdown
        global.server = server;

        return server;

    } catch (error) {
        loggerError(`Failed to start server: ${error.message}`);
        loggerError(`Stack trace: ${error.stack}`);
        process.exit(1);
    }
}

// Start the server
if (require.main === module) {
    startServer();
}

module.exports = app;
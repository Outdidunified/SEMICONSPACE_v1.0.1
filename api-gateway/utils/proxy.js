const proxy = require('express-http-proxy');
const { loggerDebug, loggerError, loggerSuccess, loggerWarn, loggerInfo } = require('./logger');

function createServiceProxy(target, match, authHeader) {
    // Dynamic timeout based on request type
    const getTimeout = (req) => {
        // Longer timeout for GET requests with potential large data
        if (req.method === 'GET' && !req.originalUrl.includes('/auth')) {
            return 120000; // 2 minutes for data-heavy endpoints
        }
        return 60000; // 1 minute for other requests
    };

    return proxy(target, {
        timeout: getTimeout,
        limit: '50mb', // Increase body size limit
        proxyReqPathResolver: (req) => req.originalUrl.replace(/^\/api/, ''),
        proxyReqOptDecorator: (proxyReqOpts, srcReq) => {
            const correlationId =
                srcReq.headers['x-correlation-id'] || `req-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
            proxyReqOpts.headers['x-correlation-id'] = correlationId;

            if (match !== '/auth' && authHeader) {
                proxyReqOpts.headers['authorization'] = authHeader;
            }

            if (srcReq.body && Object.keys(srcReq.body).length > 0) {
                proxyReqOpts.headers['Content-Type'] = 'application/json';
                proxyReqOpts.headers['Content-Length'] = Buffer.byteLength(JSON.stringify(srcReq.body));
            }

            // Add timeout headers
            proxyReqOpts.headers['x-request-timeout'] = getTimeout(srcReq);

            loggerDebug(`Proxying ${srcReq.method} ${srcReq.originalUrl} to ${target}${srcReq.url}`);
            return proxyReqOpts;
        },
        userResDecorator: (proxyRes, proxyResData, userReq, userRes) => {
            const status = proxyRes.statusCode;
            const fullUrl = `${target}${userReq.originalUrl.replace(/^\/api/, '')}`;
            const clientIp = userReq.headers['x-forwarded-for'] || userReq.socket.remoteAddress;

            const logMessage = `Response from [${fullUrl}] (Client: ${clientIp}) | Status: ${status}`;

            // Add performance timing headers
            const startTime = userReq.startTime || Date.now();
            const responseTime = Date.now() - startTime;
            userRes.setHeader('X-Response-Time', `${responseTime}ms`);

            if (status >= 200 && status < 300) {
                loggerSuccess(`SUCCESS - ${logMessage} (${responseTime}ms)`);
            } else if (status >= 400 && status < 500) {
                loggerWarn(`CLIENT ERROR - ${logMessage} (${responseTime}ms)`);
            } else if (status >= 500) {
                loggerError(`SERVER ERROR - ${logMessage} (${responseTime}ms)`);
            } else {
                loggerInfo(`INFO - ${logMessage} (${responseTime}ms)`);
            }

            return proxyResData;
        },
        proxyReqBodyDecorator: function (bodyContent, srcReq) {
            // Store start time for performance tracking
            srcReq.startTime = Date.now();
            return bodyContent;
        },
        proxyErrorHandler: (err, res, next) => {
            const clientIp = res.req.headers['x-forwarded-for'] || res.req.socket.remoteAddress;
            const fullUrl = `${target}${res.req.originalUrl.replace(/^\/api/, '')}`;
            const requestTime = res.req.startTime ? Date.now() - res.req.startTime : 0;

            // Enhanced error categorization
            let errorType = 'PROXY ERROR';
            let errorMessage = 'The service is unavailable';
            let statusCode = 502;

            if (err.code === 'ECONNRESET' || err.message.includes('socket hang up')) {
                errorType = 'TIMEOUT ERROR';
                errorMessage = 'Request timeout - service took too long to respond';
                statusCode = 504;
            } else if (err.code === 'ENOTFOUND' || err.code === 'ECONNREFUSED') {
                errorType = 'CONNECTION ERROR';
                errorMessage = 'Service is temporarily unavailable';
                statusCode = 503;
            } else if (err.message.includes('timeout')) {
                errorType = 'TIMEOUT ERROR';
                errorMessage = `Request timeout after ${requestTime}ms - consider pagination for large datasets`;
                statusCode = 504;
            }

            loggerError(`${errorType} - Failed to reach [${fullUrl}] (Client: ${clientIp}) | Reason: ${err.message} | Duration: ${requestTime}ms`);

            if (!res.headersSent) {
                res.status(statusCode).json({
                    error: errorType.replace(' ERROR', ''),
                    message: errorMessage,
                    service: match,
                    target,
                    duration: `${requestTime}ms`,
                    suggestion: statusCode === 504 ? 'Try adding pagination parameters (?limit=100&offset=0)' : null,
                    timestamp: new Date().toISOString()
                });
            }
        },
    });
}

module.exports = { createServiceProxy };

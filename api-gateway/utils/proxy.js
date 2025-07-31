const proxy = require('express-http-proxy');
const { loggerDebug, loggerError, loggerSuccess, loggerWarn, loggerInfo } = require('./logger');

function createServiceProxy(target, match, authHeader) {
    return proxy(target, {
        timeout: 30000, // Increased timeout to 30 seconds
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

            loggerDebug(`Proxying ${srcReq.method} ${srcReq.originalUrl} to ${target}${srcReq.url}`);
            return proxyReqOpts;
        },
        userResDecorator: (proxyRes, proxyResData, userReq, userRes) => {
            const status = proxyRes.statusCode;
            const fullUrl = `${target}${userReq.originalUrl.replace(/^\/api/, '')}`;
            const clientIp = userReq.headers['x-forwarded-for'] || userReq.socket.remoteAddress;

            const logMessage = `Response from [${fullUrl}] (Client: ${clientIp}) | Status: ${status}`;

            if (status >= 200 && status < 300) {
                loggerSuccess(`SUCCESS - ${logMessage}`);
            } else if (status >= 400 && status < 500) {
                loggerWarn(`CLIENT ERROR - ${logMessage}`);
            } else if (status >= 500) {
                loggerError(` SERVER ERROR - ${logMessage}`);
            } else {
                loggerInfo(`INFO - ${logMessage}`);
            }

            return proxyResData;
        },


        proxyErrorHandler: (err, res, next) => {
            const clientIp = res.req.headers['x-forwarded-for'] || res.req.socket.remoteAddress;
            const fullUrl = `${target}${res.req.originalUrl.replace(/^\/api/, '')}`;

            loggerError(`PROXY ERROR - Failed to reach [${fullUrl}] (Client: ${clientIp}) | Reason: ${err.message}`);

            if (!res.headersSent) {
                res.status(502).json({
                    error: 'Bad Gateway',
                    message: 'The service is unavailable',
                    service: match,
                    target,
                });
            }
        },
    });
}

module.exports = { createServiceProxy };
const jwt = require('jsonwebtoken');
const { loggerInfo, loggerError, loggerWarn } = require('../utils/logger');
const { sessionManager } = require('../utils/session_manager');

function verifyJwt(req, res, next) {
  const authHeader = req.headers['authorization'];

  if (!authHeader) {
    loggerError('Authentication failed: No authorization header');
    return res.status(401).json({ error: 'Authorization header is required' });
  }

  const parts = authHeader.split(' ');

  if (parts.length !== 2 || parts[0] !== 'Bearer') {
    loggerError('Authentication failed: Invalid authorization format');
    return res.status(401).json({ error: 'Authorization format should be: Bearer [token]' });
  }

  const token = parts[1];

  if (!token) {
    loggerError('Authentication failed: Missing token');
    return res.status(401).json({ error: 'Missing token' });
  }

  try {
    if (!process.env.JWT_SECRET) {
      loggerError('Authentication failed: JWT_SECRET not configured');
      return res.status(500).json({ error: 'Server configuration error' });
    }

    const payload = jwt.verify(token, process.env.JWT_SECRET, {
      algorithms: [process.env.JWT_ALGORITHM || 'HS256'], // ⬅️ Enforce correct algo
    });

    // Check if token has expired (additional check)
    const currentTime = Math.floor(Date.now() / 1000);
    if (payload.exp && payload.exp < currentTime) {
      loggerError('Authentication failed: Token has expired');
      return res.status(401).json({ error: 'Token has expired' });
    }

    // Validate session if sessionId is present
    if (payload.sessionId && payload.userId) {
      if (!sessionManager.isValidSession(payload.sessionId, payload.userId)) {
        loggerWarn(`Invalid session detected for user: ${payload.userId}, sessionId: ${payload.sessionId}`);
        return res.status(401).json({ error: 'Session invalid or expired', code: 'INVALID_SESSION' });
      }
    }

    req.user = payload;

    // Add user info to headers for downstream services
    if (payload.userId) req.headers['x-user-id'] = payload.userId;
    if (payload.email) req.headers['x-user-email'] = payload.email;
    if (payload.role) req.headers['x-user-role'] = payload.role;
    if (payload.sessionId) req.headers['x-session-id'] = payload.sessionId;

    loggerInfo(`Authentication successful for user: ${payload.email || payload.userId || 'unknown'} (Session: ${payload.sessionId || 'N/A'})`);
    next();
  } catch (err) {
    if (err.name === 'TokenExpiredError') {
      loggerError('Authentication failed: Token has expired');
      return res.status(401).json({ error: 'Token has expired', code: 'TOKEN_EXPIRED' });
    } else if (err.name === 'JsonWebTokenError') {
      loggerError(`Authentication failed: Invalid token - ${err.message}`);
      return res.status(401).json({ error: 'Invalid token', code: 'INVALID_TOKEN' });
    } else {
      loggerError(`Authentication failed: ${err.message}`);
      return res.status(403).json({ error: 'Authentication failed', code: 'AUTH_ERROR' });
    }
  }
}

module.exports = { verifyJwt };

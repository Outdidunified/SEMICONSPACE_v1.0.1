const jwt = require('jsonwebtoken');
const { loggerInfo, loggerError } = require('../utils/logger');

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

    req.user = payload;

    // Add user info to headers for downstream services
    if (payload.userId) req.headers['x-user-id'] = payload.userId;
    if (payload.email) req.headers['x-user-email'] = payload.email;
    if (payload.role) req.headers['x-user-role'] = payload.role;

    loggerInfo(`Authentication successful for user: ${payload.email || payload.userId || 'unknown'}`);
    next();
  } catch (err) {
    loggerError(`Authentication failed: ${err.message}`);
    return res.status(403).json({ error: 'Invalid or expired token' });
  }
}

module.exports = { verifyJwt };

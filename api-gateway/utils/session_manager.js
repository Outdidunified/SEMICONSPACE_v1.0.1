const { loggerInfo, loggerWarn, loggerDebug } = require('./logger');

class SessionManager {
    constructor() {
        this.activeSessions = new Map(); // userId -> { sessionId, lastActivity, token }
        this.sessionTokens = new Map(); // sessionId -> { userId, token, lastActivity }

        // Clean up expired sessions every 5 minutes
        setInterval(() => {
            this.cleanupExpiredSessions();
        }, 5 * 60 * 1000);
    }

    /**
     * Register a new session for a user
     * @param {string} userId 
     * @param {string} sessionId 
     * @param {string} token 
     */
    registerSession(userId, sessionId, token) {
        const now = Date.now();

        // If user already has an active session, invalidate it
        if (this.activeSessions.has(userId)) {
            const oldSession = this.activeSessions.get(userId);
            this.sessionTokens.delete(oldSession.sessionId);
            loggerInfo(`Invalidated previous session for user: ${userId}`);
        }

        // Register new session
        const sessionData = {
            sessionId,
            lastActivity: now,
            token
        };

        this.activeSessions.set(userId, sessionData);
        this.sessionTokens.set(sessionId, {
            userId,
            token,
            lastActivity: now
        });

        loggerInfo(`Registered new session for user: ${userId}, sessionId: ${sessionId}`);
    }

    /**
     * Check if a session is valid
     * @param {string} sessionId 
     * @param {string} userId 
     * @returns {boolean}
     */
    isValidSession(sessionId, userId) {
        if (!sessionId || !userId) {
            return false;
        }

        const userSession = this.activeSessions.get(userId);
        const sessionData = this.sessionTokens.get(sessionId);

        if (!userSession || !sessionData) {
            return false;
        }

        // Check if the session belongs to the user
        if (userSession.sessionId !== sessionId || sessionData.userId !== userId) {
            loggerWarn(`Session mismatch for user: ${userId}, sessionId: ${sessionId}`);
            return false;
        }

        // Update last activity
        const now = Date.now();
        userSession.lastActivity = now;
        sessionData.lastActivity = now;

        return true;
    }

    /**
     * Invalidate a specific session
     * @param {string} sessionId 
     */
    invalidateSession(sessionId) {
        const sessionData = this.sessionTokens.get(sessionId);
        if (sessionData) {
            this.activeSessions.delete(sessionData.userId);
            this.sessionTokens.delete(sessionId);
            loggerInfo(`Invalidated session: ${sessionId} for user: ${sessionData.userId}`);
        }
    }

    /**
     * Invalidate all sessions for a user
     * @param {string} userId 
     */
    invalidateUserSessions(userId) {
        const userSession = this.activeSessions.get(userId);
        if (userSession) {
            this.sessionTokens.delete(userSession.sessionId);
            this.activeSessions.delete(userId);
            loggerInfo(`Invalidated all sessions for user: ${userId}`);
        }
    }

    /**
     * Clean up expired sessions (older than 2 hours of inactivity)
     */
    cleanupExpiredSessions() {
        const now = Date.now();
        const maxInactivity = 2 * 60 * 60 * 1000; // 2 hours
        let cleanedCount = 0;

        // Clean up from sessionTokens map
        for (const [sessionId, sessionData] of this.sessionTokens.entries()) {
            if (now - sessionData.lastActivity > maxInactivity) {
                this.sessionTokens.delete(sessionId);
                this.activeSessions.delete(sessionData.userId);
                cleanedCount++;
            }
        }

        if (cleanedCount > 0) {
            loggerInfo(`Cleaned up ${cleanedCount} expired sessions`);
        }
    }

    /**
     * Get session statistics
     * @returns {object}
     */
    getStats() {
        return {
            activeSessions: this.activeSessions.size,
            totalSessions: this.sessionTokens.size,
            timestamp: new Date().toISOString()
        };
    }
}

// Create singleton instance
const sessionManager = new SessionManager();

module.exports = { sessionManager };
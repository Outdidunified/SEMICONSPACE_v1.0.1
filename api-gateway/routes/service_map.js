module.exports = {
  '/auth': {
    target: process.env.AUTH_SERVICE_URL || 'http://172.232.102.237:8001',
    protected: false,
  },
  '/user': {
    target: process.env.USER_SERVICE_URL || 'http://172.232.102.237:8002',
    protected: true,
  },
  '/product': {
    target: process.env.PRODUCT_SERVICE_URL || 'http://172.232.102.237:8003',
    protected: false,
  },
  '/search': {
    target: process.env.SEARCH_SERVICE_URL || 'http://172.232.102.237:8004',
    protected: false
  },
  '/cart': {
    target: process.env.CART_SERVICE_URL || 'http://172.232.102.237:8005',
    protected: true,
  },
  '/order': {
    target: process.env.ORDER_SERVICE_URL || 'http://172.232.102.237:8006',
    protected: true,
  },
  '/payment': {
    target: process.env.CONFIG_SERVICE_URL || 'http://172.232.102.237:8007',
    protected: true,
  },
  '/notifications': {
    target: process.env.NOTIFICATION_SERVICE_URL || 'http://172.232.102.237:8008',
    protected: true,
  },
  '/digikey': {
    target: process.env.DIGIKEY_SERVICE_URL || 'http://172.232.102.237:8009',
    protected: false,
  },
};
// frontend/src/setupProxy.js
const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  // Special handling for SSE endpoint - no buffering
  app.use(
    '/generate_events_stream',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
      // Critical: disable all buffering for SSE
      onProxyReq: (proxyReq) => {
        proxyReq.setHeader('Connection', 'keep-alive');
        proxyReq.setHeader('Cache-Control', 'no-cache');
      },
      onProxyRes: (proxyRes) => {
        // Remove any buffering headers
        delete proxyRes.headers['content-length'];
        proxyRes.headers['cache-control'] = 'no-cache';
        proxyRes.headers['connection'] = 'keep-alive';
        proxyRes.headers['x-accel-buffering'] = 'no';
      },
      // Disable all buffering and compression
      selfHandleResponse: false,
      ws: false,
      logLevel: 'debug'
    })
  );

  // Regular proxy for all other API calls
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
    })
  );

  // Proxy for generate_events (the old endpoint)
  app.use(
    '/generate_events',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
    })
  );
};

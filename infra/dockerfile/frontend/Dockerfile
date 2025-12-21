# Dockerfile for Frontend
# Simple nginx container serving static files

FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY infra/nginx/nginx.conf /etc/nginx/conf.d/

# Copy static files
COPY src/frontend/index.html /usr/share/nginx/html/
COPY src/frontend/styles.css /usr/share/nginx/html/
COPY src/frontend/script.js /usr/share/nginx/html/

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

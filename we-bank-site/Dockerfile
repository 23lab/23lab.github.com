FROM nginx:1.27-alpine

ARG BUILD_DATE
ARG VCS_REF

LABEL org.opencontainers.image.title="we-bank-site-demo" \
      org.opencontainers.image.description="Static corporate site template (demo)" \
      org.opencontainers.image.vendor="demo" \
      org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.revision=$VCS_REF

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY public /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1/ | grep -qi "</html>" || exit 1


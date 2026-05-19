# Sentinel Health — Landing Page (static)
# Serves the institutional landing + coverage page through nginx.
FROM nginx:alpine
COPY . /usr/share/nginx/html/
# Host files may be 600 (owner-only); fix perms so the nginx user (uid 101)
# inside the container can read them. Otherwise nginx returns 403.
RUN chmod -R a+rX /usr/share/nginx/html
EXPOSE 80

# STAGE 1: Build
FROM node:20-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# STAGE 2: Production (Nginx)
FROM nginx:stable-alpine as production-stage
# Copying the files from the previous phase into the Nginx folder
COPY --from=build-stage /app/dist /usr/share/nginx/html
# Expose port 80 inside the container
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
# STAGE 1: Build
FROM node:20-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# STAGE 2: Production (Nginx)
FROM nginx:stable-alpine as production-stage
# Copia i file compilati dalla fase precedente nella cartella di Nginx
COPY --from=build-stage /app/dist /usr/share/nginx/html
# Espone la porta 80 interna al container
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
FROM node:20-alpine AS builder
WORKDIR /app
ARG VITE_NURA_API_BASE=/v1
ENV VITE_NURA_API_BASE=$VITE_NURA_API_BASE
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

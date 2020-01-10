# Stage: build
FROM node:10 as build
WORKDIR /app
COPY package*.json /app/
RUN npm install
COPY . .
RUN npm run build

# Stage: runtime
FROM nginx:alpine as runtime
COPY --from=build /app/dist/alice-controller /usr/share/nginx/html/
ENTRYPOINT ["nginx", "-g", "daemon off;"]
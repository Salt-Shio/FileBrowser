# 階段一：打包建置 (Builder)
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 階段二：生產環境伺服器 (Production)
FROM nginx:alpine
# 將階段一編譯好的純靜態檔案複製到 Nginx 目錄
COPY --from=builder /app/dist /usr/share/nginx/html
# 覆蓋自訂的 Nginx 設定檔
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

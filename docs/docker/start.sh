#!/bin/bash
# Bắt đầu chương trình phụ trợ Java (nghe cổng 8003 trong docker)
java -jar /app/xiaozhi-esp32-api.jar \
  --server.port=8003 \
  --spring.datasource.druid.url=${SPRING_DATASOURCE_DRUID_URL} \
  --spring.datasource.druid.username=${SPRING_DATASOURCE_DRUID_USERNAME} \
  --spring.datasource.druid.password=${SPRING_DATASOURCE_DRUID_PASSWORD} \
  --spring.data.redis.host=${SPRING_DATA_REDIS_HOST} \
  --spring.data.redis.password=${SPRING_DATA_REDIS_PASSWORD} \
  --spring.data.redis.port=${SPRING_DATA_REDIS_PORT} &

# Khởi động Nginx (chạy ở nền trước để giữ cho container tồn tại)
nginx -g 'daemon off;'
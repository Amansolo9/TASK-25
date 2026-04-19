FROM node:22-alpine

WORKDIR /app

COPY package.json /app/package.json
RUN npm install --no-audit --no-fund

COPY . /app

EXPOSE 4173

CMD ["sh", "-c", "echo 'HarborOps URL: https://localhost:8443' && npm run dev -- --host 0.0.0.0 --port 4173 --strictPort --logLevel error"]

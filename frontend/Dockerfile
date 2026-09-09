FROM node:18-alpine

WORKDIR /app

COPY package.json .
RUN npm install --silent

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]

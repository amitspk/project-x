# Admin UI build-and-serve image without embedded Nginx
FROM node:20-alpine

WORKDIR /app

COPY fyi_widget_admin_ui/package*.json ./
RUN npm install && npm install react-hook-form@7.52.0

COPY fyi_widget_admin_ui/ .

ARG VITE_API_BASE_URL="http://127.0.0.1:8005"
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN GODEBUG=asyncpreemptoff=1 npm run build

EXPOSE 5173

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]

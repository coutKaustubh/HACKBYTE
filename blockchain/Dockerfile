FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Expose Hardhat default port
EXPOSE 8545

# Run the local RPC node
CMD ["npx", "hardhat", "node", "--hostname", "0.0.0.0"]

# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy go mod files first for better caching
COPY go.mod go.sum ./
RUN go mod download

# Copy the source code
COPY . .

# Initialize go module if it doesn't exist
RUN if [ ! -f go.mod ]; then go mod init agent360; fi

# Add missing dependencies
RUN go mod tidy

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -o agent360 ./src/api

# Final stage
FROM alpine:3.18

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /app/agent360 .

# Copy any additional required files
COPY src/api/config ./config/

EXPOSE 8080

CMD ["./agent360"]
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY . .
RUN go build -o agent360 ./cmd/api

FROM alpine:3.18
WORKDIR /app
COPY --from=builder /app/agent360 .
EXPOSE 8080
CMD ["./agent360"]
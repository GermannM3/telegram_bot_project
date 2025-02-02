# go_server/Dockerfile
FROM golang:1.20

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN go build -o server

EXPOSE 8080

CMD ["./server"]

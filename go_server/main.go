package main

import (
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "os"
    "strings"
    "bytes"
    "io" // Добавлен импорт

    "github.com/gin-gonic/gin"
)

type TelegramUpdate struct {
    UpdateID int `json:"update_id"`
    Message  struct {
        Chat struct {
            ID int64 `json:"id"`
        } `json:"chat"`
        Text string `json:"text"`
    } `json:"message"`
}

type TelegramResponse struct {
    Method  string `json:"method"`
    ChatID  int64  `json:"chat_id"`
    Text    string `json:"text"`
    ParseMode string `json:"parse_mode,omitempty"`
}

func generateHandler(c *gin.Context) {
    body, err := io.ReadAll(c.Request.Body)
    if err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Failed to read request body"})
        return
    }

    var update TelegramUpdate
    err = json.Unmarshal(body, &update)
    if err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid JSON"})
        return
    }

    // Получаем токен из переменных среды
    token := os.Getenv("TELEGRAM_BOT_TOKEN")
    if token == "" {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "TELEGRAM_BOT_TOKEN is not set"})
        return
    }

    // Отправляем запрос к серверу на Python
    resp, err := http.Post("http://python_server:5000/generate", "application/json", 
        strings.NewReader(fmt.Sprintf(`{"text": "%s"}`, update.Message.Text)))
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to send request to Python server"})
        return
    }
    defer resp.Body.Close()

    var res TelegramResponse
    if err := json.NewDecoder(resp.Body).Decode(&res); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to parse response from Python server"})
        return
    }

    // Отправляем ответ в Telegram
    response := TelegramResponse{
        Method:  "sendMessage",
        ChatID:  update.Message.Chat.ID,
        Text:    res.Text,
        ParseMode: "HTML",
    }

    jsonData, err := json.Marshal(response)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to marshal response"})
        return
    }

    url := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", token)
    respTelegram, err := http.Post(url, "application/json", bytes.NewReader(jsonData))
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to send message to Telegram"})
        return
    }
    defer respTelegram.Body.Close()

    if respTelegram.StatusCode != http.StatusOK {
        body, _ := io.ReadAll(respTelegram.Body)
        c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("Telegram API error: %s", string(body))})
        return
    }

    c.JSON(http.StatusOK, gin.H{"status": "Message sent successfully"})
}

func main() {
    router := gin.Default()
    router.POST("/telegram", generateHandler)
    fmt.Println("Go server is running on port 8080")
    log.Fatal(router.Run(":8080"))
}

package main

import (
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "io/ioutil"
    "os"
    "strings"
)

type TelegramUpdate struct {
    UpdateID int `json:"update_id"`
    Message struct {
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

func generateHandler(w http.ResponseWriter, r *http.Request) {
    body, err := ioutil.ReadAll(r.Body)
    if err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    var update TelegramUpdate
    err = json.Unmarshal(body, &update)
    if err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }

    // Получаем токен из переменных среды
    token := os.Getenv("TELEGRAM_BOT_TOKEN")
    if token == "" {
        http.Error(w, "TELEGRAM_BOT_TOKEN is not set", http.StatusInternalServerError)
        return
    }

    // Отправляем запрос к серверу на Python
    resp, err := http.Post("http://python_server:5000/generate", "application/json", 
        ioutil.NopCloser(strings.NewReader(fmt.Sprintf(`{"text": "%s"}`, update.Message.Text))))
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    defer resp.Body.Close()

    var res TelegramResponse
    err = json.NewDecoder(resp.Body).Decode(&res)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }

    // Отправляем ответ в Telegram
    response := TelegramResponse{
        Method: "sendMessage",
        ChatID: update.Message.Chat.ID,
        Text:   res.Text,
    }

    url := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", token)
    jsonData, err := json.Marshal(response)
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }

    respTelegram, err := http.Post(url, "application/json", ioutil.NopCloser(bytes.NewReader(jsonData)))
    if err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    defer respTelegram.Body.Close()

    if respTelegram.StatusCode != http.StatusOK {
        body, _ := ioutil.ReadAll(respTelegram.Body)
        http.Error(w, string(body), respTelegram.StatusCode)
        return
    }

    w.WriteHeader(http.StatusOK)
}

func main() {
    http.HandleFunc("/telegram", generateHandler)
    fmt.Println("Go server is running on port 8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}

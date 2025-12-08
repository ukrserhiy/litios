# Деплой LITI

Детальні інструкції для розгортання LITI на різних платформах.

## Зміст

- [Google Cloud Run](#google-cloud-run) (рекомендовано)
- [Railway](#railway)
- [Heroku](#heroku)
- [DigitalOcean App Platform](#digitalocean-app-platform)
- [Власний сервер (VPS)](#власний-сервер-vps)
- [Локальний Docker](#локальний-docker)

---

## Google Cloud Run

**Вартість**: ~$0 для невеликого навантаження (є безкоштовний рівень)

### Передумови

1. Акаунт Google Cloud: [console.cloud.google.com](https://console.cloud.google.com)
2. Встановлений `gcloud` CLI: [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install)

### Кроки

```bash
# 1. Авторизація
gcloud auth login

# 2. Створіть проект (або використайте існуючий)
gcloud projects create liti-app --name="LITI App"
gcloud config set project liti-app

# 3. Увімкніть необхідні API
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# 4. Деплой
gcloud run deploy liti \
  --source . \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated

# 5. Отримайте URL
# Service URL: https://liti-xxx.europe-west1.run.app
```

### Оновлення

```bash
# Просто повторіть команду деплою
gcloud run deploy liti \
  --source . \
  --platform managed \
  --region europe-west1 \
  --allow-unauthenticated
```

---

## Railway

**Вартість**: $5/місяць (є безкоштовний trial)

### Кроки

1. Перейдіть на [railway.app](https://railway.app)
2. Натисніть **"Start a New Project"**
3. Виберіть **"Deploy from GitHub repo"**
4. Оберіть ваш форк `litios`
5. Railway автоматично визначить Dockerfile
6. Натисніть **Deploy**

### Змінні середовища

Опціонально додайте в Railway Dashboard → Variables:
```
PORT=8080
```

---

## Heroku

**Вартість**: від $7/місяць (Basic Dyno)

### Передумови

1. Акаунт Heroku: [heroku.com](https://heroku.com)
2. Встановлений Heroku CLI: [devcenter.heroku.com/articles/heroku-cli](https://devcenter.heroku.com/articles/heroku-cli)

### Кроки

```bash
# 1. Авторизація
heroku login

# 2. Створіть додаток
heroku create liti-app

# 3. Деплой
git push heroku main

# 4. Відкрийте додаток
heroku open
```

### Procfile

Вже включено в репозиторій:
```
web: gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 server:app
```

---

## DigitalOcean App Platform

**Вартість**: від $5/місяць

### Кроки

1. Перейдіть на [cloud.digitalocean.com/apps](https://cloud.digitalocean.com/apps)
2. Натисніть **"Create App"**
3. Виберіть **"GitHub"** як джерело
4. Оберіть репозиторій `litios`
5. Налаштування:
   - **Type**: Web Service
   - **Build Command**: (залиште порожнім, буде використано Dockerfile)
   - **Port**: 8080
6. Натисніть **"Create Resources"**

---

## Власний сервер (VPS)

### Передумови

- Ubuntu 20.04+ або Debian 11+
- Docker та Docker Compose

### Встановлення Docker

```bash
# Оновіть систему
sudo apt update && sudo apt upgrade -y

# Встановіть Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Встановіть Docker Compose
sudo apt install docker-compose -y

# Перезайдіть для застосування груп
exit
```

### Деплой

```bash
# 1. Клонуйте репозиторій
git clone https://github.com/ukrserhiy/litios.git
cd litios

# 2. Запустіть
docker-compose up -d

# 3. Перевірте статус
docker-compose ps

# LITI доступний на http://your-server-ip:8080
```

### Nginx як reverse proxy (опціонально)

```nginx
# /etc/nginx/sites-available/liti
server {
    listen 80;
    server_name liti.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Активуйте конфіг
sudo ln -s /etc/nginx/sites-available/liti /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL з Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d liti.yourdomain.com
```

---

## Локальний Docker

Для тестування або локальної розробки.

### Запуск

```bash
# Один контейнер
docker build -t liti .
docker run -p 8080:8080 liti

# Або через Docker Compose
docker-compose up -d
```

### Зупинка

```bash
docker-compose down
```

---

## Змінні середовища

| Змінна | Опис | Значення за замовчуванням |
|--------|------|---------------------------|
| `PORT` | Порт сервера | `8080` |

**Примітка**: API ключ OpenRouter вводиться через UI додатку і зберігається в браузері користувача (localStorage). Це безпечніше ніж змінні середовища на сервері.

---

## Оновлення

### Google Cloud Run

```bash
gcloud run deploy liti --source . --platform managed --region europe-west1 --allow-unauthenticated
```

### Railway / Heroku / DigitalOcean

Автоматично при push в GitHub (якщо налаштовано auto-deploy).

### VPS

```bash
cd litios
git pull
docker-compose down
docker-compose up -d --build
```

---

## Troubleshooting

### Помилка "Port already in use"

```bash
# Знайдіть процес
lsof -i :8080
# Завершіть його
kill -9 <PID>
```

### Docker не запускається

```bash
# Перевірте логи
docker-compose logs

# Перезапустіть Docker
sudo systemctl restart docker
```

### Помилка при build на Cloud Run

Перевірте що в репозиторії є:
- `Dockerfile`
- `requirements.txt`
- `server.py`

---

## Підтримка

Проблеми? Створіть [Issue на GitHub](https://github.com/ukrserhiy/litios/issues).

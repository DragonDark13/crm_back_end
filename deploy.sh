#!/bin/bash

# Шлях до проекту
PROJECT_DIR=/home/aleksandrForUpwork/crm_back_end

# Перейти в директорію проекту
cd $PROJECT_DIR || exit

# Видалити старі файли (окрім .git)
rm -rf * .[!.]*

# Клонувати останню версію репозиторію
git clone https://github.com/DragonDark13/crm_back_end.git .

# Активувати віртуальне середовище
source venv/bin/activate

# Оновити залежності
pip install -r requirements.txt

# Перезапустити WSGI-сервер
touch /var/www/ваше_ім'я_на_PythonAnywhere_pythonanywhere_com_wsgi.py

echo "Деплой завершено успішно!"

#!/bin/bash

TARGET_DIR="/home/aleksandrForUpwork/crm_back_end"

echo "Перехожу до директорії $TARGET_DIR..."
cd "$TARGET_DIR" || exit 1

echo "Видаляю старі файли..."
rm -rf * .[!.]* .??*

echo "Клоную репозиторій..."
git clone https://github.com/DragonDark13/crm_back_end.git .

echo "Активую virtualenv..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "Встановлюю залежності..."
pip install -r requirements.txt

echo "Деплой завершено!"
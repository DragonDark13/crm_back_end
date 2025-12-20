echo === CLONE REPOSITORY ===
if not exist crm_back_end (
    git clone https://github.com/DragonDark13/crm_back_end.git
)

cd crm_back_end || exit /b 1

echo === COPY ENV FILE ===
if not exist .flaskenv (
	copy ..\.flaskenv .env
)

echo === CREATE VENV ===
if not exist myenv (
    py -3.10 -m venv myenv
)

echo === ACTIVATE VENV ===
call myenv\Scripts\activate

echo === UPGRADE PIP ===
python -m pip install --upgrade pip setuptools wheel

echo === INSTALL REQUIREMENTS ===
pip install -r requirements.txt

echo === CREATE DATABASE ===
python create_db_postgree.py
python init_data.py

echo === RUN FLASK ===
set FLASK_APP=app.py
set FLASK_ENV=development
flask run

pause
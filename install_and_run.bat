echo === CLONE REPOSITORY ===
if not exist crm_back_end (
    git clone https://github.com/DragonDark13/crm_back_end.git
)

cd crm_back_end || exit /b 1

echo === COPY ENV FILE ===
if not exist .flaskenv (
	copy ..\.flaskenv .env
)

echo === COPY IMPORT FOLDERS FROM PARENT ===

if not exist example_import_data_csv (
    robocopy ..\example_import_data_csv example_import_data_csv /E /NFL /NDL
)

if not exist import_exampla_data_func (
    robocopy ..\import_exampla_data_func import_exampla_data_func /E /NFL /NDL
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
if errorlevel 1 goto :error

python init_data.py
if errorlevel 1 goto :error

echo === IMPORT FULL DATABASE ===
python -m import_exampla_data_func.example_import_full_db
if errorlevel 1 goto :error

echo === RUN FLASK ===
set FLASK_APP=app.py
set FLASK_ENV=development
flask run
goto :eof

:error
echo.
echo ❌ ERROR OCCURRED. STOPPING SCRIPT.
pause
exit /b 1
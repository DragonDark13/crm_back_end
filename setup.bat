@echo off
echo Creating virtual environment with Python 3.10...

py -3.10 -m venv myenv

call myenv\Scripts\activate

python -m pip install --upgrade pip setuptools wheel

pip install -r requirements.txt

echo.
echo Setup complete!
pause

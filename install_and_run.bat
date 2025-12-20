@echo off

git clone https://github.com/DragonDark13/crm_back_end.git
cd crm_back_end

py -3.10 -m venv myenv
call myenv\Scripts\activate

python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

flask run
pause

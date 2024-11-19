pkg update && pkg full-upgrade
pkg i tur-repo -y
pkg install cmake libandroid-spawn rust python git python-pandas libxml2 libxslt python-pyarrow -y
git clone https://github.com/minicom365/AI_CRYPTO
cd AI_CRYPTO
pip install -r requirements.txt
python main.py
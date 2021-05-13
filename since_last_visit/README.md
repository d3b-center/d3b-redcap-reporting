# Show how long it's been since each subject was last seen (e.g. max of latest diagnosis and latest update)

## Web Browser

```shell
cd web
docker compose up
```

or

```shell
cd web
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run since_last_visit.py
```

## Tkinter GUI

```shell
cd gui
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python since_last_visit.py
```

# ctracing

custom tracing lib and helpers


## Setup dev env

```
python3 -m venv venv
. venv/bin/activate
pip install -r requirements-dev.txt
pre-commit install
```

## Test

```
. venv/bin/activate
pip install -e .[full]
pytest --cov-report html --cov-report term --cov-report xml:cov.xml
```

## Build

```
echo x.y.z > VERSION
pip install -r requirements-release.txt
python -m build -s -w
```

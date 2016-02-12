# Installation for testing
```
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt

python runserver.py
```

## When you want to use [the PDF export](https://pypi.python.org/pypi/pdfkit) functionality
```
sudo apt-get install wkhtmltopdf
```

# Code linting ([PEP 8](https://www.python.org/dev/peps/pep-0008/) and [pyflakes](https://pypi.python.org/pypi/pyflakes) using [flake8](https://pypi.python.org/pypi/flake8))
```
pip install flake8

flake8
```

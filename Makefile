init:
	pip install -qr requirements.txt

test: init
	python -m unittest discover -s './tests' -t .

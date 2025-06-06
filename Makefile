PYTHON = python3
PIP = $(PYTHON) -m pip

# Install dependencies
install:
	$(PIP) install -r requirements.txt

# Run server with optional host and port
run-server:
	$(PYTHON) echo.py server -l 127.0.0.1 -p 55667

# Run client with optional server IP and port
run-client:
	$(PYTHON) echo.py client -s 127.0.0.1 -p 55667

# Clean up __pycache__ and .pyc files
clean:
	find . -type d -name '__pycache__' -exec rm -r {} + 2>/dev/null
	find . -name '*.pyc' -delete

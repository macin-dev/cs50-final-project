# Netwatch

#### Video Demo [Watch video on YouTube](https://youtu.be/djr5f6cMGF8)


#### Description
Hello, my name is Ernesto. I am thrilled to share my final project from the CS50 course. 
This is a simple network monitoring tool designed for students building LAN networking labs that helps them visualize the status of services running on the devices connected to the network with log-in support.
The current state of the application allows you to add and delete devices and create status logs when checking the connection state, as well as a search feature that lets you filter by device name and host.

#### How it works
The core functionality of this application attempts to establish a TCP three-way handshake connection to let the user know the configured host and port are reachable and measure how long it takes. 
It's worth mentioning that even though the communication could succeed, it does not guarantee the application behind it is functioning correctly.

On the following list, I will explain what the purpose of each technology is and why I chose them to complete the project.

- Python: Is the core language I used for the backend because it's easy to implement and comes with compatible modules that I can install, like Flask.
- Flask: Flask is a micro web framework that comes with useful web features to handle requests and set up sessions for logged-in users.
- SQLite: Stores the application’s data in a local database file.
- SQLAlchemy: ORM is a powerful design system to abstract the underlying functionality of SQL statements with OOP syntax. I chose SQLAlchemy to map Python classes with database tables, letting me manage users, devices, and logs; it has well-built-in functionalities and flexibility to implement.
- Tailwind CSS: I chose Tailwind as a framework for CSS due to its versatility to create powerful and unique styles without relying heavily on one design or pattern.
- Sockets: Establishing a connection between server-client machines requires transferable data across the network, either on the same device or different machines. The sockets system attempts an outgoing TCP connection to the configured IPv4 host and port. The application records whether it succeeds and measures the connection time.
- HTMX: This project relies heavily on HTMX, which is a lightweight JavaScript library to extend the functionality of native HTML behavior. As for this project, it uses the HTMX attributes to trigger events for adding, deleting, and filtering data. It processes the returned data from the backend and decides which parts of the application need to change based on a specific event or functionality without reloading a whole page. Small JavaScript handlers manage modal interactions.

#### Project Structure

There are a few files I'd like to explain, as they are the modules that make up the overall functionality of the application.

- ```app.py```: Flask routes and application logic that handles HTTP requests like GET, POST, and DELETE for retrieving devices, the device's logs, deleting a device, checking TCP connection, login, signup, and logout.
- ```models.py```: This file was created to set the structure of Python classes to define models with predefined attributes for the SQLite tables; this approach is called ORM (Object-Relational Mapping).
- ```checker.py```: Checks TCP reachability using Python’s socket module, with a connection timeout of three seconds. Checks are triggered manually.
- ```templates/partials/```: Partials contain reusable Jinja templates.
- ```migrations/```: It uses Flask-Migrate to upgrade changes to the database through the console; this directory registers each new version with the new changes created.

If you'd like, you can run this project locally on your computer. Download or clone the project, then open a terminal in its root directory, and follow the instructions for your operating system.

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:NETWATCH_SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
flask --app app run
```
```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export NETWATCH_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
flask --app app run
```

Open http://127.0.0.1:5000 in your browser.

RESTful API
- ```GET /```: Displays the user’s devices, latest connection status, and latency in a table.
- ```POST /api/devices/<int:device_id>/check```: Tests TCP reachability and records the result and connection time.
- ```GET /api/devices/<int:device_id>/logs```: Retrieve each device’s logs.
- ```GET /api/devices```: Returns the add-device form.
- ```POST /api/devices```: Creates a device using the submitted name, host, protocol, and port.
- ```DELETE /api/devices/<int:device_id>```: It removes the registered device from the database permanently along with their logs.
- ```GET /login```: Returns the log-in form.
- ```POST /login```: It processes the data entered by the user before granting access.
- ```GET /register```: Returns the sign-up form.
- ```POST /register```: It creates a new account with valid data.
- ```GET /logout```: Users can sign off from their account.

Currently, these are all the features this version has. I'm planning to add automatic reload for a certain number of seconds so users don’t do it manually.
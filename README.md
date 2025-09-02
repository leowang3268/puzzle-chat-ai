## Technical Tools

- Backend:
    - Django (Python web framework)
    - Django Channels: for real-time WebSocket communication
    - PostgreSQL: for database
- Frontend:
    -
- Real-time Collaboration:
    - WebSockets: for real-time updates (integrated with Django Channels on the backend)
- AI Integration:
    - OpenAI API (ChatGPT): for story suggestions and assistance


## Execution method
### Step 1: Install Django & channels (in the anaconda environment)
```
pip install django
```
```
pip install channels
```
### Step 2: Start a Django Project
#### 1. Open the terminal and navigate to the directory where you want to create your project.
#### 2. Run the following command to start a new Django project:
```
python -m django startproject puzzle_chat_ai
```
#### 3. Create a Django App
Firstly nevigate to the puzzle_chat_ai file
```
cd puzzle_chat_ai
```
Next, to create an app, run:
```
python manage.py startapp chat
```
#### 4. File Structure
The file structure now will look like:
```
puzzle_chat_ai/
    db.sqlite3
    manage.py
    puzzle_chat_ai/
        __init__.py
        asgi.py
        settings.py
        urls.py
        wsgi.py
    chat/
        __init__.py
        admin.py
        apps.py
        models.py
        tests.py
        views.py
        migrations/
```
### Step 3: Update the file
update the files in chat directory and mywebsite directory with the code provided above.
### ps. There are some files that you need to add.
#### In the " ./puzzle_chat_ai/chat
#### add files: "consumers.py", "forms.py", "routing.py", "urls.py"
#### add directory: "templates"
#### And in the "templates" directory 
#### add "chat" directory
#### And in the ./puzzle_chat_ai/chat/templates/chat/
#### add files: "index.html", "lobby.html"
#### Also update the code in these files

### Step 4: Create the database and Migrate the model to database
#### 1. Create you database, and update the personal information in the setting.py
![image](https://github.com/user-attachments/assets/46f8b166-a589-4ec8-9588-e9ec1fc538e4)

#### 2. run the command to migrate the models to the database:
```
python manage.py makemigrations
python manage.py migrate
```


### Step 5: Run the server
run the command:
```
python manage.py runserver
```
ps. if there are any package that you didn't have, please pip them

### Step 6: Use ngrok to connect to the server
#### 1. Download ngrok in their website
#### 2. put the ngrok.exe at the place you like
#### 3. In the place where you put the ngrok.exe, open the terminal
#### 4. run the prompt
```
.\ngrok http http://localhost:8000
```
#### and there will be a Forwarding url (suppose like https://aaa.ngrok-free.app)
#### copy the part "aaa.ngrok-free.app" and paste in the lobby.html
#### there is a line in lobby.html like
```
let url = `6911-2001-288-4001-d750-c520-3669-39a1-17f.ngrok-free.app/ws/socket-server/?userName=${userName}`;
```
#### replace with
```
let url = `aaa.ngrok-free.app/ws/socket-server/?userName=${userName}`;
```
#### And you can use the url: https://aaa.ngrok-free.app to connect to the server
#### ps. remember to run the server



        




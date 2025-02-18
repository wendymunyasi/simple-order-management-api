# Simple Order Management System Backend API.

The Simple Order Management System Backend API is a robust and scalable web API designed to manage orders efficiently. It provides full CRUD (Create, Read, Update, Delete) functionality, allowing users to create, view, update, and delete orders seamlessly.

This project leverages Django as the backend framework, Redis as the message broker, and Celery for handling background tasks such as sending order confirmation emails or processing asynchronous operations. With these technologies, the system ensures high performance, reliability, and scalability, making it suitable for both small-scale and enterprise-level applications.

The API is fully documented using Swagger, providing an interactive interface for developers to explore and test endpoints with ease.
## Documentation

- The API documentation is available via Swagger. Swagger provides an interactive interface to explore and test the API endpoints.

### Accessing Swagger Documentation

1. **Local Development**:
   Once the server is running, you can access the Swagger documentation at:
   [http://127.0.0.1:8000/swagger/](http://127.0.0.1:8000/swagger/)

2. **Production Environment**:
   If deployed, replace `127.0.0.1:8000` with your production server URL.

3. **Swagger UI Features**:
   - View all available API endpoints.
   - Test API requests directly from the browser.
   - Explore request/response formats and example payloads.

---

### Prerequisites and Installing

You need to install the following software/technologies to have the app running on your local machine for development and testing purposes. Instructions on how to install will also be provided next to the software.

| Software            | Installation Instructions/Terminal Commands      |
| ------------------- | ------------------------------------------------ |
| Python3.12          | 1. sudo apt-get update                           |
|                     | 2. sudo apt-get install python3.12               |
| Virtual Environment | 1. Python3 -m venv venv                          |
|                     | 2. Activate by running: source venv/bin/activate |
| Pip                 | pip install --upgrade pip                        |


Then run this command in your terminal to install the required software:

```
pip install -r requirements.txt
```

## Built With

- [Django] - 5.1 (https://docs.djangoproject.com/en/5.1/)

## Project-Setup Instructions.

1. git clone this repo using the following link.

   https://github.com/wendymunyasi/simple-order-management-api.git

2. For Django app, set the database to your own url then run the commands:

```
python3 manage.py makemigrations
python3 manage.py migrate
```
3. Edit the file `data_script.py` with your own database details, then populate the database by running the file.
4. Start the Redis server by running:
```
redis-server --port 6381
```

5. Start the Celery worker by running:
```
celery -A order_management worker --loglevel=info
```

6. Run the command `python3 manage.py runserver` to start the server.
7. Run the project in whichever app you want.

## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Authors

- **Wendy Munyasi**

## License

This project is licensed under the Apache License.

## NOTE

Almost every action is documented on the console, from creating an order or canceling an order. For curiouser and curiouser, open your console and view what messages display when you perform an action.

## Collaborate

To colloborate, reach me through my email address wendymunyasi@gmail.com

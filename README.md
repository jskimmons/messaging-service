Created using Django/Python. The bulk of my code can be found in the `unified_messaging_server` django project, in the `api` app.

The server can be started by running the following from the `messaging-service` directory:

```
make setup
make db-up
make run
```

and then in another terminal, tested with:

```
make test
```

My Django test suite can be run with:
```
python manage.py test
```
while the virtual env `venv` is running.

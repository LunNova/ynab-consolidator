FROM python:3.6-alpine

WORKDIR /code/

RUN pip install 'poetry==0.12.17' && \
    poetry config settings.virtualenvs.create false

COPY poetry.lock pyproject.toml app.py run.sh /code/

COPY ynab/ /code/ynab/

RUN poetry install && chmod +x /code/run.sh

ENTRYPOINT ["/code/run.sh"]

CMD []

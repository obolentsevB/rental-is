Довідник rental-is
==================

Внутрішній REST API оренди житла: FastAPI, Python 3.14. Контракт описано в
``api/openapi.yaml`` (версія 1.1.0), його HTML-документація лежить у ``docs/api.html``.

.. toctree::
   :maxdepth: 2

   architecture
   reference

Збірка
------

Команда виконується з кореня репозиторію:

.. code-block:: text

   sphinx-build -W -b html docs/reference docs/reference/_build/html

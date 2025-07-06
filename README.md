# Automatización de auditorías básicas con Scrapy

## Pasos a seguir

1. Crear y activar entorno virtual desde **auditorias** con `python -m venv .venv` y `.venv\Scripts\activate`
2. Hay un **requirements.txt** en **auditorias\audit**, se instala con `pip install -r requirements.txt`
3. Lanzar `scrapy crawl crawler` desde **audit**

## Localización del archivo

El archivo de logs está en **auditorias** y el archivo del script está en **auditorias\audit\audit\spiders**.

## Problemas con Windows

Si en Windows diera problemas porque no deja hacer cualquiera de los siguientes pasos hará falta lo siguiente:

`Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`

Y para desactivarlo:

`Set-ExecutionPolicy Restricted -Scope CurrentUser`

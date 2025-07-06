# Cómo hacer auditorías básicas con Scrapy

Primero hace falta tener **Python**, un **entorno virtual** y **Scrapy** instalados.

Entorno virtual:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Instalación de Scrapy:

```powershell
pip install scrapy
```

Creación del proyecto de Scrapy:

```powershell
scrapy startproject audit
```

El archivo donde se vaya a crear la araña (*spider*) en este caso está en el directorio:

```
audit/audit/spiders/script.py
```

Donde *script.py* es el archivo con el código. Por último, la línea para arrancar la araña es:

```powershell
scrapy crawl crawler
```

Donde *crawler* es el nombre de la araña que está definido en script.py.

## Creación del *crawler*

```python
from pathlib import Path
import os

import scrapy

class AuditSpider(scrapy.Spider):
    name = "crawler" <- el nombre de la araña
```

**AuditSpider** es una clase hija de la clase **Spider**, por lo tanto en el constructor ponemos lo siguiente para que tenga como parámetros también todos los del padre.

```python
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) <- parámetros de la padre
        root = os.path.join("..", os.getcwd())
        self.path = os.path.join(root, "..", "urls.txt")
```

Las rutas que hay en el constructor es porque a la hora de automatizar la araña prefiero tener todos las URLs en un archivo .txt, leerlo y entonces guardarlas en una lista.

```python
    def get_urls(self):
        with open(self.path) as file:
            list_urls = [url.strip() for url in file if url.strip()]

        return list_urls
```

Tal vez más adelante podría ser conveniente que la ruta (*path*) se pasara como argumento en lugar de tenerla fija tal y como está.

De acuerdo a la [documentación oficial de Scrapy](https://docs.scrapy.org/en/latest/intro/tutorial.html), el código hasta ahora sería algo así:

```python
from pathlib import Path
import os
import logging

import scrapy

class AuditSpider(scrapy.Spider):
    name = "crawler"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        root = os.path.join("..", os.getcwd())
        self.path = os.path.join(root, "..", "urls.txt")

    async def start(self):
        urls = self.get_urls()
       
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        page = response.url.split("/")[-2]
        logging.info(f"URLs: {page}")
    
    def get_urls(self):
        with open(self.path) as file:
            list_urls = [url.strip() for url in file if url.strip()]

        return list_urls
```

Por ahora lo único que hace es coger las URLs del archivo y obtener las URLs.

Dentro de la opciones (*settings.py*) de nuestro proyecto podemos ver que hay dos líneas interesantes:

- `ROBOTSTXT_OBEY = True`: que es para que respete lo que haya en el archivo **robots.txt**
- `USER_AGENT`: para identificarnos como tal, pero de momento no voy a cambiar nada

También por mi parte he añadido la línea `LOG_LEVEL = "WARNING"` para que Scrapy no sea tan verboso.

En la documentación menciona que en lugar de usar un método **start()** se puede tener una lista llamada **start_urls**, así que uso el atajo que mencionan:

```python 
from pathlib import Path
import os
import logging

import scrapy

class AuditSpider(scrapy.Spider):
    name = "crawler"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        root = os.path.join("..", os.getcwd())
        self.path = os.path.join(root, "..", "urls.txt")
        self.start_urls = self.get_urls() <- la lista de start_urls

    def parse(self, response):
        page = response.url.split("/")[-2]
        logging.info(f"URLs: {page}")
        
    
    def get_urls(self):
        with open(self.path) as file:
            list_urls = [url.strip() for url in file if url.strip()]

        return list_urls
```

## Obtener enlaces de navegación

```python
    def parse(self, response):
        page = response.url.split("/")[-2]
        logging.info(f"URLs: {page}")

        if "sitemap.xml" in page:
            return self.parse_sitemap(response)
        else:
            return self.parse_nav(response)

    def parse_sitemap(self, response):
        logging.info(f"SITEMAP: de momento nada")
    
    def parse_nav(self, response):
        logging.info(f"NAV: {response.xpath('//nav//a/@href').extract()}")
```

Aquí hay varias cosas a tener en cuenta, lo primero de todo es que para recorrer lo que queremos con la araña tenemos que usar [XPath](https://es.wikipedia.org/wiki/XPath).  
Más información sobre [XPath](https://www.mclibre.org/consultar/xml/lecciones/xml-xpath.html).

A grandes rasgos sería lo siguiente:

- `..` padre del nodo actual
- `//` es cualquier descendiente del nodo actual a cualquier nivel
- `/` hijo directo del nodo actual, excepto si es al principio que entonces significa raíz
- `@` es para atributos de HTML del nodo actual (como *href* o *alt*)
- `text()`, por ejemplo, es una función que devuelve los nodos de texto hijos del nodo actual
- `|` operador de unión en XPath

También existen otras funciones como:

- `contains()`
- `starts-with()`
- `string-length()`
- `normalize-space()`

Volviendo al código, aquí lo que quiero es conseguir todos los enlaces públicos (los privados me dan igual) de la web para poder visitarlos uno a uno. Las dos maneras que hay son: yendo al *sitemap.xml* si es que la web tiene uno, o yendo a los enlaces de navegación.  
De esta forma primero pregunto por el archivo, si no existe entonces que extraiga los enlaces de manera *manual*.

Por el momento, usando mi web como ejemplo he obtenido lo siguiente:

```powershell
['index.html', 'contenido.html', 'historial.html', 'sobre.html', 'mensajes.html']
```

Pero lo que yo quiero es que esos enlaces también partan del padre, así que pruebo lo siguiente:

```python
def parse_nav(self, response):
    links = response.xpath('//nav//a/@href').extract()
    url = [response.urljoin(link) for link in links]
    logging.info(f"NAV: {url}")
```

Y ahora sí devuelve la ruta completa de cada uno. Sin embargo, esto de guardarlo en una lista para luego iterar sobre ella es innecesario y ya existe una función de la clase **response** que permite esto:

```python
def parse_nav(self, response):
    links = response.xpath('//nav//a/@href').extract()
    yield from response.follow_all(urls=links, callback=self.parse)
```

Aquí lo que hace es lo siguiente:

1. Extrae las URLs de la etiqueta HTML `<nav>`
2. Luego hace *yield* de la clase **response** (que para hacernos una idea, es una clase que funciona del mismo modo que **document** o **window** en JS), y dicha clase tiene el método **follow_all()**
3. El método **follow_all()** lo que hace, como su nombre indica, es seguir TODOS los enlaces que se pasen por parámetro
4. Para que se vea más claro, el parámetro tiene el nombre de *urls* pero se puede omitir su nombre; en este caso los enlaces a seguir son los extraídos anteriormente
5. Como *callback* se pasa nuestra función **parse()** y con ella hace lo mismo que hemos hecho hasta ahora, la ejecuta tal cual por cada enlace

Antes de continuar, la diferencia de **return** y **yield** es que el segundo se usa para las funciones generadoras. 
Mientras que el *return* corta la ejecución de una función, el *yield* solo la pausa hasta que vuelva a ser llamada. Además, el código que haya después de un *return* ya no es accesible, pero el que haya después de *yield* sí: esto quiere decir que una función puede tener varios *yield*.
Por lo general, *yield* también suele ser más eficiente con la memoria.

Nota 1: hay diferencias entre *yield* y *yield from*.

- *yield*: produce un único valor (1, 2, 3, etc)
- *yield from* itera sobre el iterable, es decir, hace un *yield* por cada uno de los elementos; éste es más compacto porque es como si se hubieran hecho varios *yield* uno detrás del otro sin tener que hacerlo implícitamente (manualmente)

Nota 2: cuando se habla de generadores (como *yield*) se usa el término "produce" en lugar de "devuelve".

## Comprobación de enlaces rotos

El código ahora:

```python
def parse_nav(self, response):
    links = response.xpath("//nav//a/@href").extract()
    yield from response.follow_all(urls=links, callback=self.check)

def get_all_href(self, response):
    links = response.xpath("//a[not(ancestor::nav)]/@href").extract()
    yield from response.follow_all(urls=links, callback=self.check_broken_links)

def check(self, response):
    yield from self.get_all_href(response)

def check_broken_links(self, response):
    if response.status != 200:
        # Esto se guardara en un archivo mas adelante
        logging.info(f"Enlace roto")
```

Primero, sigue comprobando los enlaces de navegación pero luego comprueba TODOS los enlaces de cada página sin los de navegación. Puede parecer redundante pero por defecto Scrapy se hace cargo de eso y, a menos que hayan diferencias mínimas, no va a visitar un enlace más de una vez.

La función **check()** va a servir de "pegamento" o de "coordinadora" para las comprobaciones que se van a hacer.

Por último, **check_broken_links()** comprobará si los enlaces dan algún problema.  
Esta no es la única comprobación que se hará, luego habrán más funciones como comprobar si las imágenes tienen `alt=""` con contenido, por ejemplo.

Aunque todavía no está definido, el proceso final será que toda la información la guarde en un archivo: puede ser un txt, csv o json.

## Comprobación de los enlaces de teléfono, correo y ubicación

### Teléfono

Como el log es muy extenso podemos usar `FINDSTR "texto"` para ver por pantalla solo lo que queremos, el problema es que parece que Scrapy usa *stderror* para los logs así que aunque lo hagamos de esa manera veremos todo el log.  
La forma de hacerlo sería con:

```powershell
scrapy crawl crawler 2>&1 | FINDSTR "texto"
```

Donde le decimos que pase la salida 2 (*stderror*) a la 1 que es la estándar (*stdout*). Así sí que solo veremos lo que nos interesa.  
Si fuera en Linux entonces sería con `grep`.

```python
    def check(self, response):
        yield from self.get_all_href(response)
        self.check_tel_links(response)

    def check_tel_links(self, response):
        phone = r"^(\+34|0034|34|\(\+34\))?(?=(?:\D*\d){9,14}$)\d{2,4}(?:[\s\-]?\d{2,4})*$"
        nodes = response.xpath("//body//*[text()]")

        for node in nodes:
            text = node.xpath("text()").get()
            if text is not None:
                if re.search(phone, text):
                    if node.xpath("(ancestor::a | self::a)[contains(@href, 'tel:')]").get() is None:
                        # Esto se guardara en un archivo mas adelante
                        logging.info(f"NO TIENE ENLACE, {text}")
```

Primero se necesitarán dos **expresiones regulares** (*regex*) y para ello hace falta importar el módulo **re** con `import re`.

Por un lado tenemos el patrón para los números de teléfono, en principio acepta varios números españoles pero está más limitado para números extranjeros. Este patrón necesita alguna mejora o afinarlo más. El patrón también tiene lookahead positivo en `?(?=(?:\D*\d){9,14}$)` para que solo acepte números (seguidos por guiones, espacios, etc) de una longitud de 9 a 14 dígitos.

Después queremos obtener nodos de texto, cualquier nodo de texto por lo tanto partimos de `<body>`.

- `//` es cualquier descendiente del nodo actual a cualquier nivel
- `*[text()]` hace referencia a seleccionar todos los nodos con texto (que son hijos), independientemente de qué tipo de etiqueta es y los corchetes son para condiciones o filtros

Luego hay que iterar los nodos y conseguir el texto como tal de dicho nodo. Anteriormente cogía el nodo, ahora con obtiene el texto con `node.xpath("text()").get()`.

Posteriormente comprueba si el texto existe (si coincide el patrón). 
En Python `re.search()` devuelve el **objeto** o **None** si no coincide el patrón, por lo tanto hay que preguntar *¿is None?*. Esto es diferente a como funciona en C.  

Después, dentro de ese if, se comprueba si un ancestro de ese nodo o si el nodo en sí es un enlace y además si contiene el atributo `href` con el texto `tel:` y en caso negativo (de ahí el `!= True`) pintaría por pantalla que no tiene enlace. Más adelante no querré que lo pinte por pantalla, si no que lo guarde en un archivo de texto.

Tal vez sea conveniente pasar los patrones de la función a un atributo de la clase.

```python
class AuditSpider(scrapy.Spider):
    name = "crawler"
    phone = r"^^(\+34|0034|34|\(\+34\))?(?=(?:\D*\d){9,14}$)\d{2,4}(?:[\s\-]?\d{2,4})*$"

...

    def check_tel_links(self, response):
        nodes = response.xpath("//body//*[text()]")

        for node in nodes:
            text = node.xpath("text()").get()
            if text is not None:
                if re.search(self.phone, text):
                    if node.xpath("(ancestor::a | self::a)[contains(@href, 'tel:')]").get() is None:
                        # Esto se guardara en un archivo mas adelante
                        logging.info(f"NO TIENE ENLACE, {text}")
```

Pero hará falta que luego tengan `self`.

### Correo

```python
    def check(self, response):
        yield from self.get_all_href(response)
        self.check_links(response)

    def get_text_nodes(self, response):
        return response.xpath("//body//*[text()]")

    def check_links(self, response):
        nodes = self.get_text_nodes(response)

        for node in nodes:
            text = node.xpath("text()").get()
            if text is not None:
                if re.search(self.phone, text):
                    if node.xpath("(ancestor::a | self::a)[contains(@href, 'tel:')]").get() is None:
                        # Esto se guardara en un archivo mas adelante
                        logging.info(f"NO TIENE ENLACE, {text}")

                if re.search(self.mail, text):
                    if node.xpath("(ancestor::a | self::a)[contains(@href, 'mailto:')]").get() is None:
                        # Esto se guardara en un archivo mas adelante
                        logging.info(f"NO TIENE ENLACE, {text}")
```

Aquí he preferido mantener (y renombrar la función) la lógica en una sola función para que así `response.xpath("//body//*[text()]")` solo lo haga una vez y no dos veces (una por función).  
Esto se puede refactorizar para que las funciones sean "pequeñas" y hagan lo suyo una independiente de la otra, pero tienen una que coordina ambas. Además, la que "coordina" sigue haciendo la búsqueda de texto una sola vez.

```python
    def check(self, response):
        yield from self.get_all_href(response)
        self.check_links(response)

    def get_text_nodes(self, response):
        return response.xpath("//body//*[text()]")

    def check_links(self, response):
        nodes = self.get_text_nodes(response)

        for node in nodes:
            text = node.xpath("text()").get()
            if text is not None:
                self.check_tel_links(node, text)
                self.check_mail_links(node, text)

    def check_tel_links(self, node, text):
        if re.search(self.phone, text):
            if node.xpath("(ancestor::a | self::a)[contains(@href, 'tel:')]").get() is None:
                # Esto se guardara en un archivo mas adelante
                logging.info(f"NO TIENE ENLACE, {text}")

    def check_mail_links(self, node, text):
        if re.search(self.mail, text):
            if node.xpath("(ancestor::a | self::a)[contains(@href, 'mailto:')]").get() is None:
                # Esto se guardara en un archivo mas adelante
                logging.info(f"NO TIENE ENLACE, {text}")
```

Por lo demás, el código de **mailto:** es similar al de **tel:**  
Finalmente, ya solo quedaría el patrón de email.

```python
mail = r"^([\w\-]+)(\@){1}([\w\-]+)(\.){1}([\w]+)$"
```

El patrón de correo también es mejorable, pero por ahora valdrá.

### Refactorización para que coja teléfono y correo en una sola función

```python
    def check_links(self, response):
        nodes = self.get_text_nodes(response)

        for node in nodes:
            text = node.xpath("text()").get()
            if text is not None:
                self.check_contact_links(node, text, self.phone, "tel:")
                self.check_contact_links(node, text, self.mail, "mailto:")

    def check_contact_links(self, node, text, pattern, link_type):
        if re.search(pattern, text):
            if node.xpath(f"(ancestor::a | self::a)[contains(@href, '{link_type}')]").get() is None:
                # Esto se guardara en un archivo mas adelante
                logging.info(f"{text} NO TIENE ENLACE DE TIPO {link_type}")
```

Se reemplazan las dos funciones anteriores por una más genérica llamada **check_contact_links()** y se pasa por parámetro `tel:` o `mailto:`, también se pasa por parámetro el patrón a utilizar.

### Imágenes

Este es más fácil, solamente hay que comprobar si la imagen tiene `alt=` y comprobar si el `alt=` está vacío.

```python
    def check(self, response):
        yield from self.get_all_href(response)
        self.check_links(response)
        self.check_img_links(response)

    def check_img_links(self, response):
        imgs = response.xpath("//body//img")

        for img in imgs:
            alt = img.xpath("./@alt").get()

            if alt is None:
                logging.info(f"PRUEBA DE IMAGENES: ALT NO EXISTE {img}")
            elif alt == "":
                logging.info(f"PRUEBA DE IMAGENES: ALT ESTA VACIO {img}")
```

`./` se refiere al nodo actual (en el contexto donde está). Es similar a `self::` pero no son exactamente iguales.

Aunque ahora mismo las funciones de enlaces e imágenes no son funciones generadoras, es posible que en el futuro -cuando quiera que retornen algo para guardar su resultado en un archivo de texto- por ejemplo, sí sea interesante que usaran la palabra reservada `yield`.

## Hacer que el *crawler* no se escape

Es conveniente que el *crawler* solo siga enlaces del sitio web, no queremos que se vaya a explorar otros sitios web.

```python 
    from urllib.parse import urlparse

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        root = os.path.join("..", os.getcwd())
        self.path = os.path.join(root, "..", "urls.txt")
        self.start_urls = self.get_urls()
        self.allowed_domains = self.get_allowed_domains()

    def get_allowed_domains(self):
        urls = self.get_urls()
        domains = set()

        for url in urls:
            url_parsed = urlparse(url)
            domains.add(url_parsed.netloc)
        
        return list(domains)

    def get_all_href(self, response):
        links = response.xpath("//a/@href").extract()
        is_internal_link = [link for link in links if self.internal_link(link)]
        yield from response.follow_all(urls=is_internal_link, callback=self.check)

    def internal_link(self, url):
        url_parsed = urlparse(url)

        # urls internas
        if not url_parsed.netloc:
            return True

        for domain in self.allowed_domains:
            if domain in url_parsed.netloc:
                return True
        return False 
```

Antes podía escaparse, ahora es más difícil que ocurra.

1. Se ha usado la librería [urllib.parse](https://docs.python.org/3/library/urllib.parse.html).
2. Se ha creado `self.allowed_domains` en el constructor, ahí definimos una lista de dominios permitidos.
3. Creamos la función `get_allowed_domains()`, dicha función llama a una de las primeras que se crearon que es `self.get_urls()`. Dicha función leía el archivo txt con los enlaces, aquí en cambio tenemos un set de dominios (para que no hayan repetidos) e iteramos las urls del archivo de texto. Después se parsea la url y se obtiene el *netloc* que es el nombre de dominio del sitio. Se añaden y retornan los dominios del set, además se retorna como una lista porque es lo que quiere Scrapy.
4. Se crea la función `internal_link()` que como parámetro necesita la url a comprobar, dicha url es realmente `link` en las otras funciones. En esta se vuelve a parsear la url, después se comprueba si es una url interna y si el dominio es uno de los permitidos.
5. Finalmente, tanto `parse_nav()` como `get_all_href` (que es posible que sean refactorizadas en el futuro) llaman a la función creada en el punto anterior para comprobar si los enlaces son internos o no y si son parte de los dominios permitidos o no. De ser así, nuestra araña puede seguirlos.

También se ha reemplazado la función que comprobaba los enlaces de `<nav>` y los que no, por una que coja todos como tal.

## Comprobar si un enlace es HTTP en lugar de HTTPS

```python
    def check(self, response):
        yield from self.get_all_href(response)
        self.check_broken_links(response)
        self.check_http(response)
        self.check_links(response)
        self.check_img_links(response)

    def check_http(self, response):
        links = response.xpath("//a/@href").extract()

        for link in links:
            if link.startswith("http") and not link.startswith("https"):
                # Esto se guardara en un archivo mas adelante
                logging.info(f"EL ENLACE {link} NO ES HTTPS")
```

Simplemente hay que obtener el enlace (con `extract()` o con `getall()` porque esto devuelve una `list[str]` mientras que `get()` solo devolvería un enlace). Después iteramos por cada enlace obtenido en la lista y se comprueba si empieza por HTTP con la función de Python `elemento.startswith("texto")` y además hay que indicarle que no empiece por HTTPS porque de lo contrario dará como error incluso los HTTPS.

Realmente no hay diferencia entre **extract()** y **getall()**, hacen lo mismo pero **getall()** es más moderno. Por mantener la coherencia, más adelante cambiaré todos los **extract()** por **getall()** ya que es más descriptivo y se ve mejor la diferencia con **get()**.

## Comprobar si existe **sitemap.xml** y **robots.txt**

Podemos hacer dos funciones de esta manera:

```python
    def check_sitemap(self, response):
        if response.url.rstrip("/") in self.start_urls:
            links = response.xpath("//a/@href").extract()

            for link in links:
                if "sitemap.xml" in link:
                    logging.info(f"EL ARCHIVO sitemap.xml SÍ EXISTE EN {self.start_urls}")
                    return
            # Esto se guardara en un archivo mas adelante
            logging.info(f"EL ARCHIVO sitemap.xml NO EXISTE EN {self.start_urls}")

    def check_robots(self, response):
        if response.url.rstrip("/") in self.start_urls:
            links = response.xpath("//a/@href").extract()

            for link in links:
                if "robots.txt" in link:
                    logging.info(f"EL ARCHIVO robots.txt SÍ EXISTE EN {self.start_urls}")
                    return
            # Esto se guardara en un archivo mas adelante
            logging.info(f"EL ARCHIVO robots.txt NO EXISTE EN {self.start_urls}")
```

Pero como la comprobación es la misma podemos tener toda la lógica en una sola:

```python
    def check_file_exists(self, response, file):
        if response.url.rstrip("/") in self.start_urls:
            links = response.xpath("//a/@href").extract()

            for link in links:
                if file in link:
                    logging.info(f"EL ARCHIVO {file} SÍ EXISTE EN {self.start_urls}")
                    return
            # Esto se guardara en un archivo mas adelante
            logging.info(f"EL ARCHIVO {file} NO EXISTE EN {self.start_urls}")

    def check(self, response):
        yield from self.get_all_href(response)
        self.check_file_exists(response, "sitemap.xml")
        self.check_file_exists(response, "robots.txt")
```

Aquí dos cosas a tener en cuenta:

1. Si no hacemos la comprobación inicial, va a buscar el archivo en cualquiera de las páginas (lo cual es innecesario porque si existe debería estar en la primera).
2. Necesitamos la función `rstrip()` de Python porque a veces, aunque en el archivo **urls.txt** no esté escrita la dirección con una barra (`/`) al final, sí se añade automáticamente y entonces no pasará la comprobación.

Después es solamente comprobar si la dirección a ese archivo está en alguna de los enlaces de la página principal: si lo encuentra puede hacer *return* para dejar de comprobar y si no lo encuentra se volcará la información al documento de texto (posteriormente).  
Se pasa el archivo por parámetro.

## Comprobar si existe un *favicon*

Los corchetes, `[filtro]`, en XPath son para evaluar condiciones o para filtrar.

```python
    def check(self, response):
        yield from self.get_all_href(response)
        self.check_favicon(response)

    def check_favicon(self, response):
        link = response.xpath("//link[@rel='icon' or @rel='shortcut icon']")
        href = link.xpath("./@href").get()

        if link:
            if href == "" or href is None:
                # Esto se guardara en un archivo mas adelante
                logging.info(f"EL HREF DEL FAVICON ESTA VACIO: {href} en {response}")
        else:
            # Esto se guardara en un archivo mas adelante
            logging.info(f"NO HAY FAVICON: {link} en {response}")
```

La comprobación del **href=** es similar a la de **alt=** para imágenes.  
Coge los enlaces que tengan `rel="icon"` o `rel="shortcut icon"`, el segundo es más antiguo que el primero pero todavía se puede ver en uso así que compruebo ambos (hay más, pero no los he visto nunca): estos enlaces son para los *favicon*. El nodo lo cojo "vivo".  
Después busco **href=** en el nodo actual y con **get()** lo paso a un string. Finalmente compruebo:

- Si el enlace existe
- En caso positivo compruebo si el **href** existe o si está vacío

## Comprobar si existe un `<h1>`

```python
    def check(self, response):
        yield from self.get_all_href(response)
        self.check_h1(response)

    def check_h1(self, response):
        h1 = response.xpath("//h1")

        if len(h1) == 0:
            # Esto se guardara en un archivo mas adelante
            logging.info(f"NO HAY NINGÚN <h1> EN {response}")
        elif len(h1) > 1:
            # Esto se guardara en un archivo mas adelante
            logging.info(f"HAY MÁS DE UNA ETIQUETA <h1> EN {response}")
```

Este es bastante fácil, solamente hay que obtener la etiqueta `<h1>` de cada página web del sitio y entonces ver si el largo es 0: en caso positivo no hay ningún encabezado `<h1>`. La segunda condición es para ver si hay más de un solo `<h1>`.

## Comprobar si los enlaces del sitio abren en una pestaña nueva

No deberían abrir en una pestaña nueva.

## Comprobar si los enlaces que no son del sitio abren en una pestaña nueva

Sí deberían abrir en una pestaña nueva.

## Comprobar jerarquía de encabezados

Que no haya un h1 por debajo de un h2, o saltos importantes como h2 a h5 y cosas así.

## Mover la lógica de obtener todos los *href* a una sola función

```python
    def parse_href(self, response):
        return response.xpath("//a/@href").getall()
```

Todas las funciones que hacían uso de XPath ahora llaman a esta función.

## Volcar la información en un archivo

```python
    log_file_name = f"log_{datetime.today().strftime('%Y-%m-%d')}.txt"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = os.path.join("..", os.getcwd())
        self.url_file = self.open_file(self.url_file_name, "r")
        self.log_file = self.open_file(self.log_file_name, "a")
        self.start_urls = self.get_urls()
        self.allowed_domains = self.get_allowed_domains()

    def check(self, response):
        self.write_file(self.log_file, f"\nComprobando... {response}")

        yield from self.get_all_href(response)

        self.check_file_exists(response, "sitemap.xml")
        self.check_file_exists(response, "robots.txt")
        self.check_broken_links(response)
        self.check_http(response)
        self.check_favicon(response)
        self.check_h1(response)
        self.get_contact_links(response)
        self.check_img_links(response)

        # Esto ahora mismo da problemas
        self.close_file(response, self.log_file)
        self.close_file(response, self.url_file)

    def open_file(self, filename, mode):
        file_path = os.path.join(self.root, "..", filename)
        return open(file_path, mode, encoding="utf-8")

    def write_file(self, filename, text):
        filename.write(f"{text}\n")

    def close_file(self, filename):
        filename.close()
```

Creo tres funciones: una que abra el archivo (aunque lo he cambiado para que acepte otros archivos de texto), otra que escriba las líneas cuando dicha función es llamada y finalmente que cierre el archivo.  
Cada línea a escribir saldrá de todas las líneas anteriores de `logging.info()`. Por ejemplo, en esta función:

```python
    def check_file_exists(self, response, file):
        if response.url.rstrip("/") in self.start_urls:
            links = self.parse_href(response)

            for link in links:
                if file in link:
                    self.write_file(self.log_file, f"El archivo {file} sí existe en {self.start_urls}.")
                    return
            self.write_file(self.log_file, f"El archivo {file} no existe en {self.start_urls}.")
```

También el archivo de texto (que no hace falta crear porque lo hace automáticamente) tiene la fecha de creación.

# Problemas resueltos

## Falla en algunas web pero no en otras

Esto se debe a que quiere seguir enlaces que no puede seguir como tal: esto son los **mailto:**, **tel:** y similares. Pero sí queremos analizar todos los enlaces, se puedan seguir o no. La manera de hacer que no "explote", se cuelgue o tire excepciones es precisamente con un try-catch (en Python **try-except**):

```python
    def get_all_href(self, response):
        links = self.parse_href(response)

        is_internal_link = [link.strip() for link in links if self.internal_link(link)]

        for link in is_internal_link:
            try:
                yield response.follow(url=link, callback=self.check)
            except:
                self.write_file(self.log_file, f"No puedo seguir esta dirección {link}")
```

Simplemente hay que añadir esa línea ahí. La ejecución continuará normalmente y además mostrará en el archivo qué enlace se está "saltando".  
También se ha cambiado la línea de `yield from` a un `yield` normal y se ha metido en un bucle `for`.
A pesar de eso, la comprobación de teléfonos y correos que se hace en la función `check()` sí debería seguir funcionando.

## Si se cierra el archivo en la función `check()` el programa explota

Esto pasa porque el método `check()` se llama varias veces, una por respuesta, y entonces una vez que cierra el archivo la primera vez luego no puede escribir: además el archivo se abre solo una vez y no se vuelve a abrir así que se lo encuentra cerrado en las veces posteriores.

```python 
    def close_spider(self, response):
        # Cerrar archivo
        self.close_file(response, self.log_file)
        self.close_file(response, self.url_file)
```

Scrapy tiene un método bastante autodescriptivo que es `close_spider()` donde cada vez que se va a cerrar la araña, primero ejecuta lo que se defina dentro de él. En este caso es el cierre de los dos archivos.  
El cierre deja de estar en `check()` y pasa a `close_spider()`.

# Problemas por resolver

Me gustaría que procesara una página cada vez, de forma secuencial. Ahora mismo puede que primero compruebe un enlace de *página web 1*, luego otro de *página web 2* y luego otro de *página web 1* otra vez.

import os
import re
import logging
from datetime import datetime
from urllib.parse import urlparse

import scrapy

class AuditSpider(scrapy.Spider):
    # Nombre del crawler
    name = "crawler"

    # Patrones
    phone = r"^(\+34|0034|34|\(\+34\))?(?=(?:\D*\d){9,14}$)\d{2,4}(?:[\s\-]?\d{2,4})*$"
    mail = r"^([\w\-]+)(\@){1}([\w\-]+)(\.){1}([\w]+)$"

    # Archivos
    url_file_name = "urls.txt"
    log_file_name = f"log_{datetime.today().strftime('%Y-%m-%d')}.txt"

    # Constructor
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = os.path.join("..", os.getcwd())
        self.url_file = self.open_file(self.url_file_name, "r")
        self.log_file = self.open_file(self.log_file_name, "a")
        self.start_urls = self.get_urls()
        self.allowed_domains = self.get_allowed_domains()

    # Esta funcion la llama Scrapy automaticamente
    def parse(self, response):
        yield from self.get_all_href(response)

    # Obtener todos los href de todos los enlaces
    def parse_href(self, response):
        return response.xpath("//a/@href").getall()
    
    def get_all_href(self, response):
        links = self.parse_href(response)

        is_internal_link = [link.strip() for link in links if self.internal_link(link)]

        for link in is_internal_link:
            try:
                yield response.follow(url=link, callback=self.check)
            except:
                # logging.info(f"No puedo seguir esta dirección {link}")

                # Comentar esta linea si no se quiere que aparezca en el archivo
                self.write_file(self.log_file, f"No puedo seguir esta dirección {link}")

    # Practicamente la logica parte de aqui
    def check(self, response):
        self.write_file(self.log_file, f"\n---------------")
        self.write_file(self.log_file, f"Comprobando... {response}")
        self.write_file(self.log_file, f"---------------\n")

        # Obtener todos los href
        yield from self.get_all_href(response)

        # Comprobaciones
        self.check_file_exists(response, "sitemap.xml")
        self.check_file_exists(response, "robots.txt")
        self.check_broken_links(response)
        self.check_http(response)
        self.check_favicon(response)
        self.check_h1(response)
        self.get_contact_links(response)
        self.check_img_links(response)

    # Comprueba si archivos como sitemap.xml y robots.txt existen
    def check_file_exists(self, response, file):
        if response.url.rstrip("/") in self.start_urls:
            links = self.parse_href(response)

            for link in links:
                if file in link:
                    self.write_file(self.log_file, f"El archivo {file} sí existe en {self.start_urls}")
                    return
            self.write_file(self.log_file, f"El archivo {file} no existe en {self.start_urls}")

    # Comprueba si algun enlace da un mensaje de estado diferente a 200
    def check_broken_links(self, response):
        if response.status != 200:
            self.write_file(self.log_file, f"Enlace con código de estado {response.status}")

    # Comprueba si un enlace es HTTP en lugar de HTTPS
    def check_http(self, response):
        links = self.parse_href(response)

        for link in links:
            if link.startswith("http") and not link.startswith("https"):
                self.write_file(self.log_file, f"El enlace {link} no es HTTPS.")

    # Comprueba si el favicon existe o si esta vacio
    def check_favicon(self, response):
        link = response.xpath("//link[@rel='icon' or @rel='shortcut icon']")
        href = link.xpath("./@href").get()

        if link:
            if href == "" or href is None:
                self.write_file(self.log_file, f"El href del favicon está vacío: {href} en {response}")
        else:
            self.write_file(self.log_file, f"No hay favicon: {link} en {response}")

    # Obtiene los nodos de texto
    def get_text_nodes(self, response):
        return response.xpath("//body//*[text()]")

    # Obtiene los enlaces de contacto (telefono y correo electronico)
    def get_contact_links(self, response):
        nodes = self.get_text_nodes(response)

        for node in nodes:
            text = node.xpath("text()").get()
            if text is not None:
                self.check_contact_links(node, text, self.phone, "tel:")
                self.check_contact_links(node, text, self.mail, "mailto:")

    # Comprueba los enlaces de contacto (telefono y correo electronico)
    def check_contact_links(self, node, text, pattern, link_type):
        if re.search(pattern, text):
            if node.xpath(f"(ancestor::a | self::a)[contains(@href, '{link_type}')]").get() is None:
                self.write_file(self.log_file, f"{text} no tiene enlace de tipo {link_type}")

    # Comprueba si las imagenes tienen alt o si esta vacio
    def check_img_links(self, response):
        imgs = response.xpath("//body//img")

        for img in imgs:
            alt = img.xpath("./@alt").get()

            if alt is None:
                self.write_file(self.log_file, f"El atributo alt no existe en {img}")
            elif alt == "":
                self.write_file(self.log_file, f"El atributo alt está vacío en {img}")

    # Comprueba si existe la etiqueta h1 en cada pagina
    def check_h1(self, response):
        h1 = response.xpath("//h1")

        if len(h1) == 0:
            self.write_file(self.log_file, f"No hay ningún h1 en {response}")
        elif len(h1) > 1:
            self.write_file(self.log_file, f"Hay más de una etiqueta h1 en {response}")

    # Obtener los enlaces/dominios del archivo
    def get_urls(self):
        list_urls = [url.strip() for url in self.url_file if url.strip()]

        return list_urls
    
    # Los dominios permitidos para usar el crawler
    def get_allowed_domains(self):
        urls = self.get_urls()
        domains = set()

        for url in urls:
            url_parsed = urlparse(url)
            domains.add(url_parsed.netloc)
        
        return list(domains)
    
    # Para que no se escape el crawler
    def internal_link(self, url):
        url_parsed = urlparse(url)

        # URLs internas
        if not url_parsed.netloc:
            return True

        for domain in self.allowed_domains:
            if domain in url_parsed.netloc:
                return True
        return False 
            
    # Entrada/salida de los archivos de texto
    def open_file(self, filename, mode):
        file_path = os.path.join(self.root, "..", filename)
        return open(file_path, mode, encoding="utf-8")

    def write_file(self, filename, text):
        filename.write(f"{text}\n")

    def close_file(self, filename):
        filename.close()

    # Antes de cerrar el crawler
    def close_spider(self, response):
        # Cerrar archivo
        self.close_file(response, self.log_file)
        self.close_file(response, self.url_file)
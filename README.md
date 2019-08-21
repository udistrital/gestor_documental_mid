# Fachada para Gestor Documental
API para servir de fachada para la interacción con servicios del gestor documental.

Para construir la imagen se debe ejecutar

    docker build -t gestor_documental_mid:<tag> .

Para ejecutar el API se debe ejecutar:

    docker run -e API_PORT=<port> -e NUXEO_URL=<url> -e NUXEO_USERNAME=<username> -e NUXEO_PASORD=<pass> gestor_documental_mid:<tag>
# gestor_documental_mid

API CRUD para la gestión de información definida por la organización para las entidades de la universidad.

## Especificaciones Técnicas

### Tecnologías Implementadas y Versiones
* [Flask (Python)](https://flask.palletsprojects.com/en/1.1.x/)
* [Nuxeo SDK](https://doc.nuxeo.com/nxdoc/python-client/)
* [Docker](https://docs.docker.com/engine/install/ubuntu/)
* [Docker Compose](https://docs.docker.com/compose/)

### Variables de Entorno
```shell
# parametros de api
API_PORT=[Puerto de exposición del API]
NUXEO_URL=[URL de servidor Nuxeo]
NUXEO_USERNAME=[Usuario de nuxeo]
NUXEO_PASSWORD=[Contraseña usuario nuxeo]
DOCUMENTOS_CRUD_URL=[URL API documentos_crud]
```


**NOTA:** Las variables se pueden ver en el fichero api.py ...


**NOTA 2:** Solo para el caso de esta Api el parámetro path del target_group se cambia al valor /v1/
### Ejecución del Proyecto
```shell
#1. Obtener el repositorio con git
git clone https://github.com/udistrital/gestor_documental_mid.git

#2. Moverse a la carpeta del repositorio
cd gestor_documental_mid

# 3. Moverse a la rama **develop**
git pull origin develop && git checkout develop

# 4. alimentar todas las variables de entorno que utiliza el proyecto.
export API_PORT=8080 NUXEO_URL=https://xxxxxx/nuxeo/ NUXEO_USERNAME=xxxxxxx NUXEO_PASSWORD=xxxxxxx DOCUMENTOS_CRUD_URL=http://xxxxxxxxx/v1/

# 5. instalar dependencias de python
pip install -r requirements.txt

# 6. Ejecutar el api
python api.py
```
### Ejecución Dockerfile
```shell
# Implementado para despliegue del Sistema de integración continua CI.
```

### Documentacion

- [Documentacion y manual del servicio](https://docs.google.com/document/d/1ETG2KtDpNXN8hTyjDIe-VkVJ9gGFqzaC/edit?usp=sharing&ouid=110288693142592643207&rtpof=true&sd=true)

## Estado CI
| Develop | Relese 0.0.1 | Master |
| -- | -- | -- |
| [![Build Status](https://hubci.portaloas.udistrital.edu.co/api/badges/udistrital/gestor_documental_mid/status.svg?ref=refs/heads/develop)](https://hubci.portaloas.udistrital.edu.co/udistrital/gestor_documental_mid) | [![Build Status](https://hubci.portaloas.udistrital.edu.co/api/badges/udistrital/gestor_documental_mid/status.svg?ref=refs/heads/release/0.0.1)](https://hubci.portaloas.udistrital.edu.co/udistrital/gestor_documental_mid) | [![Build Status](https://hubci.portaloas.udistrital.edu.co/api/badges/udistrital/gestor_documental_mid/status.svg?ref=refs/heads/master)](https://hubci.portaloas.udistrital.edu.co/udistrital/gestor_documental_mid) |


## Licencia

This file is part of gestor_documental_mid.

gestor_documental_mid is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

gestor_documental_mid is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with gestor_documental_mid. If not, see https://www.gnu.org/licenses/.
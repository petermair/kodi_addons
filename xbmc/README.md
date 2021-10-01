# Setup instractions

* Install "Slyguy Common"-Addon from [Slyguy-Repository](https://www.matthuisman.nz/2020/02/slyguy-kodi-repository.html). 
* Install [Repository](https://github.com/PeterMair/kodi_addons/raw/master/install/repository.petermair/repository.petermair-0.0.2.zip) and install Plugins from repository

## SQLite3
No changes needed

## MySQL 
Modify [advancedsettings.xml](https://kodi.wiki/view/MySQL/Setting_up_Kodi#MySQL_and_advancedsettings.xml)
*   Add databasenames for Music and Video (with version)
````xml
    <advancedsettings>
    <videodatabase>
        ...
        <database>MyVideos116</database>
        ...
    </videodatabase> 
    <musicdatabase>
        ...
        <database>MyMusic72</database>
        ...
    </musicdatabase>
    </advancedsettings>
````
*   Plex:
````xml
    <advancedsettings>
    <plexdatabase>
        <type>mysql</type>
        <host>***.***.***.***</host>
        <database>plex</database>
        <port>3306</port>
        <user>kodi</user>
        <pass>***</pass>
    </plexdatabase>
    </advancedsettings>
````
*   Disney+:
````xml
    <advancedsettings>
    <disneyplusdatabase>
        <type>mysql</type>
        <host>***.***.***.***</host>
        <database>plex</database>
        <port>3306</port>
        <user>kodi</user>
        <pass>***</pass>
    </disneyplusdatabase>
    </advancedsettings>
````

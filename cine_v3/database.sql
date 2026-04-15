-- ============================================================
--  Sistema Web de Gestión de Cine - Base de Datos
-- ============================================================

CREATE DATABASE IF NOT EXISTS cine_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cine_db;

-- ------------------------------------------------------------
-- Tabla: usuarios
-- ------------------------------------------------------------
CREATE TABLE usuarios (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    nombre       VARCHAR(100) NOT NULL,
    email        VARCHAR(150) NOT NULL UNIQUE,
    contrasena   VARCHAR(255) NOT NULL,
    rol          ENUM('admin', 'cliente') NOT NULL DEFAULT 'cliente',
    telefono     VARCHAR(20),
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Tabla: peliculas
-- ------------------------------------------------------------
CREATE TABLE peliculas (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    titulo       VARCHAR(200) NOT NULL,
    descripcion  TEXT,
    duracion     INT NOT NULL COMMENT 'en minutos',
    genero       VARCHAR(80),
    clasificacion VARCHAR(10) COMMENT 'Ej: +13, +18, ATP',
    imagen_url   VARCHAR(300),
    trailer_url  VARCHAR(300),
    estado       ENUM('activa', 'inactiva') DEFAULT 'activa'
);

-- ------------------------------------------------------------
-- Tabla: funciones
-- ------------------------------------------------------------
CREATE TABLE funciones (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    pelicula_id  INT NOT NULL,
    fecha        DATE NOT NULL,
    hora         TIME NOT NULL,
    sala         VARCHAR(50) DEFAULT 'Sala Principal',
    precio       DECIMAL(10,2) NOT NULL,
    formato      VARCHAR(10) DEFAULT '2D',
    estado       ENUM('disponible', 'cancelada') DEFAULT 'disponible',
    FOREIGN KEY (pelicula_id) REFERENCES peliculas(id) ON DELETE CASCADE,
    -- Evita traslapes: misma sala, misma fecha y hora
    UNIQUE KEY no_traslape (sala, fecha, hora)
);

-- ------------------------------------------------------------
-- Tabla: asientos  (se precargan 150 asientos)
-- ------------------------------------------------------------
CREATE TABLE asientos (
    id      INT AUTO_INCREMENT PRIMARY KEY,
    numero  INT NOT NULL,
    fila    CHAR(1) NOT NULL,
    columna INT NOT NULL,
    tipo    VARCHAR(10) NOT NULL DEFAULT 'normal',
    estado  ENUM('activo', 'inactivo') DEFAULT 'activo'
);

-- ------------------------------------------------------------
-- Tabla: tiquetes
-- ------------------------------------------------------------
CREATE TABLE tiquetes (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    codigo       VARCHAR(50) NOT NULL UNIQUE,
    usuario_id   INT,
    funcion_id   INT NOT NULL,
    fecha_compra DATETIME DEFAULT CURRENT_TIMESTAMP,
    total        DECIMAL(10,2) NOT NULL,
    nombre_cliente VARCHAR(100),
    estado       ENUM('activo', 'usado', 'cancelado') DEFAULT 'activo',
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    FOREIGN KEY (funcion_id) REFERENCES funciones(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- Tabla: detalle_tiquete  (relación tiquete ↔ asientos)
-- ------------------------------------------------------------
CREATE TABLE detalle_tiquete (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    tiquete_id     INT NOT NULL,
    asiento_id     INT NOT NULL,
    precio_unitario DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (tiquete_id) REFERENCES tiquetes(id) ON DELETE CASCADE,
    FOREIGN KEY (asiento_id) REFERENCES asientos(id),
    -- Regla crítica: un asiento NO puede venderse dos veces en la misma función
    -- Se valida por backend; la restricción lógica se gestiona con función + asiento
    UNIQUE KEY asiento_por_funcion (tiquete_id, asiento_id)
);

-- ============================================================
--  DATOS INICIALES
-- ============================================================

-- Admin por defecto  (contraseña: admin123  - debes hashearla en producción)
INSERT INTO usuarios (nombre, email, contrasena, rol) VALUES
('Administrador', 'admin@cine.com', 'admin123', 'admin');

-- Precargar 150 asientos  (10 filas A-J × 15 columnas)
DELIMITER $$
CREATE PROCEDURE precargar_asientos()
BEGIN
    DECLARE f INT DEFAULT 0;
    DECLARE c INT DEFAULT 0;
    DECLARE fila_letra CHAR(1);
    DECLARE num INT DEFAULT 1;

    SET f = 1;
    WHILE f <= 10 DO
        SET fila_letra = CHAR(64 + f);   -- A=65, B=66 ...
        SET c = 1;
        WHILE c <= 15 DO
            INSERT INTO asientos (numero, fila, columna, tipo)
            VALUES (num, fila_letra, c, IF(f >= 9, 'vip', 'normal'));
            SET num = num + 1;
            SET c = c + 1;
        END WHILE;
        SET f = f + 1;
    END WHILE;
END$$
DELIMITER ;

CALL precargar_asientos();
DROP PROCEDURE precargar_asientos;

-- Películas de ejemplo
INSERT INTO peliculas (titulo, descripcion, duracion, genero, clasificacion, imagen_url, estado) VALUES
('Dune: Parte Dos',     'La épica continuación de la saga en Arrakis.',  166, 'Ciencia Ficción', '+13', 'https://via.placeholder.com/300x450?text=Dune+2',     'activa'),
('Oppenheimer',         'La historia del padre de la bomba atómica.',     180, 'Drama',            '+13', 'https://via.placeholder.com/300x450?text=Oppenheimer', 'activa'),
('Spider-Man: No Way Home', 'El multiverso se abre para Peter Parker.',  148, 'Acción',            'ATP', 'https://via.placeholder.com/300x450?text=SpiderMan',  'activa');

-- Funciones de ejemplo
INSERT INTO funciones (pelicula_id, fecha, hora, sala, precio) VALUES
(1, CURDATE(), '14:00:00', 'Sala Principal', 18000),
(1, CURDATE(), '17:30:00', 'Sala Principal', 18000),
(2, CURDATE(), '20:00:00', 'Sala Principal', 20000),
(3, DATE_ADD(CURDATE(), INTERVAL 1 DAY), '15:00:00', 'Sala Principal', 16000);

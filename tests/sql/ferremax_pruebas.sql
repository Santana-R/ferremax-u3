-- Esquema reproducible para una base PostgreSQL temporal de pruebas.
-- No elimina tablas ni datos existentes. El servidor temporal se descarta al cerrar.
CREATE SCHEMA IF NOT EXISTS ferremax_u3;

CREATE TABLE IF NOT EXISTS ferremax_u3.cotizacion_version (
    id uuid NOT NULL,
    version integer NOT NULL CHECK (version > 0),
    folio text NOT NULL,
    datos jsonb NOT NULL,
    PRIMARY KEY (id, version)
);
CREATE TABLE IF NOT EXISTS ferremax_u3.pedido (
    id uuid PRIMARY KEY,
    cotizacion_id uuid NOT NULL,
    cotizacion_version integer NOT NULL,
    estado text NOT NULL CHECK (estado IN ('Pendiente', 'Confirmado', 'Cancelado')),
    datos jsonb NOT NULL,
    FOREIGN KEY (cotizacion_id, cotizacion_version)
        REFERENCES ferremax_u3.cotizacion_version(id, version)
);
CREATE TABLE IF NOT EXISTS ferremax_u3.inventario (
    sku text NOT NULL,
    ubicacion_id text NOT NULL,
    existencia_fisica numeric NOT NULL CHECK (existencia_fisica >= 0),
    comprometida numeric NOT NULL DEFAULT 0 CHECK (comprometida >= 0),
    en_transito numeric NOT NULL DEFAULT 0 CHECK (en_transito >= 0),
    PRIMARY KEY (sku, ubicacion_id),
    CHECK (comprometida <= existencia_fisica)
);
CREATE TABLE IF NOT EXISTS ferremax_u3.reserva (
    pedido_id uuid NOT NULL REFERENCES ferremax_u3.pedido(id),
    sku text NOT NULL,
    ubicacion_id text NOT NULL,
    cantidad numeric NOT NULL CHECK (cantidad > 0),
    PRIMARY KEY (pedido_id, sku, ubicacion_id),
    FOREIGN KEY (sku, ubicacion_id)
        REFERENCES ferremax_u3.inventario(sku, ubicacion_id)
);
CREATE TABLE IF NOT EXISTS ferremax_u3.auditoria (
    id uuid PRIMARY KEY,
    actor_id text NOT NULL,
    accion text NOT NULL,
    agregado_id text NOT NULL,
    antes jsonb NOT NULL,
    despues jsonb NOT NULL,
    motivo text NOT NULL,
    fecha timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS ferremax_u3.outbox (
    id uuid PRIMARY KEY,
    tipo text NOT NULL,
    agregado_id text NOT NULL,
    datos jsonb NOT NULL,
    ocurrido timestamptz NOT NULL
);

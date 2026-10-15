-- Esquema del prototipo U3. Aplicar en un proyecto academico dedicado.
BEGIN;
CREATE SCHEMA IF NOT EXISTS ferremax_u3;
REVOKE ALL ON SCHEMA ferremax_u3 FROM PUBLIC;
DO $$ DECLARE r text; BEGIN
  FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
    IF EXISTS(SELECT FROM pg_roles WHERE rolname=r) THEN
      EXECUTE format('REVOKE ALL ON SCHEMA ferremax_u3 FROM %I',r);
    END IF;
  END LOOP;
  IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='ferremax_u3_backend') THEN
    CREATE ROLE ferremax_u3_backend NOLOGIN;
  END IF;
END $$;
CREATE TABLE IF NOT EXISTS ferremax_u3.cotizacion_version(
  id uuid NOT NULL,version integer NOT NULL CHECK(version>0),folio text NOT NULL,
  datos jsonb NOT NULL,PRIMARY KEY(id,version),UNIQUE(folio,version));
CREATE TABLE IF NOT EXISTS ferremax_u3.pedido(
  id uuid PRIMARY KEY,cotizacion_id uuid NOT NULL,cotizacion_version integer NOT NULL,
  estado text NOT NULL CHECK(estado IN ('Pendiente','Confirmado','Cancelado')),datos jsonb NOT NULL,
  FOREIGN KEY(cotizacion_id,cotizacion_version) REFERENCES ferremax_u3.cotizacion_version(id,version));
CREATE TABLE IF NOT EXISTS ferremax_u3.inventario(
  sku text NOT NULL,ubicacion_id text NOT NULL,
  existencia_fisica numeric NOT NULL CHECK(existencia_fisica>=0 AND existencia_fisica<'Infinity'::numeric),
  comprometida numeric NOT NULL DEFAULT 0 CHECK(comprometida>=0 AND comprometida<'Infinity'::numeric),
  en_transito numeric NOT NULL DEFAULT 0 CHECK(en_transito>=0 AND en_transito<'Infinity'::numeric),
  PRIMARY KEY(sku,ubicacion_id),CHECK(comprometida<=existencia_fisica));
CREATE TABLE IF NOT EXISTS ferremax_u3.reserva(
  pedido_id uuid NOT NULL REFERENCES ferremax_u3.pedido(id),sku text NOT NULL,ubicacion_id text NOT NULL,
  cantidad numeric NOT NULL CHECK(cantidad>0 AND cantidad<'Infinity'::numeric),
  PRIMARY KEY(pedido_id,sku,ubicacion_id),
  FOREIGN KEY(sku,ubicacion_id) REFERENCES ferremax_u3.inventario(sku,ubicacion_id));
CREATE TABLE IF NOT EXISTS ferremax_u3.auditoria(
  id uuid PRIMARY KEY,actor_id text NOT NULL,accion text NOT NULL,agregado_id text NOT NULL,
  antes jsonb NOT NULL,despues jsonb NOT NULL,motivo text NOT NULL CHECK(length(trim(motivo))>0),fecha timestamptz NOT NULL);
CREATE INDEX IF NOT EXISTS auditoria_agregado_fecha ON ferremax_u3.auditoria(agregado_id,fecha);
CREATE TABLE IF NOT EXISTS ferremax_u3.outbox(
  id uuid PRIMARY KEY,tipo text NOT NULL,agregado_id text NOT NULL,datos jsonb NOT NULL,
  ocurrido timestamptz NOT NULL,publicado boolean NOT NULL DEFAULT false);
CREATE INDEX IF NOT EXISTS outbox_pendiente ON ferremax_u3.outbox(ocurrido) WHERE NOT publicado;
GRANT USAGE ON SCHEMA ferremax_u3 TO ferremax_u3_backend;
GRANT SELECT,INSERT ON ferremax_u3.cotizacion_version TO ferremax_u3_backend;
GRANT SELECT,INSERT,UPDATE ON ferremax_u3.pedido,ferremax_u3.inventario TO ferremax_u3_backend;
GRANT SELECT,INSERT,DELETE ON ferremax_u3.reserva TO ferremax_u3_backend;
GRANT SELECT,INSERT ON ferremax_u3.auditoria,ferremax_u3.outbox TO ferremax_u3_backend;
DO $$ DECLARE t text; r text; BEGIN
  FOREACH t IN ARRAY ARRAY['cotizacion_version','pedido','inventario','reserva','auditoria','outbox'] LOOP
    EXECUTE format('ALTER TABLE ferremax_u3.%I ENABLE ROW LEVEL SECURITY',t);
    EXECUTE format('REVOKE ALL ON ferremax_u3.%I FROM PUBLIC',t);
    FOREACH r IN ARRAY ARRAY['anon','authenticated'] LOOP
      IF EXISTS(SELECT FROM pg_roles WHERE rolname=r) THEN
        EXECUTE format('REVOKE ALL ON ferremax_u3.%I FROM %I',t,r);
      END IF;
    END LOOP;
    IF NOT EXISTS(SELECT FROM pg_policies WHERE schemaname='ferremax_u3' AND tablename=t AND policyname='backend_confiable') THEN
      EXECUTE format('CREATE POLICY backend_confiable ON ferremax_u3.%I TO ferremax_u3_backend USING(true) WITH CHECK(true)',t);
    END IF;
  END LOOP;
END $$;
COMMIT;

-- Core database schema for CountyStream property data.
-- Postgres is the canonical store for normalized parcel records used by search,
-- frontend details, KPI queries, and future GIS joins.

CREATE SCHEMA IF NOT EXISTS fl;

CREATE TABLE IF NOT EXISTS fl.properties (
    state text NOT NULL DEFAULT 'FL',
    county text NOT NULL,
    county_number integer,
    parcel_id text NOT NULL,
    state_parcel_id text,
    owner_name text,

    situs_street text,
    situs_city text,
    situs_state text,
    situs_zip text,
    situs_address_normalized text,
    property_address_hash text,

    mailing_street_1 text,
    mailing_street_2 text,
    mailing_city text,
    mailing_state text,
    mailing_zip text,

    dor_land_use_code text,
    pa_land_use_code text,
    neighborhood_code text,
    market_area text,

    year_built_actual integer,
    year_built_effective integer,
    living_area_sqft integer,
    land_sqft integer,
    residential_units integer,
    building_count integer,

    land_value bigint,
    building_value bigint,
    assessed_value_sd bigint,
    assessed_value_nsd bigint,
    just_value bigint,
    taxable_value_sd bigint,
    taxable_value_nsd bigint,

    last_sale_date text,
    last_sale_price bigint,
    last_sale_qualified_code text,
    last_sale_vacant_improved_code text,

    bedrooms numeric,
    bathrooms numeric,
    half_bathrooms numeric,

    base_source text NOT NULL DEFAULT 'FL_DOR_NAL',
    enrichment_source text,

    inserted_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (state, county, parcel_id)
);

CREATE INDEX IF NOT EXISTS fl_properties_address_hash_idx
    ON fl.properties (property_address_hash)
    WHERE property_address_hash IS NOT NULL;

CREATE INDEX IF NOT EXISTS fl_properties_county_city_zip_idx
    ON fl.properties (county, situs_city, situs_zip);

CREATE INDEX IF NOT EXISTS fl_properties_owner_idx
    ON fl.properties USING gin (to_tsvector('simple', coalesce(owner_name, '')));

CREATE INDEX IF NOT EXISTS fl_properties_address_search_idx
    ON fl.properties USING gin (to_tsvector('simple', coalesce(situs_address_normalized, '')));

CREATE INDEX IF NOT EXISTS fl_properties_value_idx
    ON fl.properties (just_value);

CREATE INDEX IF NOT EXISTS fl_properties_sale_price_idx
    ON fl.properties (last_sale_price);

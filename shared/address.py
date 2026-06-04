"""Address normalization and deterministic hashing.

This module ports the normalization behavior from the Go value object used by
REIsearch/CountyStream into Python. The hash is intentionally based on the
canonical USPS-style address string so formatting differences like
"Street" vs "ST" or "Florida" vs "FL" collapse to the same property key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Callable, Optional


STREET_ABBREVIATIONS = {
    "street": "ST", "road": "RD", "avenue": "AVE", "boulevard": "BLVD",
    "drive": "DR", "lane": "LN", "court": "CT", "highway": "HWY",
    "parkway": "PKWY", "terrace": "TER", "circle": "CIR", "place": "PL",
    "st": "ST", "rd": "RD", "ave": "AVE", "blvd": "BLVD",
    "dr": "DR", "ln": "LN", "ct": "CT", "hwy": "HWY",
    "pkwy": "PKWY", "ter": "TER", "cir": "CIR", "pl": "PL",
}

DIRECTIONALS = {
    "north": "N", "south": "S", "east": "E", "west": "W",
    "northeast": "NE", "northwest": "NW", "southeast": "SE", "southwest": "SW",
    "north west": "NW", "south east": "SE", "south west": "SW",
    "n": "N", "s": "S", "e": "E", "w": "W",
    "ne": "NE", "nw": "NW", "se": "SE", "sw": "SW",
}

STATE_MAP = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "district of columbia": "DC", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}

ORDINALS = {
    "first": "1st", "second": "2nd", "third": "3rd", "fourth": "4th",
    "fifth": "5th", "sixth": "6th", "seventh": "7th", "eighth": "8th",
    "ninth": "9th", "tenth": "10th",
}

NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12",
}

STREET_WORD_ALIASES = {
    "hwy": "highway",
    "hiway": "highway",
    "mt": "mount",
    "st": "street",
    "rd": "road",
    "ave": "avenue",
}

CITY_ALIAS_MAP = {
    "st louis": "saint louis",
    "saint louis": "saint louis",
    "st. louis": "saint louis",
    "st paul": "saint paul",
    "mt view": "mountain view",
    "mount view": "mountain view",
    "ft worth": "fort worth",
    "ft. worth": "fort worth",
    "ft lauderdale": "fort lauderdale",
}

UNIT_NORMALIZATION_MAP = {
    "apt": "APT", "apartment": "APT", "unit": "APT",
    "ste": "APT", "suite": "APT", "bldg": "APT", "building": "APT",
    "fl": "APT", "floor": "APT", "rm": "APT", "room": "APT",
}

USPS_ABBREVIATIONS = {
    "APT", "STE", "BLDG", "FL", "RM", "ST", "RD", "AVE", "BLVD", "DR",
    "LN", "CT", "HWY", "PKWY", "TER", "CIR", "PL", "N", "S", "E", "W",
    "NE", "NW", "SE", "SW",
}

WHITESPACE_RE = re.compile(r"\s+")
ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")
ORDINAL_SUFFIX_RE = re.compile(r"^(\d+)(st|nd|rd|th)$", re.IGNORECASE)
INLINE_UNIT_RE = re.compile(r"^(?:#|apt|apartment|unit|ste|suite|bldg|building|fl|floor|rm|room)[#-]?([a-z0-9]+)$", re.IGNORECASE)
STREET_PUNCTUATION_RE = re.compile(r"[.,]")
ZIP_DIGIT_EXTRACTOR = re.compile(r"\d{5}")
TWO_LETTER_STATE_RE = re.compile(r"^[a-z]{2}$", re.IGNORECASE)

DEFAULT_NORMALIZATION_PENALTY = 0.05
_address_canonicalizer: Optional[Callable[[str], str]] = None


@dataclass
class NormalizationContext:
    notes: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def add_note(self, note: str) -> None:
        if note:
            self.notes.append(note)
            self.penalize(DEFAULT_NORMALIZATION_PENALTY)

    def penalize(self, delta: float) -> None:
        if delta > 0:
            self.confidence = max(0.1, self.confidence - delta)


@dataclass
class Address:
    street_address: str
    city: str
    state: str
    zip_code: str
    county: str = ""
    country: str = "US"
    normalized: str = ""
    normalization_confidence: float = 1.0
    normalization_notes: list[str] = field(default_factory=list)

    @property
    def address_hash(self) -> str:
        return hash_normalized_address(self.normalized)

    def is_valid(self) -> bool:
        """Return True when the address has the minimum required fields."""
        return bool(self.street_address and self.city and self.state and self.zip_code)

    def equals(self, other: object) -> bool:
        """Return True when another Address has the same normalized form."""
        return isinstance(other, Address) and self.normalized == other.normalized

    def __str__(self) -> str:
        """Return the canonical normalized address string."""
        return self.normalized

    def __eq__(self, other: object) -> bool:
        return self.equals(other)


class AddressNormalizationError(ValueError):
    """Raised when an address cannot be normalized into street/city/state/ZIP."""


def register_address_canonicalizer(fn: Optional[Callable[[str], str]]) -> None:
    """Optionally inject an external USPS/SmartyStreets-style canonicalizer."""
    global _address_canonicalizer
    _address_canonicalizer = fn


def normalize_address_string(address: str) -> str:
    normalized, _, _ = normalize_address_string_with_meta(address)
    return normalized


def normalize_address_string_with_meta(address: str) -> tuple[str, float, list[str]]:
    ctx = NormalizationContext()
    normalized = address.strip().lower() if address is not None else ""
    if not normalized:
        raise AddressNormalizationError("address cannot be empty")

    # Keep ZIP+4 usable before normalizing hyphens elsewhere in the address.
    normalized = re.sub(r"\b(\d{5})-\d{4}\b", r"\1", normalized)
    normalized = normalized.replace("-", " ")
    normalized = WHITESPACE_RE.sub(" ", normalized).strip()
    normalized = normalize_ordinal_suffixes(normalized)

    clean_parts = [part.strip() for part in normalized.split(",") if part.strip()]
    if len(clean_parts) == 4:
        clean_parts[2] = clean_parts[2] + " " + clean_parts[3]
        clean_parts = clean_parts[:3]

    if len(clean_parts) < 3:
        ctx.add_note("address missing expected components")
        raise AddressNormalizationError(f"address format invalid: {address}")

    street = " ".join(clean_parts[: len(clean_parts) - 2])
    street = STREET_PUNCTUATION_RE.sub(" ", street)
    street = WHITESPACE_RE.sub(" ", street).strip()
    street_words = street.split(" ") if street else []

    for i, word in enumerate(street_words):
        if word in ORDINALS:
            street_words[i] = ORDINALS[word]
        else:
            street_words[i] = normalize_ordinal_token(word)

    street_words = apply_word_aliases(street_words, STREET_WORD_ALIASES, ctx)
    street_words = normalize_directional_tokens(street_words)
    street_words = [STREET_ABBREVIATIONS.get(word, word) for word in street_words]
    street_words = normalize_unit_tokens(street_words, ctx)

    if street_words and street_words[0] in NUMBER_WORDS:
        street_words[0] = NUMBER_WORDS[street_words[0]]

    street = " ".join(street_words)

    city = WHITESPACE_RE.sub(" ", clean_parts[len(clean_parts) - 2]).strip()
    clean_city = remove_diacritics(city)
    if clean_city != city:
        ctx.add_note("removed city diacritics")
        city = clean_city

    lower_city = city.lower()
    canonical_city = CITY_ALIAS_MAP.get(lower_city)
    if canonical_city:
        if canonical_city != lower_city:
            ctx.add_note("normalized city alias")
        city = canonical_city

    valid_tokens = [token.strip() for token in clean_parts[-1].split(" ") if token.strip()]
    if len(valid_tokens) < 2:
        ctx.add_note("missing state or zip component")
        raise AddressNormalizationError(f"invalid state and ZIP format in address: {address}")

    zip_code = valid_tokens[-1]
    if not ZIP_RE.match(zip_code):
        digits = ZIP_DIGIT_EXTRACTOR.search(zip_code)
        if digits:
            ctx.add_note("extracted ZIP digits from noisy token")
            zip_code = digits.group(0)
        else:
            ctx.add_note("invalid ZIP code token")
            raise AddressNormalizationError(f"invalid ZIP code in address: {address}")

    if "-" in zip_code:
        zip_code = zip_code.split("-", 1)[0]

    state_raw = " ".join(valid_tokens[:-1]).replace(".", "")
    state = STATE_MAP.get(state_raw.lower())
    if not state and TWO_LETTER_STATE_RE.match(state_raw):
        state = state_raw.upper()
    if not state:
        raise AddressNormalizationError(f"invalid state: {state_raw}")

    canonical = f"{to_title_case(street)}, {to_title_case(city)}, {state} {zip_code}"
    canonical = WHITESPACE_RE.sub(" ", canonical).strip()

    if _address_canonicalizer is not None:
        try:
            verified = _address_canonicalizer(canonical)
            if verified:
                if verified != canonical:
                    ctx.add_note("applied external canonicalizer")
                canonical = verified
        except Exception:
            ctx.add_note("external canonicalizer error")

    return canonical, ctx.confidence, ctx.notes


def new_address(raw_address: str) -> Address:
    normalized, confidence, notes = normalize_address_string_with_meta(raw_address)
    street, city, state_zip = normalized.split(", ")
    state, zip_code = state_zip.split(" ")
    return Address(
        street_address=street,
        city=city,
        state=state,
        zip_code=zip_code,
        country="US",
        normalized=normalized,
        normalization_confidence=confidence,
        normalization_notes=notes,
    )


def new_address_from_parts(street_address: str, city: str, state: str, zip_code: str, county: str = "") -> Address:
    street = normalize_street_address(street_address)
    normalized_city = normalize_city(city)
    normalized_state = normalize_state(state)
    normalized_zip = normalize_zip_code(zip_code)
    canonical = WHITESPACE_RE.sub(" ", f"{street}, {normalized_city}, {normalized_state} {normalized_zip}").strip()
    return Address(
        street_address=street,
        city=normalized_city,
        state=normalized_state,
        zip_code=normalized_zip,
        county=normalize_city(county) if county else "",
        country="US",
        normalized=canonical,
        normalization_confidence=1.0,
        normalization_notes=["normalized from structured fields"],
    )


def hash_normalized_address(normalized_address: str) -> str:
    """Return a stable SHA-256 hex hash for a canonical address string."""
    if not normalized_address:
        raise AddressNormalizationError("normalized address cannot be empty")
    return hashlib.sha256(normalized_address.encode("utf-8")).hexdigest()


def hash_address(address: str) -> str:
    """Normalize a raw address, then return its deterministic SHA-256 hash."""
    return hash_normalized_address(normalize_address_string(address))


def hash_address_parts(street_address: str, city: str, state: str, zip_code: str) -> str:
    """Normalize structured address parts, then return their deterministic SHA-256 hash."""
    return new_address_from_parts(street_address, city, state, zip_code).address_hash


def normalize_ordinal_suffixes(input_value: str) -> str:
    return " ".join(normalize_ordinal_token(word) for word in input_value.split(" "))


def normalize_ordinal_token(word: str) -> str:
    match = ORDINAL_SUFFIX_RE.match(word.strip().lower())
    if match:
        return f"{match.group(1)}{match.group(2)}"
    return word


def apply_word_aliases(words: list[str], aliases: dict[str, str], ctx: NormalizationContext) -> list[str]:
    result = []
    for word in words:
        lower = word.lower()
        replacement = aliases.get(lower, word)
        if replacement != lower and lower in aliases:
            ctx.add_note("normalized street alias")
        result.append(replacement)
    return result


def normalize_directional_tokens(words: list[str]) -> list[str]:
    result = list(words)
    i = 0
    while i < len(result) - 1:
        two_word = f"{result[i]} {result[i + 1]}"
        replacement = DIRECTIONALS.get(two_word)
        if replacement:
            result[i] = replacement
            del result[i + 1]
            if i > 0:
                i -= 1
            continue
        i += 1
    return [DIRECTIONALS.get(word, word) for word in result]


def normalize_unit_tokens(words: list[str], ctx: NormalizationContext) -> list[str]:
    result: list[str] = []
    i = 0
    while i < len(words):
        word = words[i]
        lower = word.lower()
        if lower.startswith("#") and len(lower) > 1:
            result.extend(["APT", lower.lstrip("#").upper()])
            ctx.add_note("normalized inline # unit identifier")
            i += 1
            continue

        label = UNIT_NORMALIZATION_MAP.get(lower)
        if label:
            value = ""
            if i + 1 < len(words):
                next_value = words[i + 1].strip().strip("#")
                if next_value:
                    value = next_value
                    i += 1
            result.append(label)
            if value:
                result.append(value.upper())
            ctx.add_note("normalized explicit unit identifier")
            i += 1
            continue

        match = INLINE_UNIT_RE.match(lower)
        if match:
            result.extend(["APT", match.group(1).upper()])
            ctx.add_note("normalized inline unit token")
            i += 1
            continue

        result.append(word)
        i += 1
    return result


def remove_diacritics(value: str) -> str:
    replacements = str.maketrans({
        "à": "a", "á": "a", "â": "a", "ã": "a", "ä": "a",
        "è": "e", "é": "e", "ê": "e", "ë": "e",
        "ì": "i", "í": "i", "î": "i", "ï": "i",
        "ò": "o", "ó": "o", "ô": "o", "õ": "o", "ö": "o",
        "ù": "u", "ú": "u", "û": "u", "ü": "u",
        "ñ": "n", "ç": "c",
        "À": "A", "Á": "A", "Â": "A", "Ã": "A", "Ä": "A",
        "È": "E", "É": "E", "Ê": "E", "Ë": "E",
        "Ì": "I", "Í": "I", "Î": "I", "Ï": "I",
        "Ò": "O", "Ó": "O", "Ô": "O", "Õ": "O", "Ö": "O",
        "Ù": "U", "Ú": "U", "Û": "U", "Ü": "U",
        "Ñ": "N", "Ç": "C",
    })
    return value.translate(replacements)


def to_title_case(value: str) -> str:
    result = []
    for word in value.split(" "):
        if not word:
            continue
        if (
            word in USPS_ABBREVIATIONS
            or re.match(r"^[A-Z]{2}$", word)
            or re.match(r"^\d+$", word)
            or re.match(r"^\d+[A-Z]+$", word)
        ):
            result.append(word)
        else:
            result.append(word[0].upper() + word[1:].lower())
    return " ".join(result)


def normalize_street_address(street: str) -> str:
    if not street:
        raise AddressNormalizationError("street address cannot be empty")
    normalized = STREET_PUNCTUATION_RE.sub(" ", street.strip().lower())
    normalized = WHITESPACE_RE.sub(" ", normalized).strip()
    words = normalized.split(" ")
    words = [ORDINALS.get(word, normalize_ordinal_token(word)) for word in words]
    words = normalize_directional_tokens(words)
    words = [STREET_ABBREVIATIONS.get(word, word) for word in words]
    words = normalize_unit_tokens(words, NormalizationContext())
    if words and words[0] in NUMBER_WORDS:
        words[0] = NUMBER_WORDS[words[0]]
    return to_title_case(" ".join(words))


def normalize_city(city: str) -> str:
    if not city:
        return ""
    normalized = WHITESPACE_RE.sub(" ", city.strip().lower()).strip()
    normalized = CITY_ALIAS_MAP.get(normalized, normalized)
    return to_title_case(normalized)


def normalize_state(state: str) -> str:
    if not state:
        raise AddressNormalizationError("state cannot be empty")
    normalized = state.strip().lower().replace(".", "")
    if TWO_LETTER_STATE_RE.match(normalized):
        return normalized.upper()
    if normalized in STATE_MAP:
        return STATE_MAP[normalized]
    raise AddressNormalizationError(f"invalid state: {state}")


def normalize_zip_code(zip_code: str) -> str:
    if not zip_code:
        raise AddressNormalizationError("ZIP code cannot be empty")
    normalized = zip_code.strip()
    if not ZIP_RE.match(normalized):
        raise AddressNormalizationError(f"invalid ZIP code format: {zip_code}")
    return normalized.split("-", 1)[0]

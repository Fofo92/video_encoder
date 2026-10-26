"""Keep both language titles, including identical titles for foreign works."""


def title_with_original(metadata):
    french = str(metadata.get("french_title") or "").strip()
    original = str(metadata.get("original_title") or "").strip()
    if not french:
        return original
    if not original:
        return french
    countries = metadata.get("countries", [])
    french_work = (isinstance(countries, list) and bool(countries)
                   and all(isinstance(country, str) and country.strip().casefold() == "france"
                           for country in countries))
    duplicate = french.casefold() == original.casefold() and french_work
    already_present = french.casefold().endswith(f" ({original.casefold()})")
    return french if duplicate or already_present else f"{french} ({original})"
